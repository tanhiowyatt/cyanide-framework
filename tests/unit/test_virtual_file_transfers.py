from unittest.mock import AsyncMock, MagicMock

import pytest

from cyanide.vfs.engine import FakeFilesystem
from cyanide.vfs.rsync import RsyncHandler
from cyanide.vfs.scp import SCPHandler


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.honeypot = MagicMock()
    session.honeypot.config = {
        "ssh": {"allow_upload": True, "allow_download": True, "max_upload_size_mb": 50}
    }
    session.honeypot.logger = MagicMock()
    session.honeypot.save_quarantine_file = MagicMock()
    session.fs = FakeFilesystem()
    session.src_ip = "192.168.1.100"
    session.username = "root"
    session.conn_id = "test_conn"
    session.channel = MagicMock()
    return session


@pytest.fixture
def mock_process():
    process = MagicMock()
    process.stdin = AsyncMock()
    process.stdout = MagicMock()
    process.stderr = MagicMock()
    process.channel = MagicMock()
    return process


@pytest.mark.asyncio
async def test_rsync_handshake_and_error(mock_session, mock_process):
    # Test RsyncHandler in process_factory mode
    mock_process.stdin.read.return_value = b"@RSYNCD: 31.0\n"

    handler = RsyncHandler(mock_session, process=mock_process)
    rc = await handler.handle("rsync --server . /tmp/test")

    # Needs to return 1 (error code) for honeypot behavior
    assert rc == 1

    # Should have sent @RSYNCD: 31.0\n greeting
    mock_process.channel.write.assert_any_call(b"@RSYNCD: 31.0\n")

    # Should log operations
    mock_session.honeypot.logger.log_event.assert_called()


@pytest.mark.asyncio
async def test_scp_upload_sink_mode(mock_session, mock_process):
    # scp -t /tmp
    mock_session.fs.mkdir_p("/tmp")

    # Override _readuntil and _read to simulate the protocol exchange robustly.
    mock_process.readuntil_call_count = 0

    async def mock_readuntil(sep, timeout=10.0):
        if mock_process.readuntil_call_count == 0:
            mock_process.readuntil_call_count += 1
            return b"C0644 11 test.txt\n"
        return b""

    handler = SCPHandler(mock_session, process=mock_process)
    handler._readuntil = mock_readuntil

    async def mock_read_fixed(size):
        return b"hello world"

    handler._read_fixed = mock_read_fixed

    async def mock_read(size, timeout=10.0):
        return b"\0"

    handler._read = mock_read

    rc = await handler.handle("scp -t /tmp")

    # Handled completely
    assert rc == 0

    # Check if file was created in VFS
    assert mock_session.fs.exists("/tmp/test.txt")
    assert mock_session.fs.get_content("/tmp/test.txt") == "hello world"

    # Check quarantine called
    mock_session.honeypot.save_quarantine_file.assert_called_with(
        "test.txt", b"hello world", "conn_test_conn", "192.168.1.100"
    )


@pytest.mark.asyncio
async def test_scp_download_source_mode(mock_session, mock_process):
    # scp -f /etc/passwd
    mock_session.fs.mkdir_p("/etc")
    mock_session.fs.mkfile("/etc/passwd", content="root:x:0:0:")

    # Client sends null ack
    mock_process.stdin.read.return_value = b"\0"

    handler = SCPHandler(mock_session, process=mock_process)

    # Override _read to simulate the exact behavior
    async def mock_read(size, timeout=10.0):
        return b"\0"

    handler._read = mock_read

    rc = await handler.handle("scp -f /etc/passwd")

    assert rc == 0

    # Output should contain C command (file metadata)
    written_data = b"".join(call.args[0] for call in mock_process.channel.write.call_args_list)
    assert b"C0644 11 passwd\n" in written_data
    assert b"root:x:0:0:" in written_data


@pytest.mark.asyncio
async def test_scp_disabled_download(mock_session, mock_process):
    # Disable downloads
    mock_session.honeypot.config["ssh"]["allow_download"] = False

    handler = SCPHandler(mock_session, process=mock_process)
    rc = await handler.handle("scp -f /etc/passwd")

    assert rc == 1
    mock_process.channel.write.assert_any_call(b"\x01SCP downloads disabled\n")
