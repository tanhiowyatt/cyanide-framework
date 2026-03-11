import asyncio
import re
import os
from typing import Any, Dict, List, Optional, Tuple

import asyncssh

class SCPHandler:
    """
    Handler for SCP requests (scp -t, scp -f).
    Implements the basic SCP protocol over a channel.
    """

    def __init__(self, session: Any):
        self.session = session # SSHSession instance
        self.honeypot = session.honeypot
        self.channel = session.channel
        self.fs = session.fs
        self.src_ip = session.src_ip
        self.username = session.username
        self.session_id = session.session_id
        self.logger = self.honeypot.logger

    def _log_op(self, op: str, path: str, success: bool = True, extra: Optional[Dict] = None):
        log_data = {
            "protocol": "scp",
            "src_ip": self.src_ip,
            "username": self.username,
            "op": op,
            "path": path,
            "success": success
        }
        if extra:
            log_data.update(extra)
        
        self.logger.log_event(self.session_id, "scp_op", log_data)

    async def handle(self, command: str) -> int:
        """
        Main entry point for handling an SCP command.
        Returns the exit code.
        """
        # Parse scp command line
        # Typical: scp -t /path/to/dest
        #          scp -f /path/to/src
        
        sink_mode = '-t' in command
        source_mode = '-f' in command
        
        # Simple extraction of the path
        parts = command.split()
        try:
            # Path is usually the last argument that doesn't start with -
            path = [p for p in parts if not p.startswith('-') and p != 'scp'][-1]
        except IndexError:
            path = "/"

        if sink_mode:
            self._log_op("sink_mode_request", path)
            return await self._handle_sink(path)
        elif source_mode:
            self._log_op("source_mode_request", path)
            return await self._handle_source(path)
        else:
            self._log_op("unknown_scp_request", command, success=False)
            return 1

    async def _handle_sink(self, dest_path: str) -> int:
        """Attacker -> Honeypot (Upload)"""
        # Ack start
        self.channel.write(b'\0')
        
        try:
            while not self.channel.at_eof():
                line_bytes = await self.channel.readuntil(b'\n')
                if not line_bytes:
                    break
                
                line = line_bytes.decode().strip()
                if not line:
                    continue
                
                # SCP command types:
                # C modes size name (File)
                # D modes 0 name (Directory)
                # E (End directory)
                
                if line.startswith('C'):
                    # C0644 123 test.txt
                    match = re.match(r'C(\d+) (\d+) (.+)', line)
                    if match:
                        modes, size, name = match.groups()
                        size = int(size)
                        full_path = os.path.join(dest_path, name)
                        
                        # Check upload limits
                        max_size = self.honeypot.config['ssh'].get('max_upload_size_mb', 50) * 1024 * 1024
                        if size > max_size:
                            self.channel.write(b'\x01SCP upload size limit exceeded\n')
                            self._log_op("upload_rejected", full_path, extra={"reason": "size_limit", "size": size})
                            return 1
                        
                        # Ack line
                        self.channel.write(b'\0')
                        
                        # Read file data
                        content = await self._read_fixed(size)
                        
                        # Ack data
                        self.channel.write(b'\0')
                        
                        # Skip terminating null from client
                        await self.channel.read(1)
                        
                        # Save to VFS
                        self.fs.mkfile(full_path, content=content.decode('utf-8', 'ignore'))
                        
                        # Quarantining
                        self.honeypot.save_quarantine_file(
                            name,
                            content,
                            self.session_id,
                            self.src_ip
                        )
                        
                        self._log_op("upload_complete", full_path, extra={"size": size})
                elif line.startswith('D'):
                    # Directory creation (simplified)
                    match = re.match(r'D(\d+) 0 (.+)', line)
                    if match:
                        modes, name = match.groups()
                        new_dir = os.path.join(dest_path, name)
                        self.fs.mkdir_p(new_dir)
                        self.channel.write(b'\0')
                        dest_path = new_dir # Descend
                        self._log_op("mkdir", new_dir)
                elif line.startswith('E'):
                    # End directory
                    self.channel.write(b'\0')
                    dest_path = os.path.dirname(dest_path) # Ascend
                
            return 0
        except Exception as e:
            self._log_op("error", dest_path, success=False, extra={"error": str(e)})
            return 1

    async def _handle_source(self, src_path: str) -> int:
        """Honeypot -> Attacker (Download)"""
        if not self.honeypot.config['ssh'].get('allow_download', True):
            self.channel.write(b'\x01SCP downloads disabled\n')
            self._log_op("download_rejected", src_path, extra={"reason": "disabled"})
            return 1

        try:
            # Wait for initial null ack from client
            await self.channel.read(1)
            
            if not self.fs.exists(src_path):
                self.channel.write(b'\x01SCP no such file\n')
                return 1
            
            if self.fs.is_file(src_path):
                content = self.fs.get_content(src_path).encode()
                size = len(content)
                name = os.path.basename(src_path)
                
                # Send C command
                header = f"C0644 {size} {name}\n".encode()
                self.channel.write(header)
                
                # Wait for ack
                await self.channel.read(1)
                
                # Send data
                self.channel.write(content)
                self.channel.write(b'\0') # Terminator
                
                # Wait for ack
                await self.channel.read(1)
                
                self._log_op("download_complete", src_path, extra={"size": size})
            else:
                # Directory support would go here, currently limited to files for simplicity
                self.channel.write(b'\x01SCP directory downloads not yet implemented\n')
                return 1
                
            return 0
        except Exception as e:
            self._log_op("error", src_path, success=False, extra={"error": str(e)})
            return 1

    async def _read_fixed(self, size: int) -> bytes:
        data = b''
        while len(data) < size:
            chunk = await self.channel.read(size - len(data))
            if not chunk:
                break
            data += chunk
        return data
