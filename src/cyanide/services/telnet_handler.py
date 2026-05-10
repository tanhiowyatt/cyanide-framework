import asyncio
import traceback
import uuid
from typing import Any, Dict, Optional, cast

from cyanide.core.emulator import ShellEmulator


class TelnetHandler:
    """
    Advanced Telnet Handler with History Support.
    Enhanced stability and session logging.
    """

    LOGIN_PROMPT = b"Login: "
    PASSWORD_PROMPT = b"Password: "

    def __init__(self, server, config: Dict):
        self.server = server
        self.config = config
        self.logger = server.logger
        self.stats = server.stats
        self.services = server.services
        self.session_timeout = config.get("telnet", {}).get("timeout", 600)  # Increased to 10 mins

    async def _read_byte(self, reader, timeout: Optional[float] = None) -> Optional[int]:
        """Helper to read a single byte and return its integer value."""
        try:
            b = await asyncio.wait_for(reader.read(1), timeout=timeout or self.session_timeout)
            if not b:
                return None
            return ord(b[0]) if isinstance(b, str) else b[0]
        except Exception:
            return None

    async def _read_char(self, reader) -> Optional[str]:
        """Reads one character or control code from the stream."""
        while True:
            val = await self._read_byte(reader)
            if val is None:
                return None

            if val == 255:
                await self._process_telnet_iac(reader)
                continue

            # Convert back to bytes for decoding
            b = bytes([val])
            return self._decode_char(b)

    async def _process_telnet_iac(self, reader):
        """Handle Telnet Interpret As Command (IAC) sequences."""
        cmd = await self._read_byte(reader, timeout=0.1)
        if cmd is None:
            return

        if 251 <= cmd <= 254:
            # 3-byte sequences (WILL/WONT/DO/DONT)
            await self._read_byte(reader, timeout=0.1)
        elif cmd == 250:
            # Subnegotiation (SB)
            await self._process_subnegotiation(reader)

    async def _process_subnegotiation(self, reader):
        """Process Telnet SB (Subnegotiation) until SE (Subnegotiation End)."""
        while True:
            val = await self._read_byte(reader, timeout=0.1)
            if val is None:
                break
            if val == 255:
                next_val = await self._read_byte(reader, timeout=0.1)
                if next_val in (None, 240):  # SE or EOF
                    break

    def _decode_char(self, b: bytes | str) -> Optional[str]:
        """Decode byte or string from the stream into a character."""
        if isinstance(b, bytes):
            try:
                return b.decode("utf-8", "ignore")
            except Exception:
                return None
        return b

    async def _consume_eol(self, reader):
        """Standard Telnet EOL consumer (swallows follow-up \n or \0)."""
        try:
            # Check if another byte is waiting (non-blocking)
            await asyncio.wait_for(reader.read(1), timeout=0.1)
        except Exception:
            pass

    async def _read_line_advanced(
        self, reader, writer, prompt: str, shell: Optional[ShellEmulator] = None
    ) -> str:
        """Advanced line reader with History navigation (Arrow Keys) support."""
        state: dict[str, Any] = {"line": "", "ptr": -1, "buffer": ""}

        while True:
            char = await self._read_char(reader)
            if char is None:
                break
            if not char:
                continue

            if char in ("\r", "\n"):
                writer.write(b"\r\n")
                await writer.drain()
                await self._consume_eol(reader)
                return cast(str, state["line"])

            if char in ("\x08", "\x7f"):
                await self._handle_backspace(writer, state)
                continue

            if char == "\x1b":
                await self._handle_arrow_keys(reader, writer, prompt, shell, state)
                continue

            if ord(char) >= 32 or char == "\t":
                state["line"] = str(state["line"]) + char
                writer.write(char.encode("utf-8"))
                await writer.drain()

        return str(state["line"])

    async def _handle_backspace(self, writer, state: dict):
        """Handle backspace character."""
        if state["line"]:
            state["line"] = state["line"][:-1]
            writer.write(b"\b \b")
            await writer.drain()

    async def _handle_arrow_keys(self, reader, writer, prompt, shell, state):
        """Handle ANSI escape sequences for arrow keys (History navigation)."""
        try:
            bracket = await asyncio.wait_for(self._read_char(reader), timeout=0.1)
            if bracket != "[":
                return
            code = await asyncio.wait_for(self._read_char(reader), timeout=0.1)
            if not shell or not shell.history:
                return

            if code == "A":  # UP
                if state["ptr"] == -1:
                    state["buffer"] = state["line"]
                state["ptr"] = min(state["ptr"] + 1, len(shell.history) - 1)
                new_line = shell.history[-(state["ptr"] + 1)]
                await self._refresh_line_ui(writer, prompt, state["line"], new_line)
                state["line"] = new_line
            elif code == "B":  # DOWN
                if state["ptr"] > 0:
                    state["ptr"] -= 1
                    new_line = shell.history[-(state["ptr"] + 1)]
                elif state["ptr"] == 0:
                    state["ptr"] = -1
                    new_line = state["buffer"]
                else:
                    return
                await self._refresh_line_ui(writer, prompt, state["line"], new_line)
                state["line"] = new_line
        except Exception:
            pass

    async def _refresh_line_ui(self, writer, prompt, old_line, new_line):
        """Redraw the line with new content from history."""
        # Clear line: Carriage return + spaces + Carriage return
        writer.write(b"\r" + b" " * (len(prompt) + len(old_line)) + b"\r")
        writer.write(prompt.encode() + new_line.encode())
        await writer.drain()

    async def _read_line_simple(self, reader, writer, echo=True, mask=False) -> str:
        """Simple line reader for Login/Password with EOL robustness."""
        line_str = ""
        while True:
            char = await self._read_char(reader)
            if char is None:
                break
            if char in ("\r", "\n"):
                await self._handle_simple_eol(reader, writer, char, echo)
                return line_str

            if ord(char) >= 32 or char == "\t":
                line_str += char
                if echo and not mask:
                    writer.write(char.encode("utf-8"))
                    await writer.drain()
        return line_str

    async def _handle_simple_eol(self, reader, writer, char, echo):
        """Handle EOL for simple reader, swallowing follow-up \n or \0."""
        if echo:
            writer.write(b"\r\n")
            await writer.drain()

        # Consume the other half of \r\n if it exists
        if char == "\r":
            try:
                # Use short timeout to check for follow-up \n or \0
                # Must use reader.read(1) directly to avoid IAC loops in _read_char
                next_b = await asyncio.wait_for(reader.read(1), timeout=0.05)
                if next_b and next_b not in (b"\n", "\n", b"\0", "\0"):
                    # Not EOL, but in simple reader we don't have a pushback buffer
                    pass
            except Exception:
                pass

    async def handle_connection(self, reader, writer):
        """Main entry point."""
        src_ip = writer.get_extra_info("peername")[0]
        session_id = "telnet_" + str(uuid.uuid4())[:8]
        self.stats.on_connect("telnet", src_ip)
        self.services.session.register_session(src_ip, session_id=session_id)

        try:
            # Master Mode Negotiation
            writer.write(bytes([255, 251, 1]))  # WILL ECHO
            writer.write(bytes([255, 251, 3]))  # WILL SUPPRESS_GO_AHEAD
            await writer.drain()

            # Send banner immediately
            banner_conf = (
                self.config.get("telnet", {}).get("banner", "")
                or "Red Hat Enterprise Linux 9.3 (Plow)\nKernel \\r on an \\m\n"
            )
            hostname = self.config.get("hostname", "server")
            banner = (
                banner_conf.replace("\\n", hostname).replace("\\l", "pts/0").replace("\n", "\r\n")
            )
            if not banner.endswith("\r\n"):
                banner += "\r\n"
            writer.write(banner.encode())
            await writer.drain()

            # Username
            writer.write(self.LOGIN_PROMPT)
            await writer.drain()
            username = await self._read_line_simple(reader, writer, echo=True)

            # Password
            writer.write(self.PASSWORD_PROMPT)
            await writer.drain()
            password = await self._read_line_simple(reader, writer, echo=False)

            success = self.server.is_valid_user(username, password)
            self.stats.on_auth(username, password, success)

            self.logger.log_event(
                session_id,
                "auth",
                {"protocol": "telnet", "src_ip": src_ip, "username": username, "success": success},
            )

            if success:
                writer.write(b"\r\n")

                def q_hook(f, c):
                    if hasattr(self.server, "save_quarantine_file"):
                        self.server.save_quarantine_file(f, c, session_id, src_ip)

                fs = self.server.get_filesystem(session_id, src_ip, username)
                shell = ShellEmulator(
                    fs,
                    username,
                    quarantine_callback=q_hook,
                    config=self.config,
                    logger=self.logger,
                    session_id=session_id,
                    src_ip=src_ip,
                    analytics=getattr(self.server, "analytics", None),
                )
                await self._run_shell(reader, writer, shell, username, session_id)
            else:
                writer.write(b"Login incorrect\r\n")
                await writer.drain()

        except (ConnectionResetError, BrokenPipeError):
            self.logger.log_event(session_id, "telnet_disconnect", {"reason": "client_closed"})
        except Exception as e:
            self.logger.log_event(
                session_id, "telnet_error", {"error": str(e), "traceback": traceback.format_exc()}
            )
        finally:
            self.services.session.unregister_session(session_id)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _run_shell(self, reader, writer, shell, username, session_id):
        """Interactive shell loop with Editor and History support."""
        prompt_str = shell.get_prompt()
        writer.write(prompt_str.encode())
        await writer.drain()

        while True:
            try:
                if shell.pending_input_callback:
                    if not await self._handle_editor_session(reader, writer, shell):
                        break
                else:
                    if not await self._handle_shell_session(reader, writer, shell):
                        break
            except (asyncio.TimeoutError, ConnectionResetError, asyncio.IncompleteReadError) as e:
                self.logger.log_event(
                    session_id, "session_disconnect", {"reason": type(e).__name__}
                )
                break

    async def _handle_editor_session(self, reader, writer, shell) -> bool:
        """Process input while in real-time mode (Vim/Nano). Returns False on disconnect."""
        char = await self._read_char(reader)
        if char is None:
            return False
        if not char:
            return True

        was_in_editor = shell.pending_input_callback is not None
        stdout, stderr, _ = await shell.execute(char)
        is_in_editor = shell.pending_input_callback is not None

        resp = stdout + stderr
        if was_in_editor and not is_in_editor:
            # Just exited editor, append the prompt
            resp += shell.get_prompt()

        output = resp.replace("\n", "\r\n").encode("utf-8")
        writer.write(output)
        await writer.drain()
        return True

    async def _handle_shell_session(self, reader, writer, shell) -> bool:
        """Process input while in standard shell mode. Returns False on exit/disconnect."""
        prompt_str = shell.get_prompt()
        cmd = await self._read_line_advanced(reader, writer, prompt_str, shell)

        if cmd is None:  # Disconnected
            return False
        if not cmd.strip():
            writer.write(prompt_str.encode())
            await writer.drain()
            return True
        if cmd.strip() in ("exit", "logout"):
            return False

        if hasattr(self.server, "_analyze_command"):
            self.server._analyze_command(
                cmd,
                shell.username,
                shell.src_ip,
                shell.session_id,
                "telnet",
                is_bot=False,
            )

        stdout, stderr, _ = await shell.execute(cmd)
        output = (stdout + stderr).replace("\n", "\r\n").encode("utf-8")
        writer.write(output)

        if not shell.pending_input_callback:
            new_prompt = shell.get_prompt()
            writer.write(new_prompt.encode())
        await writer.drain()
        return True
