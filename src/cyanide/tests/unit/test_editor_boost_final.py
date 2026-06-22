from unittest.mock import MagicMock

import pytest

from cyanide.vfs.commands.editor import NanoCommand, VimCommand


@pytest.fixture
def emulator():
    emu = MagicMock()
    emu.fs = MagicMock()
    emu.fs.mkfile = MagicMock()
    emu.fs.get_node = MagicMock()
    emu.username = "root"
    emu.cwd = "/root"
    emu.resolve_path = lambda p: f"/root/{p}" if not p.startswith("/") else p
    emu.logger = MagicMock()
    emu.width = 80
    emu.height = 24
    return emu


def test_vim_modes_and_keys(emulator):
    cmd = VimCommand(emulator)
    cmd._reset_state("test.txt")

    cmd.mode = "INSERT"
    cmd._handle_input("h")
    cmd._handle_input("e")
    cmd._handle_input("l")
    cmd._handle_input("l")
    cmd._handle_input("o")
    assert cmd.lines == ["hello"]

    cmd._handle_input("\x7f")
    assert cmd.lines == ["hell"]

    cmd._handle_input("\n")
    assert len(cmd.lines) == 2

    cmd.mode = "NORMAL"
    cmd.cursor_y = 0
    cmd._handle_input("o")
    assert len(cmd.lines) == 3
    assert cmd.mode == "INSERT"

    cmd.mode = "COLON"
    cmd.colon_buffer = "unknown"
    cmd._handle_colon_execute()
    assert "Unknown command" in cmd.message


def test_nano_scrolling_and_keys(emulator):
    cmd = NanoCommand(emulator)
    cmd._reset_state("test.txt")

    cmd.lines = ["line"] * 50
    cmd.cursor_y = 40
    cmd.scroll_top = 0
    cmd._render()
    assert cmd.scroll_top > 0

    cmd.lines = ["a", "b", "c"]
    cmd._handle_input("\x0b")
    assert cmd.lines == ["a", "b"]
    assert cmd.cut_buffer == "c"

    cmd._handle_input("\x15")
    assert cmd.lines == ["a", "b", "c"]
