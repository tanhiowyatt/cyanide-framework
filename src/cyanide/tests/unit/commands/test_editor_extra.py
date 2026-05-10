from unittest.mock import MagicMock

import pytest

from cyanide.vfs.commands.editor import NanoCommand, VimCommand
from cyanide.vfs.engine import FakeFilesystem


@pytest.fixture
def fs():
    return FakeFilesystem()


@pytest.fixture
def emulator(fs):
    emu = MagicMock()
    emu.fs = fs
    emu.logger = None
    emu.session_id = "test-session"
    emu.username = "root"
    emu.width = 80
    emu.height = 24
    emu.resolve_path = lambda p: f"/home/cyanide/{p}" if not p.startswith("/") else p
    return emu


def test_nano_save_as(fs, emulator):
    """Test Nano Save As functionality for a new buffer."""
    cmd = NanoCommand(emulator)
    cmd._reset_state("New Buffer")
    cmd.lines = ["test line"]
    cmd.dirty = True

    # Send Ctrl+O
    out, _, _ = cmd._handle_input("\x0f")
    assert "File Name to Write:" in out
    assert emulator.pending_input_callback == cmd._handle_save_as

    # Provide filename
    out, _, _ = cmd._handle_save_as("test.txt")
    assert "Wrote 1 lines" in out
    assert fs.exists("/home/cyanide/test.txt")
    assert fs.get_content("/home/cyanide/test.txt") == "test line\n"


def test_nano_exit_confirmation(fs, emulator):
    """Test Nano exit confirmation when buffer is dirty."""
    cmd = NanoCommand(emulator)
    cmd._reset_state("test.txt")
    cmd.lines = ["modified"]
    cmd.dirty = True

    # Send Ctrl+X
    out, _, _ = cmd._handle_input("\x18")
    assert "Save modified buffer?" in out
    assert emulator.pending_input_callback == cmd._handle_exit_confirm

    # Answer 'n' (Don't save)
    out, _, _ = cmd._handle_exit_confirm("n")
    assert "\x1b[?1049l" in out  # EXIT_ALT_SCREEN
    assert emulator.pending_input_callback is None


def test_nano_cut_uncut(fs, emulator):
    """Test Nano Cut (Ctrl+K) and Uncut (Ctrl+U)."""
    cmd = NanoCommand(emulator)
    cmd._reset_state("test.txt")
    cmd.lines = ["line 1", "line 2"]

    # Cut
    cmd._handle_input("\x0b")
    assert len(cmd.lines) == 1
    assert cmd.cut_buffer == "line 2"

    # Uncut
    cmd._handle_input("\x15")
    assert len(cmd.lines) == 2
    assert cmd.lines[1] == "line 2"


def test_nano_limits(fs, emulator):
    """Test Nano line and character limits."""
    cmd = NanoCommand(emulator)
    cmd._reset_state("test.txt")
    cmd.MAX_LINES = 2
    cmd.lines = ["line 1", "line 2"]

    # Try to add 3rd line
    out, _, _ = cmd._handle_input("\n")
    assert "Limit reached" in out
    assert len(cmd.lines) == 2

    # Test char limit
    cmd.MAX_LINE_LENGTH = 5
    cmd.cursor_y = 0
    cmd.cursor_x = 5
    out, _, _ = cmd._handle_input("extra")
    assert "Limit reached" in out


def test_vim_movement_and_editing(fs, emulator):
    """Test Vim movement (G) and basic editing (x, dd)."""
    cmd = VimCommand(emulator)
    cmd._reset_state("test.txt")
    cmd.lines = ["line 1", "line 2", "line 3"]
    cmd.mode = "NORMAL"

    # G (Move to end)
    cmd._handle_input("G")
    assert cmd.cursor_y == 2

    # x (Delete char)
    cmd.lines[2] = "abc"
    cmd.cursor_x = 1
    cmd._handle_input("x")
    assert cmd.lines[2] == "ac"

    # dd (Delete line)
    cmd._handle_input("dd")
    assert len(cmd.lines) == 2
    assert cmd.lines == ["line 1", "line 2"]


def test_vim_colon_commands(fs, emulator):
    """Test Vim colon commands (w, q!, unknown)."""
    cmd = VimCommand(emulator)
    cmd._reset_state("test.txt")
    cmd.abs_path = "/home/cyanide/test.txt"
    cmd.lines = ["content"]

    # :w (Save)
    fs.mkdir_p("/home/cyanide")
    cmd.mode = "COLON"
    cmd.colon_buffer = "w"
    cmd._handle_colon_execute()
    assert fs.get_content("/home/cyanide/test.txt") == "content"

    # :q! (Quit without save)
    cmd.mode = "COLON"
    cmd.colon_buffer = "q!"
    out, _, _ = cmd._handle_colon_execute()
    assert "\x1b[?1049l" in out

    # :unknown
    cmd.mode = "COLON"
    cmd.colon_buffer = "invalid"
    out, _, _ = cmd._handle_colon_execute()
    assert "Unknown command" in out


def test_vim_insert_mode(emulator):
    """Test Vim transition to INSERT mode and typing."""
    cmd = VimCommand(emulator)
    cmd._reset_state("test.txt")
    cmd.mode = "NORMAL"

    # Enter insert mode
    cmd._handle_input("i")
    assert cmd.mode == "INSERT"

    # Type something
    cmd._handle_input("hello")
    assert cmd.lines[0] == "hello"
    assert cmd.dirty is True

    # Press Enter
    cmd._handle_input("\n")
    assert len(cmd.lines) == 2
    assert cmd.lines[1] == ""

    # Backspace
    cmd._handle_input("\x7f")
    assert len(cmd.lines) == 1
    assert cmd.lines[0] == "hello"


def test_vim_open_line(emulator):
    """Test Vim 'o' command (open line below)."""
    cmd = VimCommand(emulator)
    cmd._reset_state("test.txt")
    cmd.lines = ["line 1"]
    cmd.cursor_y = 0
    cmd.mode = "NORMAL"

    cmd._handle_input("o")
    assert len(cmd.lines) == 2
    assert cmd.lines[1] == ""
    assert cmd.cursor_y == 1
    assert cmd.mode == "INSERT"


def test_nano_shortcuts_and_arrows(emulator):
    """Test Nano various shortcuts and arrow key navigation."""
    cmd = NanoCommand(emulator)
    cmd._reset_state("test.txt")
    cmd.lines = ["abc", "def"]
    cmd.cursor_y = 0
    cmd.cursor_x = 0

    # Arrow Down
    cmd._handle_input("\x1b[B")
    assert cmd.cursor_y == 1

    # Arrow Right
    cmd._handle_input("\x1b[C")
    assert cmd.cursor_x == 1

    # Arrow Left
    cmd._handle_input("\x1b[D")
    assert cmd.cursor_x == 0

    # Arrow Up
    cmd._handle_input("\x1b[A")
    assert cmd.cursor_y == 0

    # Ctrl+G (Help)
    out, _, _ = cmd._handle_input("\x07")
    assert "Help:" in out

    # Ctrl+W (WhereIs)
    out, _, _ = cmd._handle_input("\x17")
    assert "Search:" in out


def test_nano_backspace_edge_cases(emulator):
    """Test Nano backspace at start of line (merging lines)."""
    cmd = NanoCommand(emulator)
    cmd._reset_state("test.txt")
    cmd.lines = ["line1", "line2"]
    cmd.cursor_y = 1
    cmd.cursor_x = 0

    # Backspace at start of line 2
    cmd._handle_input("\x7f")
    assert len(cmd.lines) == 1
    assert cmd.lines[0] == "line1line2"
    assert cmd.cursor_y == 0
    assert cmd.cursor_x == 5


def test_editor_logging(emulator):
    """Test that editor actions trigger the emulator's logger."""
    mock_logger = MagicMock()
    emulator.logger = mock_logger
    cmd = VimCommand(emulator)
    cmd._reset_state("test.txt")
    cmd.lines = ["logged content"]

    cmd._log_editor_action("saved_file", {"extra": "data"})
    assert mock_logger.log_event.called
    args, kwargs = mock_logger.log_event.call_args
    assert args[0] == "test-session"
    assert args[1] == "vfs_event"
    assert args[2]["details"]["action"] == "saved_file"
    assert args[2]["details"]["file"] == "test.txt"


def test_vim_colon_quit(emulator):
    """Test Vim ':q' command (quit)."""
    cmd = VimCommand(emulator)
    cmd._reset_state("test.txt")
    cmd.mode = "COLON"
    cmd.colon_buffer = "q"
    out, _, _ = cmd._handle_colon_execute()
    assert "\x1b[?1049l" in out  # EXIT_ALT_SCREEN
