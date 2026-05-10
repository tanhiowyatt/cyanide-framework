from unittest.mock import MagicMock

import pytest

from cyanide.vfs.commands.editor import NanoCommand, VimCommand


@pytest.fixture
def fs():
    mock_fs = MagicMock()
    mock_fs.mkfile = MagicMock()
    mock_fs.is_dir = MagicMock(return_value=False)
    return mock_fs


@pytest.fixture
def emulator(fs):
    emu = MagicMock()
    emu.fs = fs
    emu.username = "root"
    emu.cwd = "/root"
    emu.resolve_path = lambda p: f"/root/{p}" if not p.startswith("/") else p
    emu.pending_input_callback = None
    emu.logger = MagicMock()
    emu.width = 80
    emu.height = 24
    return emu


def test_vim_dd_and_backspace(emulator):
    cmd = VimCommand(emulator)
    cmd._reset_state("test.txt")
    cmd.mode = "NORMAL"
    cmd.lines = ["line1", "line2"]
    cmd.cursor_y = 1

    # Test dd
    cmd._handle_input("dd")
    assert cmd.lines == ["line1"]
    assert cmd.cursor_y == 0
    assert cmd.dirty is True

    # Test backspace in colon mode to exit to normal
    cmd._handle_input(":")
    assert cmd.mode == "COLON"
    cmd._handle_input("\x7f")
    assert cmd.mode == "NORMAL"


def test_vim_insert_mode_complex(emulator):
    cmd = VimCommand(emulator)
    cmd._reset_state("test.txt")
    cmd.mode = "NORMAL"

    # Enter insert mode
    cmd._handle_input("i")

    # Add text
    cmd._handle_input("abc")
    assert cmd.lines == ["abc"]

    # Backspace text
    cmd._handle_input("\x7f")
    assert cmd.lines == ["ab"]

    # Enter (new line)
    cmd._handle_input("\r")
    assert len(cmd.lines) == 2
    assert cmd.lines[-1] == ""

    # Backspace line
    cmd._handle_input("\x7f")
    assert len(cmd.lines) == 1
    assert cmd.lines == ["ab"]


def test_vim_unknown_colon(emulator):
    cmd = VimCommand(emulator)
    cmd._reset_state("test.txt")
    cmd.mode = "COLON"
    cmd.colon_buffer = "unknown_cmd"
    cmd._handle_colon_execute()
    assert "Unknown command" in cmd.message


def test_nano_exit_and_help(emulator):
    cmd = NanoCommand(emulator)
    cmd._reset_state("test.txt")

    # Test Help
    cmd._handle_input("\x07")  # Ctrl+G
    assert "Help:" in cmd.message

    # Test Whereis
    cmd._handle_input("\x17")  # Ctrl+W
    assert "Search:" in cmd.message

    # Test Exit not dirty
    cmd.dirty = False
    out, _, _ = cmd._handle_input("\x18")  # Ctrl+X
    assert "\x1b[?1049l" in out  # EXIT_ALT_SCREEN


def test_nano_backspace_join(emulator):
    cmd = NanoCommand(emulator)
    cmd._reset_state("test.txt")
    cmd.lines = ["line1", "line2"]
    cmd.cursor_y = 1
    cmd.cursor_x = 0

    # Backspace at start of line 2 joins with line 1
    cmd._handle_input("\x7f")
    assert cmd.lines == ["line1line2"]
    assert cmd.cursor_y == 0
    assert cmd.cursor_x == 5
    assert cmd.dirty is True


def test_nano_arrows(emulator):
    cmd = NanoCommand(emulator)
    cmd._reset_state("test.txt")
    cmd.lines = ["a", "b"]
    cmd.cursor_y = 1

    # Arrow Up
    cmd._handle_input("\x1b[A")
    assert cmd.cursor_y == 0

    # Arrow Down
    cmd._handle_input("\x1b[B")
    assert cmd.cursor_y == 1
