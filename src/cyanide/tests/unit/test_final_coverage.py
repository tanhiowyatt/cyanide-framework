import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cyanide.services.telnet_handler import TelnetHandler
from cyanide.vfs.commands.curl import CurlCommand
from cyanide.vfs.engine import FakeFilesystem
from cyanide.vfs.scp import ScpHandler


@pytest.fixture
def fs():
    return FakeFilesystem()


@pytest.fixture
def emulator(fs):
    emu = MagicMock()
    emu.fs = fs
    emu.src_ip = "1.2.3.4"
    emu.session_id = "test-session"
    emu.username = "root"
    emu.quarantine_callback = MagicMock()
    emu.resolve_path = lambda p: f"/root/{p}" if not p.startswith("/") else p
    return emu


@pytest.mark.asyncio
async def test_scp_error_paths(emulator):
    # Test _read error
    handler = ScpHandler(MagicMock(), process=MagicMock())
    handler.process.stdin.read.side_effect = Exception("Read error")
    data = await handler._read(1)
    assert data == b""

    # Test _write error
    handler.process.channel.write.side_effect = Exception("Write error")
    handler._write(b"data")  # Should just log and not raise

    # Test _read_file_data with partial read
    handler.process.stdin.read.side_effect = [b"a", b""]
    await handler._read_file_data(10)

    # Test _save_to_vfs with no fs
    handler.fs = None
    handler._save_to_vfs("test", b"content")  # Should return early


@pytest.mark.asyncio
async def test_scp_metadata_edge_cases(emulator):
    handler = ScpHandler(MagicMock())
    # Test no sink/source
    is_sink, is_source, path = handler._parse_scp_metadata("scp file")
    assert is_sink is False
    assert is_source is False

    # Test exception in shlex
    with patch("shlex.split", side_effect=Exception("shlex error")):
        is_sink, is_source, path = handler._parse_scp_metadata("scp -t /tmp")
        assert is_sink is False


@pytest.mark.asyncio
async def test_curl_edge_cases(emulator):
    cmd = CurlCommand(emulator)

    # Test status >= 400 with silent
    mock_resp = AsyncMock()
    mock_resp.status = 404
    mock_resp.version = None
    mock_resp.headers = {}

    mock_resp.__aenter__.return_value = mock_resp
    with patch("aiohttp.ClientSession.get", return_value=mock_resp):
        stdout, stderr, rc = await cmd.execute(["-s", "http://example.com"])
        assert rc == 22
        assert stderr == ""

    # Test ClientError
    import aiohttp

    with patch("aiohttp.ClientSession.get", side_effect=aiohttp.ClientError("Resolve failed")):
        stdout, stderr, rc = await cmd.execute(["http://example.com"])
        assert rc == 6
        assert "Could not resolve host" in stderr

    # Test generic Exception
    with patch("aiohttp.ClientSession.get", side_effect=RuntimeError("Generic error")):
        stdout, stderr, rc = await cmd.execute(["http://example.com"])
        assert rc == 1
        assert "Protocol not supported" in stderr


@pytest.mark.asyncio
async def test_telnet_read_char_edge_cases(emulator):
    class MockReader:
        def __init__(self, side_effect):
            self.side_effect = side_effect

        async def read(self, n):
            if not self.side_effect:
                return b""
            res = self.side_effect.pop(0)
            if isinstance(res, Exception):
                raise res
            return res

    handler = TelnetHandler(MagicMock(), {"telnet": {"timeout": 0.1}})

    # Test timeout
    reader = MockReader([asyncio.TimeoutError()])
    char = await handler._read_char(reader)
    assert char is None

    # Test empty read
    reader = MockReader([b""])
    char = await handler._read_char(reader)
    assert char is None

    # Test IAC with no follow-up
    reader = MockReader([b"\xff", b""])
    char = await handler._read_char(reader)
    assert char is None

    # Test SB loop exit on empty read
    reader = MockReader([b"\xff", b"\xfa", b"\x01", b"", b""])
    char = await handler._read_char(reader)
    assert char is None


def test_engine_history_edge_cases(fs):
    # Test save_ip_history with unknown IP
    fs.src_ip = "unknown"
    fs.save_ip_history()  # Should return early

    # Test save_ip_history with empty content
    fs.src_ip = "1.1.1.1"
    fs.memory_overlay["/root/.bash_history"] = {"content": ""}
    fs.save_ip_history()  # Should return early

    # Test save_ip_history exception
    with patch("pathlib.Path.mkdir", side_effect=RuntimeError("mkdir failed")):
        fs.memory_overlay["/root/.bash_history"] = {"content": "ls\n"}
        fs.save_ip_history()  # Should log and return
