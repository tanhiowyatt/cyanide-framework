import datetime
import os
import posixpath
import threading
from collections import ChainMap
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union, cast

from jinja2.sandbox import SandboxedEnvironment

from ..core.paths import get_profiles_dir
from .backend import SqliteBackend, VFSBackend
from .context import Context
from .dynamic import PROVIDERS
from .nodes import Directory, File, Node


class VirtualFile(File):
    """Proxy for a file node."""

    def __init__(
        self,
        name: str,
        path: str,
        fs: "FakeFilesystem",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name, **(config or {}))
        self.path = path
        self.fs = fs

    @property
    def content(self) -> Union[str, bytes]:
        return self.fs.get_content(self.path)


class VirtualDirectory(Directory):
    """Proxy for a directory node."""

    def __init__(
        self,
        name: str,
        path: str,
        fs: "FakeFilesystem",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name, children_getter=lambda: self._lazy_children(), **(config or {}))
        self.path = path
        self.fs = fs

    def _lazy_children(self) -> Dict[str, Node]:
        """Lazy-load children as needed by ls."""
        names = self.fs.list_dir(self.path)
        result = {}
        for name in names:
            child_path = posixpath.join(self.path, name)
            node = self.fs.get_node(child_path)
            if node:
                result[name] = node
        return result

    def get_child(self, name: str) -> Optional[Node]:
        return self.children.get(name)


class FakeFilesystem:
    """Modern Simulated Linux filesystem using Template + Context model."""

    BASH_HISTORY = ".bash_history"
    _jinja_env = SandboxedEnvironment()
    _template_cache: Dict[tuple[str, str], Any] = {}
    _cache_lock = threading.Lock()

    def __init__(
        self,
        os_profile: Optional[str] = None,
        root_dir: Optional[Union[str, Path]] = None,
        audit_callback=None,
        stats=None,
        users: Optional[List[Dict[str, Any]]] = None,
        src_ip: str = "unknown",
        session_id: str = "unknown",
        session_mgr=None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.config = config or {}
        self.root_dir = Path(root_dir) if root_dir else get_profiles_dir()
        self.audit_callback = audit_callback
        self.stats = stats
        self.users = users or []
        self.src_ip = src_ip
        self.session_id = session_id
        self.session_mgr = session_mgr

        self.os_profile: str = os_profile or os.getenv("OS_PROFILE") or "debian"
        self.profile_path = self.root_dir / self.os_profile

        self.context: Optional[Context] = None
        self.dynamic_files: Dict[str, Any] = {}
        self.backend: Optional[VFSBackend] = None

        self.memory_overlay: ChainMap = ChainMap({}, {})
        self.honeytokens: List[str] = []
        self.deleted_paths: Set[str] = set()
        self._processes: List[Dict[str, Any]] = []
        self._processes_initialized = False
        self._system_files_initialized = False
        self._user_homes_initialized = False
        self._ip_history_initialized = False

        # Load limits from config
        self.max_overlay_size = self.config.get("vfs", {}).get("max_overlay_size", 50 * 1024 * 1024)
        self.max_nodes = self.config.get("vfs", {}).get("max_nodes", 10000)

        self.jinja_env = self.__class__._jinja_env

        self._load_profile()
        # Deferred initialization

    def close(self):
        if self.backend and not getattr(self.backend, "is_shared", False):
            self.backend.close()

    def __del__(self):
        self.close()

    @property
    def processes(self) -> List[Dict[str, Any]]:
        if not self._processes_initialized:
            self._initialize_processes()
        return self._processes

    @processes.setter
    def processes(self, value: List[Dict[str, Any]]):
        self._processes = value
        self._processes_initialized = True

    def _ensure_system_init(self):
        """Ensure system files and user homes are initialized before VFS access."""
        if not self._system_files_initialized:
            self._system_files_initialized = True
            self._generate_system_files()
        if not self._user_homes_initialized:
            self._user_homes_initialized = True
            self._initialize_user_homes()
        if not self._ip_history_initialized:
            self._ip_history_initialized = True
            self._load_ip_history()

    def _initialize_processes(self):
        """Source processes from dynamic provider if available, otherwise use defaults."""
        import json

        # Look for a processes provider in dynamic_files
        proc_config = None
        for path, cfg in self.dynamic_files.items():
            if cfg.get("provider") == "processes_provider":
                proc_config = cfg
                break

        if proc_config:
            provider = PROVIDERS.get("processes_provider")
            if provider:
                try:
                    raw = provider(self.context, proc_config.get("args", {}))
                    self._processes = json.loads(raw)
                    self._processes_initialized = True
                    return
                except Exception:
                    pass

        # Fallback to minimal defaults if no provider found or it failed
        self._processes = [
            {
                "pid": 1,
                "tty": "?",
                "time": "00:00:15",
                "cmd": "/sbin/init",
                "user": "root",
            },
            {
                "pid": 2,
                "tty": "?",
                "time": "00:00:00",
                "cmd": "[kthreadd]",
                "user": "root",
            },
        ]
        self._processes_initialized = True

    def _generate_system_files(self):
        """Generate /etc/passwd and /etc/group based on self.users."""
        passwd_lines = [
            "root:x:0:0:root:/root:/bin/bash",
            "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin",
            "bin:x:2:2:bin:/bin:/usr/sbin/nologin",
            "sys:x:3:3:sys:/dev:/usr/sbin/nologin",
            "sync:x:4:65534:sync:/bin:/bin/sync",
        ]
        group_lines = [
            "root:x:0:",
            "daemon:x:1:",
            "bin:x:2:",
            "sys:x:3:",
            "adm:x:4:",
            "tty:x:5:",
            "disk:x:6:",
            "lp:x:7:",
            "mail:x:8:",
            "news:x:9:",
            "uucp:x:10:",
        ]

        uid = 1000
        for user_entry in self.users:
            username = user_entry.get("user")
            if not username or username == "root":
                continue

            home = f"/home/{username}"
            passwd_lines.append(f"{username}:x:{uid}:{uid}:{username}:{home}:/bin/bash")
            group_lines.append(f"{username}:x:{uid}:")
            uid += 1

        self.memory_overlay["/etc/passwd"] = {
            "type": "file",
            "content": "\n".join(passwd_lines) + "\n",
            "owner": "root",
            "group": "root",
            "perm": "-rw-r--r--",
        }
        self.memory_overlay["/etc/group"] = {
            "type": "file",
            "content": "\n".join(group_lines) + "\n",
            "owner": "root",
            "group": "root",
            "perm": "-rw-r--r--",
        }

    def _load_ip_history(self):
        """Load persistent history for the source IP."""
        if self.src_ip == "unknown":
            return

        history_base = Path("var/lib/cyanide/history") / self.src_ip
        history_file = history_base / self.BASH_HISTORY

        if history_file.exists():
            try:
                content = history_file.read_text()
                self.memory_overlay[f"/root/{self.BASH_HISTORY}"] = {
                    "type": "file",
                    "content": content,
                    "owner": "root",
                    "group": "root",
                    "perm": "-rw-------",
                    "size": len(content),
                    "mtime": datetime.datetime.fromtimestamp(history_file.stat().st_mtime),
                }
            except Exception as e:
                import logging

                logging.debug(f"Failed to load history for {self.src_ip}: {e}")

    def save_ip_history(self):
        """Save current session history to persistent storage."""
        if self.src_ip == "unknown":
            return

        history_path = f"/root/{self.BASH_HISTORY}"
        if history_path not in self.memory_overlay:
            return

        content = self.memory_overlay[history_path].get("content", "")
        if not content:
            return

        history_base = Path("var/lib/cyanide/history") / self.src_ip
        try:
            history_base.mkdir(parents=True, exist_ok=True)
            (history_base / self.BASH_HISTORY).write_text(content)
        except Exception as e:
            import logging

            logging.error(f"Failed to save history for {self.src_ip}: {e}")

    def _initialize_user_homes(self):
        """Automatically create /home/[user] for all configured users."""
        self.mkdir_p("/home")

        for user_entry in self.users:
            username = user_entry.get("user")
            if not username:
                continue

            if username == "root":
                self.mkdir_p("/root", owner="root", group="root")
            else:
                self._create_user_home(username)

    def _create_user_home(self, username: str):
        """Helper to create and initialize a user home directory."""
        home_path = f"/home/{username}"
        self.mkdir_p(home_path, owner=username, group=username)

        # Ensure basic shell config files exist with correct ownership
        for config_file in [".bashrc", ".bash_profile", self.BASH_HISTORY]:
            file_path = f"{home_path}/{config_file}"
            if not self.exists(file_path):
                self.mkfile(
                    file_path,
                    content=f"# {config_file}\n",
                    owner=username,
                    group=username,
                )
            else:
                self.chown(file_path, owner=username, group=username)

        # Setup .ssh directory
        self._initialize_ssh_dir(home_path, username)

    def _initialize_ssh_dir(self, home_path: str, username: str):
        """Setup .ssh directory with restricted permissions."""
        ssh_path = f"{home_path}/.ssh"
        if not self.exists(ssh_path):
            self.mkdir_p(ssh_path, owner=username, group=username, perm="drwx------")
        else:
            self.chown(ssh_path, owner=username, group=username)
            self.chmod(ssh_path, "drwx------")

    def _load_profile(self):
        """Load profile configuration using SQLite backend."""
        from .profile_loader import load as load_profile

        if (
            not (self.profile_path / "base.yaml").exists()
            and not (self.profile_path / ".compiled.db").exists()
            and not self.profile_path.exists()
        ):
            self.profile_path = get_profiles_dir() / self.os_profile

        data = load_profile(self.os_profile, self.profile_path.parent)

        self.context = data.get("context")
        self.dynamic_files = data.get("dynamic_files", {})
        self.honeytokens = data.get("honeytokens", [])

        # Use shared backend if available, otherwise create new one
        self.backend = data.get("shared_backend")
        if not self.backend:
            db_path = data.get("backend_path")
            if db_path:
                self.backend = SqliteBackend(db_path)

        # Initialize memory overlay with pre-calculated base structure
        base_overlay = data.get("base_overlay", {})
        self.memory_overlay = ChainMap({}, base_overlay)

    def get_node(self, path: str) -> Optional[Node]:
        """Resolve a path to a VirtualFile or VirtualDirectory node."""
        self._ensure_system_init()
        path = self.resolve(path)
        if path in self.deleted_paths:
            return None

        if path in self.memory_overlay:
            config = self.memory_overlay[path]
            return (
                VirtualDirectory(posixpath.basename(path), path, self, config)
                if config.get("type") == "dir"
                else VirtualFile(posixpath.basename(path), path, self, config)
            )

        if path in self.dynamic_files:
            return VirtualFile(posixpath.basename(path), path, self, self.dynamic_files[path])

        if self.backend:
            backend_config = self.backend.get_config(path)
            if backend_config:
                if backend_config.get("type") == "dir":
                    return VirtualDirectory(
                        posixpath.basename(path) or "/", path, self, backend_config
                    )
                return VirtualFile(posixpath.basename(path), path, self, backend_config)

        if self.is_dir(path):
            return VirtualDirectory(posixpath.basename(path) or "/", path, self)

        if self.exists(path):
            return VirtualFile(posixpath.basename(path), path, self)

        return None

    def exists(self, path: str) -> bool:
        self._ensure_system_init()
        path = self.resolve(path)
        if path in self.deleted_paths:
            return False
        if (
            path == "/"
            or path in self.memory_overlay
            or path in self.dynamic_files
            or (self.backend and self.backend.exists(path))
        ):
            return True
        return False

    def is_dir(self, path: str) -> bool:
        self._ensure_system_init()
        path = self.resolve(path)
        if path in self.deleted_paths:
            return False
        if path == "/":
            return True

        if path in self.memory_overlay:
            return bool(self.memory_overlay[path].get("type") == "dir")

        if path in self.dynamic_files:
            return str(self.dynamic_files[path].get("type")) == "dir"

        if self.backend and self.backend.is_dir(path):
            return True

        return False

    def is_file(self, path: str) -> bool:
        self._ensure_system_init()
        path = self.resolve(path)
        if path in self.deleted_paths:
            return False
        if path in self.memory_overlay:
            return bool(self.memory_overlay[path].get("type") == "file")
        if path in self.dynamic_files:
            ftype = self.dynamic_files[path].get("type", "file")
            return ftype in ("file", "generated")

        if self.backend:
            config = self.backend.get_config(path)
            if config:
                ftype = config.get("type", "file")
                return ftype in ("file", "generated")

        if not self.exists(path):
            return False
        return not self.is_dir(path)

    def list_dir(self, path: str) -> List[str]:
        self._ensure_system_init()
        path = self.resolve(path)
        if path in self.deleted_paths or not self.is_dir(path):
            return []

        contents = set()

        if self.backend:
            for item in self.backend.list_dir(path):
                contents.add(item)

        prefix = path.rstrip("/") + "/"
        for p in self.dynamic_files:
            if p.startswith(prefix):
                rel = p[len(prefix) :].split("/")[0]
                contents.add(rel)

        for p in self.memory_overlay:
            if p.startswith(prefix):
                rel = p[len(prefix) :].split("/")[0]
                contents.add(rel)

        return sorted([c for c in contents if posixpath.join(path, c) not in self.deleted_paths])

    def _record_file_op(self, op: str, path: str):
        """Record a file operation for auditing and statistics."""
        if self.audit_callback:
            self.audit_callback(op, path, self)
        if self.stats:
            self.stats.on_file_op(op, path)
        if self.session_mgr:
            self.session_mgr.record_file_op(self.session_id)

    def get_content(self, path: str, args: Optional[Dict[str, Any]] = None) -> Union[str, bytes]:
        self._ensure_system_init()
        path = self.resolve(path)
        if path in self.deleted_paths:
            return ""

        self._record_file_op("read", path)

        if path in self.memory_overlay:
            content = self.memory_overlay[path].get("content", "")
            return content if isinstance(content, (str, bytes)) else str(content)

        if path in self.dynamic_files:
            return self._get_dynamic_content(path, args)

        if self.backend:
            # Separated content fetching from metadata
            content = self.backend.get_content(path)
            if content is not None:
                return self._render(content)

        return ""

    def _get_dynamic_content(self, path: str, args: Optional[Dict[str, Any]]) -> Union[str, bytes]:
        """Source content from a dynamic file provider."""
        config = self.dynamic_files[path]
        provider = PROVIDERS.get(config.get("provider"))
        if provider:
            combined_args = {**config.get("args", {}), **(args or {})}
            return provider(self.context, combined_args)

        if "content" in config:
            return self._render(config["content"])
        return ""

    def get_overlay_size(self) -> int:
        """Calculate total size of the memory overlay (uncompressed)."""
        total = 0
        for node in self.memory_overlay.maps[0].values():
            content = node.get("content", "")
            if isinstance(content, bytes):
                total += len(content)
            else:
                total += len(str(content))
        return total

    def mkfile(
        self,
        path: str,
        content: Union[str, bytes] = "",
        owner="root",
        group="root",
        perm="-rw-r--r--",
    ):
        path = self.resolve(path)
        if len(self.memory_overlay.maps[0]) >= self.max_nodes:
            return None

        if self.get_overlay_size() + len(content) > self.max_overlay_size:
            return None

        parent_path = posixpath.dirname(path)
        if parent_path != path:
            if not self.exists(parent_path) or not self.is_dir(parent_path):
                return None

        self.memory_overlay[path] = {
            "type": "file",
            "content": content,
            "owner": owner,
            "group": group,
            "perm": perm,
            "size": len(content) if isinstance(content, (str, bytes)) else 0,
            "mtime": datetime.datetime.now(),
        }
        if path in self.deleted_paths:
            self.deleted_paths.remove(path)
        if self.stats:
            self.stats.on_file_op("write", path)
        if self.session_mgr:
            self.session_mgr.record_file_op(self.session_id)
        return VirtualFile(posixpath.basename(path), path, self)

    def mkdir_p(self, path: str, owner="root", group="root", perm="drwxr-xr-x"):
        path = self.resolve(path)
        parts = [p for p in path.split("/") if p]
        current = "/"
        for part in parts:
            current = posixpath.join(current, part)
            if not self.exists(current) or self.is_file(current):
                if len(self.memory_overlay.maps[0]) >= self.max_nodes:
                    return False
                self.memory_overlay[current] = {
                    "type": "dir",
                    "owner": owner,
                    "group": group,
                    "perm": perm,
                    "mtime": datetime.datetime.now(),
                }
                if current in self.deleted_paths:
                    self.deleted_paths.remove(current)
        return True

    def chmod(self, path: str, perm: str) -> bool:
        """Change permissions of a file or directory, persisting in memory overlay."""
        path = self.resolve(path)
        node = self.get_node(path)
        if not node:
            return False

        if path not in self.memory_overlay.maps[0]:
            self.memory_overlay[path] = {
                "type": "dir" if node.is_dir() else "file",
                "owner": node.owner,
                "group": node.group,
                "size": node.size,
                "mtime": node.mtime,
                "perm": node.perm,
                "content": self.get_content(path) if node.is_file() else "",
            }

        self.memory_overlay[path]["perm"] = perm
        return True

    def chown(self, path: str, owner: Optional[str] = None, group: Optional[str] = None) -> bool:
        """Change ownership of a file or directory, persisting in memory overlay."""
        path = self.resolve(path)
        node = self.get_node(path)
        if not node:
            return False

        if path not in self.memory_overlay.maps[0]:
            self.memory_overlay[path] = {
                "type": "dir" if node.is_dir() else "file",
                "owner": node.owner,
                "group": node.group,
                "size": node.size,
                "mtime": node.mtime,
                "content": self.get_content(path) if node.is_file() else "",
                "perm": node.perm,
            }

        if owner:
            self.memory_overlay[path]["owner"] = owner
        if group:
            self.memory_overlay[path]["group"] = group
        return True

    def remove(self, path: str) -> bool:
        path = self.resolve(path)
        if path == "/" or not self.exists(path):
            return False

        self.deleted_paths.add(path)
        if path in self.memory_overlay:
            del self.memory_overlay[path]

        if self.audit_callback:
            self.audit_callback("delete", path, self)
        if self.stats:
            self.stats.on_file_op("delete", path)
        if self.session_mgr:
            self.session_mgr.record_file_op(self.session_id)
        return True

    def get_owner(self, path: str) -> str:
        """Get the owner of a file or directory."""
        node = self.get_node(path)
        res = getattr(node, "owner", "root")
        return str(res)

    def resolve(self, path: str) -> str:
        if not path:
            return "/"
        res = posixpath.normpath(path)
        if res.startswith("//") and not res.startswith("///"):
            res = "/" + res.lstrip("/")
        return res

    def copy(self, src: str, dst: str, recursive: bool = False) -> bool:
        src = self.resolve(src)
        dst = self.resolve(dst)

        if not self.exists(src):
            return False

        # If destination is an existing directory, move/copy INTO it
        if self.exists(dst) and self.is_dir(dst):
            dst = posixpath.join(dst, posixpath.basename(src))

        if self.is_dir(src):
            if not recursive:
                return False

            if not self.exists(dst):
                self.mkdir_p(dst)
            elif self.is_file(dst):
                return False

            for item in self.list_dir(src):
                # When calling recursively, the sub-items are already targeted correctly
                # BUT we must pass recursive=True and NOT trigger the "into existing" logic again for children
                self._copy_recursive(posixpath.join(src, item), posixpath.join(dst, item))
            return True
        else:
            self.mkfile(dst, content=self.get_content(src))
            return True

    def _copy_recursive(self, src: str, dst: str) -> bool:
        """Internal helper for recursive copy that doesn't re-check destination logic."""
        if self.is_dir(src):
            if not self.exists(dst):
                self.mkdir_p(dst)
            for item in self.list_dir(src):
                self._copy_recursive(posixpath.join(src, item), posixpath.join(dst, item))
        else:
            self.mkfile(dst, content=self.get_content(src))
        return True

    def move(self, src: str, dst: str) -> bool:
        src = self.resolve(src)
        dst = self.resolve(dst)

        if not self.exists(src):
            return False

        if self.copy(src, dst, recursive=True):
            return self.remove(src)
        return False

    def _render(self, content: Any) -> Union[str, bytes]:
        if not content:
            return ""

        if isinstance(content, bytes):
            return content

        if not self.context or not isinstance(content, str):
            return str(content)

        # Check if we have a cached template
        cache_key = (self.os_profile, content)
        template = self._template_cache.get(cache_key)

        if not template:
            try:
                template = self.jinja_env.from_string(content)
                with self._cache_lock:
                    if len(self._template_cache) > 1000:  # Simple eviction
                        self._template_cache.clear()
                    self._template_cache[cache_key] = template
            except Exception:
                return content

        try:
            rendered = template.render(**self.context.to_dict())
            return cast(str, rendered)
        except Exception:
            return content
