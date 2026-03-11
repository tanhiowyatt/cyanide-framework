import asyncio
import os
import time
import logging
import traceback
from typing import Any, Dict, List, Optional, Tuple, Union, AsyncIterator

import asyncssh

from cyanide.vfs.engine import FakeFilesystem

class CyanideSFTPHandler(asyncssh.SFTPServer):
    """
    SFTP server implementation for Cyanide honeypot.
    Bridges asyncssh SFTP requests to the FakeFilesystem (VFS).
    """

    def __init__(self, chan: asyncssh.SSHServerChannel):
        super().__init__(chan)
        self.chan = chan
        self.conn = chan.get_connection()
        
        # Get the factory we attached in SSHServerFactory.connection_made
        self.server_factory = getattr(self.conn, 'cyanide_factory', None)
        
        if self.server_factory:
            self.honeypot = self.server_factory.honeypot
            self.fs = self.server_factory.fs
            self.session_id = "conn_" + self.server_factory.conn_id
            self.src_ip = self.server_factory.src_ip
        else:
            # Fallback if things go wrong
            raise RuntimeError("CyanideSFTPHandler requires cyanide_factory on connection")
        
        self.username = self.conn.get_extra_info('username') or 'root'
        self.cyanide_logger = self.honeypot.logger

    def _decode_path(self, path: Union[str, bytes]) -> str:
        if isinstance(path, bytes):
            return path.decode('utf-8', 'ignore')
        return path

    def _log_op(self, op: str, path: str, success: bool = True, extra: Optional[Dict] = None):
        log_data = {
            "protocol": "sftp",
            "src_ip": self.src_ip,
            "username": self.username,
            "op": op,
            "path": path,
            "success": success
        }
        if extra:
            log_data.update(extra)
        
        self.cyanide_logger.log_event(self.session_id, "sftp_op", log_data)

    async def realpath(self, path: Union[str, bytes]) -> Union[str, bytes]:
        return path or (b'.' if isinstance(path, bytes) else '.')

    async def scandir(self, path: Union[str, bytes]) -> AsyncIterator[asyncssh.SFTPName]:
        p = self._decode_path(path)
        try:
            names = self.fs.list_dir(p)
            for name in names:
                full_path = os.path.join(p, name)
                node = self.fs.get_node(full_path)
                attrs = self._get_attrs(node) if node else asyncssh.SFTPAttrs()
                
                if isinstance(path, bytes):
                    yield asyncssh.SFTPName(name.encode('utf-8'), attrs=attrs)
                else:
                    yield asyncssh.SFTPName(name, attrs=attrs)
            
            self._log_op("scandir", p)
        except Exception as e:
            self._log_op("scandir", p, success=False, extra={"error": str(e)})
            raise asyncssh.SFTPNoSuchFile(str(e))

    async def stat(self, path: Union[str, bytes]) -> asyncssh.SFTPAttrs:
        p = self._decode_path(path)
        node = self.fs.get_node(p)
        if not node:
            self._log_op("stat", p, success=False, extra={"error": "no such file"})
            raise asyncssh.SFTPNoSuchFile()
        
        self._log_op("stat", p)
        return self._get_attrs(node)

    async def lstat(self, path: Union[str, bytes]) -> asyncssh.SFTPAttrs:
        return await self.stat(path)

    async def fstat(self, file_obj: Any) -> asyncssh.SFTPAttrs:
        return await self.stat(file_obj['path'])

    async def open(self, path: Union[str, bytes], flags: int, attrs: asyncssh.SFTPAttrs) -> Any:
        p = self._decode_path(path)
        self._log_op("open", p, extra={"flags": flags})
        
        is_write = flags & (asyncssh.SFTPO_WRITE | asyncssh.SFTPO_CREAT | asyncssh.SFTPO_TRUNC)
        
        ssh_conf = self.honeypot.config.get("ssh", {})
        if is_write and not ssh_conf.get("allow_upload", True):
            raise asyncssh.SFTPPermissionDenied("Uploads disabled")
        
        if not is_write and not ssh_conf.get("allow_download", True):
            raise asyncssh.SFTPPermissionDenied("Downloads disabled")

        if is_write:
            content = b''
            if not (flags & asyncssh.SFTPO_TRUNC) and self.fs.exists(p):
                raw = self.fs.get_content(p)
                content = raw.encode('utf-8', 'ignore') if isinstance(raw, str) else (raw or b'')
            
            return {
                'path': p,
                'buffer': bytearray(content),
                'is_write': True
            }
        else:
            if not self.fs.exists(p):
                raise asyncssh.SFTPNoSuchFile()
            raw = self.fs.get_content(p)
            content = raw.encode('utf-8', 'ignore') if isinstance(raw, str) else (raw or b'')
            return {
                'path': p,
                'buffer': bytearray(content),
                'is_write': False
            }

    async def read(self, file_obj: Any, offset: int, size: int) -> bytes:
        buffer = file_obj['buffer']
        end = min(offset + size, len(buffer))
        return bytes(buffer[offset:end])

    async def write(self, file_obj: Any, offset: int, data: bytes):
        if not file_obj['is_write']:
            raise asyncssh.SFTPBadMessage("File opened for reading")
        
        ssh_conf = self.honeypot.config.get("ssh", {})
        session_limit = ssh_conf.get("max_total_upload_mb_per_session", 200) * 1024 * 1024
        if len(file_obj['buffer']) + len(data) > session_limit:
             raise asyncssh.SFTPPermissionDenied("Session upload limit exceeded")

        buffer = file_obj['buffer']
        end = offset + len(data)
        if end > len(buffer):
            buffer.extend(b'\0' * (end - len(buffer)))
        buffer[offset:end] = data

    async def close(self, file_obj: Any):
        path = file_obj['path']
        if file_obj['is_write']:
            content = bytes(file_obj['buffer'])
            self.fs.mkfile(path, content=content.decode('utf-8', 'ignore'))
            
            self.honeypot.save_quarantine_file(
                os.path.basename(path),
                content,
                self.session_id,
                self.src_ip
            )
            
            self._log_op("upload_complete", path, extra={"size": len(content)})
        else:
            self._log_op("close", path)

    async def mkdir(self, path: Union[str, bytes], attrs: asyncssh.SFTPAttrs):
        p = self._decode_path(path)
        self.fs.mkdir_p(p)
        self._log_op("mkdir", p)

    async def remove(self, path: Union[str, bytes]):
        p = self._decode_path(path)
        if self.fs.remove(p):
            self._log_op("remove", p)
        else:
            self._log_op("remove", p, success=False)
            raise asyncssh.SFTPNoSuchFile()

    async def rmdir(self, path: Union[str, bytes]):
        await self.remove(path)

    async def rename(self, oldpath: Union[str, bytes], newpath: Union[str, bytes], flags: int = 0):
        op = self._decode_path(oldpath)
        np = self._decode_path(newpath)
        if self.fs.move(op, np):
            self._log_op("rename", op, extra={"new_path": np})
        else:
            self._log_op("rename", op, success=False, extra={"new_path": np})
            raise asyncssh.SFTPNoSuchFile()

    def _get_attrs(self, node: Any) -> asyncssh.SFTPAttrs:
        attrs = asyncssh.SFTPAttrs()
        attrs.size = node.size if hasattr(node, 'size') else 0
        attrs.permissions = self._parse_mode(node.perm)
        
        if hasattr(node, 'mtime'):
            if isinstance(node.mtime, (int, float)):
                attrs.atime = attrs.mtime = int(node.mtime)
            elif hasattr(node.mtime, 'timestamp'):
                attrs.atime = attrs.mtime = int(node.mtime.timestamp())
        
        attrs.uid = 0 if node.owner == 'root' else 1000
        attrs.gid = 0 if node.group == 'root' else 1000
        return attrs

    def _parse_mode(self, perm_str: str) -> int:
        mode = 0
        if perm_str.startswith('d'):
            mode |= 0o40000
        else:
            mode |= 0o100000
            
        mapping = {'r': 4, 'w': 2, 'x': 1, '-': 0}
        parts = [perm_str[1:4], perm_str[4:7], perm_str[7:10]]
        
        res = 0
        for i, part in enumerate(parts):
            val = sum(mapping.get(c, 0) for c in part)
            res = (res << 3) | val
            
        return mode | res
