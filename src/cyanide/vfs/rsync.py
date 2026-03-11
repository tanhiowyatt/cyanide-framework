import asyncio
import logging
from typing import Any, Dict, List, Optional

class RsyncHandler:
    """
    Handler for rsync requests (rsync --server).
    Provides realistic logging and minimal handshake.
    """

    def __init__(self, session: Any):
        self.session = session
        self.honeypot = session.honeypot
        self.channel = session.channel
        self.src_ip = session.src_ip
        self.username = session.username
        self.session_id = session.session_id
        self.logger = self.honeypot.logger

    def _log_op(self, op: str, command: str, success: bool = True, extra: Optional[Dict] = None):
        log_data = {
            "protocol": "rsync",
            "src_ip": self.src_ip,
            "username": self.username,
            "op": op,
            "command": command,
            "success": success
        }
        if extra:
            log_data.update(extra)
        
        self.logger.log_event(self.session_id, "rsync_op", log_data)

    async def handle(self, command: str) -> int:
        """
        Detects and logs rsync server attempts.
        Returns the exit code.
        """
        # rsync commands usually look like:
        # rsync --server --sender -vlogDtprze.iLsfxC . /path/to/src
        # rsync --server -vlogDtprze.iLsfxC . /path/to/dest
        
        is_sender = '--sender' in command
        
        self._log_op("server_mode_request", command, extra={"is_sender": is_sender})
        
        try:
            # The rsync protocol is complex. For a honeypot, we want to:
            # 1. Exchange protocol version.
            # 2. Log the activity.
            # 3. Potentially fail with a realistic error.
            
            # Send protocol version (e.g., 31)
            # Format: <version_int>\n
            self.channel.write(b'31\n')
            
            # Wait for client version
            client_version_bytes = await self.channel.read(10)
            client_version = client_version_bytes.decode().strip() if client_version_bytes else "unknown"
            
            self._log_op("handshake", command, extra={"client_rsync_version": client_version})
            
            # For now, we return a realistic error message to the client
            # as implementing the full rsync transfer protocol is out of scope 
            # for a base implementation and could be fragile.
            # Real rsync servers often fail if the exact binary isn't matched or modules aren't found.
            
            error_msg = f"rsync: connection unexpectedly closed (root@server:{self.src_ip})\n"
            self.channel.write_stderr(error_msg.encode())
            
            return 12 # rsync error code for communication error
            
        except Exception as e:
            self._log_op("error", command, success=False, extra={"error": str(e)})
            return 1
