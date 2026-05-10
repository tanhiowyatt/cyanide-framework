import asyncio
import logging
from typing import Dict, Optional, Tuple

from cyanide.core.emulator import ShellEmulator
from cyanide.vfs.engine import FakeFilesystem

logger = logging.getLogger("cyanide.session_pool")


class SessionPool:
    """
    Manages a pool of pre-initialized (pre-warmed) sessions to handle high-concurrency spikes.
    Each session consists of a FakeFilesystem and a ShellEmulator.
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        pool_conf = self.config.get("session_pool", {})
        self.enabled = pool_conf.get("enabled", False)
        self.max_size = pool_conf.get("max_size", 20)
        self.profiles = pool_conf.get("profiles", ["debian"])

        # profile_name -> list of (fs, shell)
        self._pools: Dict[str, asyncio.Queue[Tuple[FakeFilesystem, ShellEmulator]]] = {}
        for profile in self.profiles:
            self._pools[profile] = asyncio.Queue(maxsize=self.max_size)

        self._fill_task: Optional[asyncio.Task] = None

    def start(self):
        """Start the background task to fill the pool."""
        if self.enabled and self._fill_task is None:
            self._fill_task = asyncio.create_task(self._fill_worker())
            logger.info(f"SessionPool started for profiles: {self.profiles}")

    async def stop(self):
        """Stop the background task."""
        if self._fill_task:
            self._fill_task.cancel()
            try:
                await self._fill_task
            except asyncio.CancelledError:
                raise
            finally:
                self._fill_task = None

    async def get_session(
        self, profile: str, username: str = "root"
    ) -> Optional[Tuple[FakeFilesystem, ShellEmulator]]:
        """Get a pre-warmed session from the pool (async, waits if empty)."""
        if not self.enabled or profile not in self._pools:
            return None

        # This will wait if the queue is empty until a worker fills it
        fs, shell = await self._pools[profile].get()
        self._reconfigure_session(shell, username)
        return fs, shell

    def get_session_sync(
        self, profile: str, username: str = "root"
    ) -> Optional[Tuple[FakeFilesystem, ShellEmulator]]:
        """Get a pre-warmed session from the pool (sync)."""
        if not self.enabled or profile not in self._pools:
            return None

        try:
            # Queue.get_nowait() is safe to call from sync code if we don't block
            fs, shell = self._pools[profile].get_nowait()
            self._reconfigure_session(shell, username)
            return fs, shell
        except (asyncio.QueueEmpty, RuntimeError):
            return None

    def _reconfigure_session(self, shell: ShellEmulator, username: str):
        """Update session state for a specific user."""
        if shell.username != username:
            shell.username = username
            if username == "admin":
                shell.cwd = "/home/admin"
            elif username == "root":
                shell.cwd = "/root"
            else:
                shell.cwd = f"/home/{username}"
            shell.env["HOME"] = shell.cwd
            shell.env["USER"] = username

    async def _fill_worker(self):
        """Background worker to keep the pools filled."""
        while True:
            try:
                for profile, queue in self._pools.items():
                    if not queue.full():
                        # Create a new session
                        # We use a helper thread to not block the event loop with sync VFS/Shell init
                        fs, shell = await asyncio.to_thread(self._create_session, profile)
                        try:
                            queue.put_nowait((fs, shell))
                            logger.debug(f"Pre-warmed session added for '{profile}'")
                        except asyncio.QueueFull:
                            pass

                await asyncio.sleep(1)  # Check every second
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"SessionPool worker error: {e}")
                await asyncio.sleep(5)

    def _create_session(self, profile: str) -> Tuple[FakeFilesystem, ShellEmulator]:
        """Synchronous creation of a session."""
        fs = FakeFilesystem(os_profile=profile, config=self.config)
        shell = ShellEmulator(fs, username="root", config=self.config)
        return fs, shell
