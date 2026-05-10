from unittest.mock import AsyncMock, MagicMock

import pytest

from cyanide.services.telnet_handler import TelnetHandler


@pytest.fixture
def server():
    srv = MagicMock()
    srv.logger = MagicMock()
    srv.stats = MagicMock()
    srv.services = {}
    return srv


@pytest.fixture
def handler(server):
    return TelnetHandler(server, {"telnet": {"timeout": 1}})


@pytest.mark.asyncio
async def test_read_char_iac_negotiation(handler):
    """Test Telnet IAC negotiation sequences in _read_char."""
    reader = AsyncMock()
    writer = MagicMock()
    writer.drain = AsyncMock()

    # Sequence: 255 (IAC), 251 (WILL), 1 (ECHO) -> Should be skipped
    # Then returns "A"
    reader.read.side_effect = [b"\xff", b"\xfb", b"\x01", b"A"]

    char = await handler._read_char(reader)
    assert char == "A"
    assert reader.read.call_count == 4


@pytest.mark.asyncio
async def test_read_char_sb_negotiation(handler):
    """Test Telnet SB (Subnegotiation) sequences in _read_char."""
    reader = AsyncMock()
    writer = MagicMock()
    writer.drain = AsyncMock()

    # Sequence: 255, 250 (SB), 24, 0, ... 255, 240 (SE)
    # Then returns "B"
    reader.read.side_effect = [b"\xff", b"\xfa", b"\x18", b"\x00", b"\xff", b"\xf0", b"B"]

    char = await handler._read_char(reader)
    assert char == "B"


@pytest.mark.asyncio
async def test_read_line_advanced_history(handler):
    """Test advanced line reading with history navigation (Arrow Up)."""
    reader = AsyncMock()
    writer = MagicMock()
    writer.drain = AsyncMock()
    shell = MagicMock()
    shell.history = ["ls -la", "cat /etc/passwd"]

    # Simulate Arrow Up: ESC [ A
    # Then Enter: \r
    reader.read.side_effect = [b"\x1b", b"[", b"A", b"\r"]

    # Mock _consume_eol to do nothing
    handler._consume_eol = AsyncMock()

    line = await handler._read_line_advanced(reader, writer, "prompt> ", shell)
    assert line == "cat /etc/passwd"
    assert writer.write.called


@pytest.mark.asyncio
async def test_read_line_advanced_backspace(handler):
    """Test advanced line reading with backspace."""
    reader = AsyncMock()
    writer = MagicMock()
    writer.drain = AsyncMock()

    # Input: a, b, Backspace, c, Enter
    reader.read.side_effect = [b"a", b"b", b"\x7f", b"c", b"\r"]
    handler._consume_eol = AsyncMock()

    line = await handler._read_line_advanced(reader, writer, "prompt> ")
    assert line == "ac"


@pytest.mark.asyncio
async def test_consume_eol(handler):
    """Test EOL consumer swallows follow-up byte."""
    reader = AsyncMock()
    reader.read.return_value = b"\n"

    await handler._consume_eol(reader)
    reader.read.assert_called_with(1)


@pytest.mark.asyncio
async def test_run_shell_editor_mode(handler):
    """Test _run_shell when entering and exiting editor mode."""
    reader = AsyncMock()
    writer = MagicMock()
    writer.drain = AsyncMock()
    shell = MagicMock()
    shell.cwd = "/root"
    shell.pending_input_callback = None
    shell.pending_input_prompt = None
    shell.get_prompt.return_value = "prompt> "

    async def initial_editor_call(*args):
        # This call enters editor mode
        shell.pending_input_callback = MagicMock()
        return "Entering editor", "", 0

    async def second_editor_call(*args):
        # This call (the "q" input) exits editor mode
        shell.pending_input_callback = None
        return "Exiting editor", "", 0

    # _read_line_advanced returns "vim"
    handler._read_line_advanced = AsyncMock(return_value="vim")
    # Patch _read_char with AsyncMock
    handler._read_char = AsyncMock(side_effect=["q", None])

    def shell_execute_side_effect(*args):
        if shell.pending_input_callback is None:
            shell.pending_input_callback = MagicMock()
            return "Entering editor", "", 0
        else:
            shell.pending_input_callback = None
            return "Exiting editor", "", 0

    shell.execute = AsyncMock(side_effect=shell_execute_side_effect)

    await handler._run_shell(reader, writer, shell, "root", "sess1")

    assert writer.write.called
    # Check if "Exiting editor" was written
    all_writes = b"".join(call[0][0] for call in writer.write.call_args_list)
    assert b"Entering editor" in all_writes
    assert b"Exiting editor" in all_writes
