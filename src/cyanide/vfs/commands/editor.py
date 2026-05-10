import asyncio
import inspect
import os
from typing import List, Optional

from .base import Command

# ANSI Escape Sequences
CLEAR_SCREEN = "\033[2J\033[H\033[3J"  # Full clear (only on open/close)
ENTER_ALT_SCREEN = "\033[?1049h\033[H"  # Enter alternate screen
EXIT_ALT_SCREEN = "\033[?1049l\033[m"  # Exit alternate screen and reset attributes
CURSOR_HOME = "\033[H"  # Move cursor to top-left
REDRAW_HOME = "\033[H"
REVERSE_VIDEO = "\033[7m"
RESET_VIDEO = "\033[0m"
CURSOR_MOVE = "\033[{};{}H"
CLEAR_LINE = "\033[2K"
CLEAR_LINE_TO_EOL = "\033[K"

DEFAULT_BUFFER_NAME = "New Buffer"


class BaseVisualEditor(Command):
    """Base class for editors with a visual (full-screen) interface."""

    def __init__(self, emulator):
        super().__init__(emulator)
        self.MAX_LINES = 2000
        self.MAX_LINE_LENGTH = 2000
        self.filename = ""
        self.abs_path = ""
        self.lines: List[str] = []
        self.dirty = False
        self.height = 24
        self.width = 80
        self.message = ""
        self.cut_buffer = ""
        self.cursor_y = 0
        self.scroll_top = 0
        self.on_exit = None  # Callback for exit event
        self._background_tasks = set()

    def _reset_state(self, filename: str = ""):
        """Reset internal editor state for a new session."""
        self.filename = filename
        self.lines = []
        self.dirty = False
        self.message = ""
        self.abs_path = ""
        self.cursor_x = 0
        self.cursor_y = 0
        self.scroll_top = 0
        self._first_render = True  # Use CLEAR_SCREEN once to wipe old shell output

        # Pull dynamic dimensions from emulator if available
        self.width = getattr(self.emulator, "width", 80)
        self.height = getattr(self.emulator, "height", 24)

    def _get_display_lines(self, start_line: int, count: int, filler: str = "~") -> str:
        """Render text lines, erasing to EOL on each so no old content bleeds through."""
        display = ""
        for i in range(count):
            idx = start_line + i
            if idx < len(self.lines):
                line = self.lines[idx][: self.width]
                display += line + CLEAR_LINE_TO_EOL + "\r\n"
            else:
                display += filler + CLEAR_LINE_TO_EOL + "\r\n"
        return display

    def _save(self):
        if not self.filename or self.filename == DEFAULT_BUFFER_NAME:
            self.message = "No filename specified"
            return

        content = "\n".join(self.lines)
        if self.lines and not content.endswith("\n"):
            content += "\n"

        parent = os.path.dirname(self.abs_path)
        if parent:
            self.fs.mkdir_p(parent)
        self.fs.mkfile(self.abs_path, content=content, owner=self.emulator.username)
        self.dirty = False
        self._log_editor_action("saved")

    def _log_editor_action(self, action: str):
        if not hasattr(self.emulator, "logger") or not self.emulator.logger:
            return

        content = "\n".join(self.lines)

        self.emulator.logger.log_event(
            self.emulator.session_id,
            f"editor.{action}",
            {
                "src_ip": getattr(self.emulator, "src_ip", "unknown"),
                "username": getattr(self.emulator, "username", "unknown"),
                "editor": getattr(
                    self, "name", self.__class__.__name__.replace("Command", "").lower()
                ),
                "filename": self.filename,
                "lines": len(self.lines),
                "content": content,
                "dirty": self.dirty,
            },
        )

    def _exit_editor(self, action_log: str) -> tuple[str, str, int]:
        """Finalize editor session and return exit sequence."""
        self.emulator.pending_input_callback = None
        self.emulator.pending_input_prompt = None
        self._log_editor_action(action_log)
        self._execute_exit_hook()
        return EXIT_ALT_SCREEN, "", 0

    def _execute_exit_hook(self):
        """Safely execute the exit callback (supports sync/async)."""
        if not self.on_exit:
            return

        if inspect.iscoroutinefunction(self.on_exit):
            task = asyncio.create_task(self.on_exit())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        else:
            self.on_exit()


class VimCommand(BaseVisualEditor):
    """Realistic Vim emulation."""

    MAX_LINES = 2000
    MAX_LINE_LENGTH = 2000

    async def execute(self, args: list[str], input_data: str = "") -> tuple[str, str, int]:
        filename = ""
        for arg in args:
            if not arg.startswith("-"):
                filename = arg
                break
        self._reset_state(filename)
        self.mode = "NORMAL"

        if self.filename:
            self.abs_path = self.emulator.resolve_path(self.filename)
            if self.fs.exists(self.abs_path):
                self.lines = self.get_content_str(self.abs_path).splitlines()
                if not self.lines:
                    self.lines = [""]
                self.message = f'"{self.filename}" {len(self.lines)}L'

        if not self.lines:
            self.lines = [""]

        self.emulator.pending_input_callback = self._handle_input
        self.emulator.pending_input_prompt = ""
        return self._render(), "", 0

    def _render(self) -> str:
        # Update scroll position
        if self.cursor_y < self.scroll_top:
            self.scroll_top = self.cursor_y
        elif self.cursor_y >= self.scroll_top + (self.height - 2):
            self.scroll_top = max(0, self.cursor_y - (self.height - 3))

        # First render: enter alternate screen
        if getattr(self, "_first_render", True):
            self._first_render = False
            prefix = ENTER_ALT_SCREEN
        else:
            prefix = REDRAW_HOME
        out = prefix
        out += self._get_display_lines(self.scroll_top, self.height - 2)
        out += CURSOR_MOVE.format(self.height - 1, 1)
        status = f" {self.mode} {'-- INSERT --' if self.mode == 'INSERT' else self.filename}"
        out += REVERSE_VIDEO + status.ljust(self.width) + RESET_VIDEO
        out += CURSOR_MOVE.format(self.height, 1)
        if self.mode == "COLON":
            display_msg = ":" + self.colon_buffer
        else:
            display_msg = self.message
        out += CLEAR_LINE + (display_msg[: self.width]).ljust(self.width)

        render_cursor_y = min(max(self.cursor_y - self.scroll_top + 1, 1), self.height - 2)
        if self.mode == "COLON":
            render_cursor_y = self.height
            render_cursor_x = len(self.colon_buffer) + 2
        else:
            render_cursor_x = min(self.cursor_x + 1, self.width)

        out += CURSOR_MOVE.format(render_cursor_y, render_cursor_x)
        return out

    def _handle_input(self, char: str) -> tuple[str, str, int]:
        self.message = ""

        if "\x1b" in char:
            if "[" in char:  # Handle ANSI arrow keys
                self._handle_navigation(char)
                return self._render(), "", 0
            self.mode = "NORMAL"
            return self._render(), "", 0

        if self.mode == "NORMAL":
            return self._handle_normal_mode(char)
        if self.mode == "COLON":
            return self._handle_colon_mode(char)
        if self.mode == "INSERT":
            return self._handle_insert_mode(char)

        self.emulator.pending_input_callback = self._handle_input
        return self._render(), "", 0

    def _handle_normal_mode(self, char: str) -> tuple[str, str, int]:
        if char in ("k", "\x1b[A") and self.cursor_y > 0:  # Up
            self.cursor_y -= 1
        elif char in ("j", "\x1b[B") and self.cursor_y < len(self.lines) - 1:  # Down
            self.cursor_y += 1
        elif char in ("l", "\x1b[C"):  # Right
            if self.cursor_x < len(self.lines[self.cursor_y]):
                self.cursor_x += 1
        elif char in ("h", "\x1b[D"):  # Left
            self.cursor_x = max(0, self.cursor_x - 1)
        elif char == "i":
            self.mode = "INSERT"
            if not self.lines:
                self.lines = [""]
        elif char == ":":
            self.mode = "COLON"
            self.colon_buffer = ""
        elif char == "G":
            if self.lines:
                self.cursor_y = len(self.lines) - 1
        elif char == "o":
            if len(self.lines) < self.MAX_LINES:
                self.lines.insert(self.cursor_y + 1, "")
                self.cursor_y += 1
                self.cursor_x = 0
                self.mode = "INSERT"
        else:
            self._handle_normal_delete_commands(char)

        if self.lines:
            self.cursor_x = min(self.cursor_x, len(self.lines[self.cursor_y]))

        self.emulator.pending_input_callback = self._handle_input
        return self._render(), "", 0

    def _handle_navigation(self, sequence: str):
        """Handle ANSI navigation sequences."""
        if "[A" in sequence and self.cursor_y > 0:
            self.cursor_y -= 1
        elif "[B" in sequence and self.cursor_y < len(self.lines) - 1:
            self.cursor_y += 1
        elif "[C" in sequence:
            if self.cursor_x < len(self.lines[self.cursor_y]):
                self.cursor_x += 1
        elif "[D" in sequence:
            self.cursor_x = max(0, self.cursor_x - 1)

        if self.lines:
            self.cursor_x = min(self.cursor_x, len(self.lines[self.cursor_y]))

    def _handle_normal_delete_commands(self, char: str):
        if char == "x" and self.lines and self.cursor_y < len(self.lines):
            line = self.lines[self.cursor_y]
            if self.cursor_x < len(line):
                self.lines[self.cursor_y] = line[: self.cursor_x] + line[self.cursor_x + 1 :]
                self.dirty = True
        elif char == "dd" and self.lines:
            self.lines.pop(self.cursor_y)
            self.cursor_y = max(0, self.cursor_y - 1)
            self.dirty = True

    def _handle_colon_mode(self, char: str) -> tuple[str, str, int]:
        if char in ("\r", "\n"):
            return self._handle_colon_execute()
        if char in ("\x08", "\x7f") and self.colon_buffer:
            self.colon_buffer = self.colon_buffer[:-1]
        elif char in ("\x08", "\x7f"):
            self.mode = "NORMAL"
        else:
            self.colon_buffer += char
        self.emulator.pending_input_callback = self._handle_input
        return self._render(), "", 0

    def _handle_insert_mode(self, char: str) -> tuple[str, str, int]:
        if not self.lines:
            self.lines = [""]

        if char in ("\r", "\n") and len(self.lines) < self.MAX_LINES:
            line = self.lines[self.cursor_y]
            self.lines[self.cursor_y] = line[: self.cursor_x]
            self.lines.insert(self.cursor_y + 1, line[self.cursor_x :])
            self.cursor_y += 1
            self.cursor_x = 0
            self.dirty = True
        elif char in ("\x08", "\x7f"):
            self._handle_insert_backspace()
        else:
            self._handle_insert_text(char)

        self.emulator.pending_input_callback = self._handle_input
        return self._render(), "", 0

    def _handle_insert_backspace(self):
        if self.cursor_x > 0:
            line = self.lines[self.cursor_y]
            self.lines[self.cursor_y] = line[: self.cursor_x - 1] + line[self.cursor_x :]
            self.cursor_x -= 1
            self.dirty = True
        elif self.cursor_y > 0:
            # Join with previous line
            prev_line = self.lines[self.cursor_y - 1]
            current_line = self.lines[self.cursor_y]
            self.cursor_x = len(prev_line)
            self.lines[self.cursor_y - 1] = prev_line + current_line
            self.lines.pop(self.cursor_y)
            self.cursor_y -= 1
            self.dirty = True

    def _handle_insert_text(self, char: str):
        clean = "".join(c for c in char if ord(c) >= 32 or c == "\t")
        if clean:
            line = self.lines[self.cursor_y]
            if len(line) + len(clean) <= self.MAX_LINE_LENGTH:
                self.lines[self.cursor_y] = line[: self.cursor_x] + clean + line[self.cursor_x :]
                self.cursor_x += len(clean)
                self.dirty = True

        self.emulator.pending_input_callback = self._handle_input
        return self._render(), "", 0

    def _handle_colon_execute(self) -> tuple[str, str, int]:
        cmd = self.colon_buffer.strip().lower()
        self.mode = "NORMAL"

        if cmd in ("wq", "x"):
            self._save()
            return self._exit_editor("exited_after_save")

        if cmd in ("q", "q!"):
            return self._exit_editor("exited_without_save")

        if cmd == "w":
            self._save()
            self.message = f'"{self.filename}" {len(self.lines)}L written'
        else:
            self.message = f"Unknown command: {cmd}"

        self.emulator.pending_input_callback = self._handle_input
        return self._render(), "", 0

    def _save(self):
        """Save buffer to filesystem and trigger snapshot logging."""
        if self.abs_path:
            content = "\n".join(self.lines)
            self.fs.mkfile(self.abs_path, content=content)
            self.dirty = False
            # Snapshot Logging: Log the final file state as an event
            self._log_editor_action("saved_file", {"lines": len(self.lines), "content": content})

    def _log_editor_action(self, action: str, extra: Optional[dict] = None):
        """Log editor-specific actions for forensics."""
        if self.emulator.logger:
            data = {
                "editor": "vim",
                "action": action,
                "file": self.filename,
            }
            if extra:
                data.update(extra)
            self.emulator.logger.log_event(
                self.emulator.session_id, "vfs_event", {"command": "vim", "details": data}
            )


class NanoCommand(BaseVisualEditor):
    """Realistic Nano emulation with robust state management."""

    async def execute(self, args: list[str], input_data: str = "") -> tuple[str, str, int]:
        filename = DEFAULT_BUFFER_NAME
        for arg in args:
            if not arg.startswith("-"):
                filename = arg
                break
        self._reset_state(filename)

        if filename != DEFAULT_BUFFER_NAME:
            self.abs_path = self.emulator.resolve_path(self.filename)
            if self.fs.exists(self.abs_path):
                self.lines = self.get_content_str(self.abs_path).splitlines()

        self.emulator.pending_input_callback = self._handle_input
        self.emulator.pending_input_prompt = ""
        return self._render(), "", 0

    def _render(self) -> str:
        # Handle scrolling
        if self.cursor_y < self.scroll_top:
            self.scroll_top = self.cursor_y
        elif self.cursor_y >= self.scroll_top + (self.height - 6):
            self.scroll_top = self.cursor_y - (self.height - 7)

        # Overwrite in-place from cursor home — no blank-screen flash.
        # ENTER_ALT_SCREEN is only used on initial open and final exit.
        if getattr(self, "_first_render", True):
            self._first_render = False
            out = ENTER_ALT_SCREEN
        else:
            out = REDRAW_HOME

        title = f"  GNU nano 6.2                {self.filename}"
        out += REVERSE_VIDEO + title.ljust(self.width) + RESET_VIDEO + CLEAR_LINE_TO_EOL + "\r\n"
        out += self._get_display_lines(self.scroll_top, self.height - 6, filler="")
        out += CURSOR_MOVE.format(self.height - 2, 1)
        out += CLEAR_LINE + (self.message[: self.width]).ljust(self.width)

        def format_shortcuts(pairs: list[tuple[str, str]]) -> str:
            line = ""
            for key, desc in pairs:
                line += REVERSE_VIDEO + key + RESET_VIDEO + " " + desc.ljust(12) + "  "
            return line + CLEAR_LINE_TO_EOL

        out += CURSOR_MOVE.format(self.height - 1, 1)
        out += format_shortcuts(
            [("^G", "Get Help"), ("^O", "Write Out"), ("^W", "Where Is"), ("^K", "Cut Text")]
        )
        out += CURSOR_MOVE.format(self.height, 1)
        out += format_shortcuts(
            [("^X", "Exit"), ("^J", "Justify"), ("^R", "Read File"), ("^U", "Uncut Text")]
        )

        # Precise cursor positioning
        # Row 1 = title bar, content starts at row 2
        render_cursor_y = min(self.cursor_y - self.scroll_top + 2, self.height - 3)
        render_cursor_x = self.cursor_x + 1

        out += CURSOR_MOVE.format(render_cursor_y, render_cursor_x)
        return out

    def _handle_input(self, raw_line: str) -> tuple[str, str, int]:
        self.message = ""

        # Check for shortcuts first
        shortcut_result = self._handle_nano_shortcuts(raw_line)
        if shortcut_result:
            return shortcut_result

        # Handle movement and editing
        if any(c in raw_line for c in ("\x08", "\x7f")):
            self._handle_nano_backspace()
        elif "\x1b[" in raw_line:
            self._handle_nano_arrows(raw_line)
        elif "\r" in raw_line or "\n" in raw_line:
            enter_result = self._handle_nano_enter()
            if enter_result:
                return enter_result
        else:
            text_result = self._handle_nano_text(raw_line)
            if text_result:
                return text_result

        self.emulator.pending_input_callback = self._handle_input
        return self._render(), "", 0

    def _handle_nano_shortcuts(self, raw_line: str) -> Optional[tuple[str, str, int]]:
        """Process Ctrl-shortcuts."""
        if any(c in raw_line for c in ("\x18", "^X", "^x")):
            return self._handle_nano_exit()
        if any(c in raw_line for c in ("\x0f", "^O", "^o")):
            return self._handle_nano_save_shortcut()
        if any(c in raw_line for c in ("\x0b", "^K", "^k")):
            self._handle_nano_cut()
        elif any(c in raw_line for c in ("\x15", "^U", "^u")):
            self._handle_nano_uncut()
        elif any(c in raw_line for c in ("\x07", "^G", "^g")):
            self.message = "Help: Use Ctrl+X to exit, Ctrl+O to save."
        elif any(c in raw_line for c in ("\x17", "^W", "^w")):
            self.message = "Search: Feature not implemented in this demo"
        return None

    def _handle_nano_exit(self) -> tuple[str, str, int]:
        if self.dirty:
            self.message = "Save modified buffer? (Answer y/n)"
            self.emulator.pending_input_callback = self._handle_exit_confirm
            return self._render(), "", 0
        return self._exit_editor("exited")

    def _handle_nano_save_shortcut(self) -> tuple[str, str, int]:
        if self.filename == DEFAULT_BUFFER_NAME:
            self.message = "File Name to Write: "
            self.emulator.pending_input_callback = self._handle_save_as
            return self._render(), "", 0
        self._save()
        self.message = f"Wrote {len(self.lines)} lines"
        return self._render(), "", 0

    def _handle_nano_cut(self):
        if self.lines:
            self.cut_buffer = self.lines.pop()
            self.dirty = True
            self.message = "Cut 1 line"

    def _handle_nano_uncut(self):
        if self.cut_buffer:
            self.lines.append(self.cut_buffer)
            self.dirty = True
            self.message = "Uncut 1 line"

    def _handle_nano_backspace(self):
        if self.cursor_x > 0:
            line = self.lines[self.cursor_y]
            self.lines[self.cursor_y] = line[: self.cursor_x - 1] + line[self.cursor_x :]
            self.cursor_x -= 1
            self.dirty = True
        elif self.cursor_y > 0:
            prev_len = len(self.lines[self.cursor_y - 1])
            curr_line = self.lines.pop(self.cursor_y)
            self.cursor_y -= 1
            self.lines[self.cursor_y] += curr_line
            self.cursor_x = prev_len
            self.dirty = True

    def _handle_nano_arrows(self, raw_line: str):
        if "[A" in raw_line and self.cursor_y > 0:  # Up
            self.cursor_y -= 1
        elif "[B" in raw_line and self.cursor_y < len(self.lines) - 1:  # Down
            self.cursor_y += 1
        elif "[C" in raw_line:  # Right
            if self.cursor_x < len(self.lines[self.cursor_y]):
                self.cursor_x += 1
            elif self.cursor_y < len(self.lines) - 1:
                self.cursor_y += 1
                self.cursor_x = 0
        elif "[D" in raw_line:  # Left
            if self.cursor_x > 0:
                self.cursor_x -= 1
            elif self.cursor_y > 0:
                self.cursor_y -= 1
                self.cursor_x = len(self.lines[self.cursor_y])
        self.cursor_x = min(self.cursor_x, len(self.lines[self.cursor_y]))

    def _handle_nano_enter(self) -> Optional[tuple[str, str, int]]:
        if len(self.lines) >= self.MAX_LINES:
            self.message = "Limit reached: Maximum 2000 lines"
            return self._render(), "", 0
        line = self.lines[self.cursor_y] if self.cursor_y < len(self.lines) else ""
        remaining = line[self.cursor_x :]
        if self.cursor_y < len(self.lines):
            self.lines[self.cursor_y] = line[: self.cursor_x]
        else:
            self.lines.append("")
        self.lines.insert(self.cursor_y + 1, remaining)
        self.cursor_y += 1
        self.cursor_x = 0
        self.dirty = True
        return None

    def _handle_nano_text(self, raw_line: str) -> Optional[tuple[str, str, int]]:
        clean_text = "".join(c for c in raw_line if ord(c) >= 32 and c != "^")
        if not clean_text:
            return None
        if not self.lines:
            self.lines.append(clean_text)
            self.cursor_x = len(clean_text)
        else:
            line = self.lines[self.cursor_y]
            if len(line) + len(clean_text) > self.MAX_LINE_LENGTH:
                self.message = "Limit reached: Maximum 2000 characters per line"
                return self._render(), "", 0
            self.lines[self.cursor_y] = line[: self.cursor_x] + clean_text + line[self.cursor_x :]
            self.cursor_x += len(clean_text)
        self.dirty = True
        return None

    def _handle_save_as(self, line: str) -> tuple[str, str, int]:
        line = line.strip()
        if line:
            self.filename = line
            self.abs_path = self.emulator.resolve_path(self.filename)
            self._save()
            self.message = f"Wrote {len(self.lines)} lines"
        self.emulator.pending_input_callback = self._handle_input
        return self._render(), "", 0

    def _handle_exit_confirm(self, line: str) -> tuple[str, str, int]:
        line = line.lower().strip()
        if line == "y":
            return self._handle_exit_yes()
        if line == "n":
            return self._handle_exit_no()

        self.message = "Save modified buffer? (Answer y/n)"
        return self._render(), "", 0

    def _handle_exit_yes(self) -> tuple[str, str, int]:
        if self.filename == DEFAULT_BUFFER_NAME:
            self.message = "File Name to Write: "
            self.emulator.pending_input_callback = self._handle_save_as_then_exit
            return self._render(), "", 0

        self._save()
        return self._exit_editor("exited_after_save")

    def _handle_exit_no(self) -> tuple[str, str, int]:
        return self._exit_editor("exited_without_save")

    def _exit_editor(self, action_log: str) -> tuple[str, str, int]:
        self.emulator.pending_input_callback = None
        self.emulator.pending_input_prompt = None
        self._log_editor_action(action_log)
        self._execute_exit_hook()
        return EXIT_ALT_SCREEN, "", 0

    def _execute_exit_hook(self):
        if not self.on_exit:
            return

        if inspect.iscoroutinefunction(self.on_exit):
            task = asyncio.create_task(self.on_exit())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        else:
            self.on_exit()

    def _handle_save_as_then_exit(self, line: str) -> tuple[str, str, int]:
        line = line.strip()
        if line:
            self.filename = line
            self.abs_path = self.emulator.resolve_path(self.filename)
            self._save()
        return self._exit_editor("exited_after_save")


class EditorCommand(VimCommand):
    pass
