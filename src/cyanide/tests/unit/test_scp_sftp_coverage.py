from unittest.mock import AsyncMock, MagicMock

import pytest

from cyanide.vfs.scp import ScpHandler


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.framework = MagicMock()
    session.fs = MagicMock()
    session.src_ip = "1.2.3.4"
    session.session_id = "test-session"
    session.username = "root"
    return session


@pytest.mark.asyncio
async def test_scp_handler_sink_mode(mock_session):
    # Mock stdin to return SCP protocol messages
    # C0644 5 test.txt\n + content + \0
    mock_process = MagicMock()
    mock_process.stdin = AsyncMock()

    # We need to return bytes
    mock_process.stdin.read.side_effect = [
        b"C",
        b"0",
        b"6",
        b"4",
        b"4",
        b" ",
        b"5",
        b" ",
        b"t",
        b"e",
        b"s",
        b"t",
        b".",
        b"t",
        b"x",
        b"t",
        b"\n",
        b"h",
        b"e",
        b"l",
        b"l",
        b"o",
        b"\0",
        b"",  # End
    ]

    handler = ScpHandler(mock_session, process=mock_process)

    # Test handle scp -t /tmp
    rc = await handler.handle("scp -t /tmp")
    assert rc == 0

    # Verify VFS calls
    mock_session.fs.mkfile.assert_called_once()
    args, kwargs = mock_session.fs.mkfile.call_args
    assert args[0] == "/tmp/test.txt"
    assert kwargs["content"] == b"hello"


@pytest.mark.asyncio
async def test_scp_handler_source_mode(mock_session):
    mock_process = MagicMock()
    mock_process.stdin = AsyncMock()
    # Initial ACK from client
    mock_process.stdin.read.side_effect = [b"\0"]

    handler = ScpHandler(mock_session, process=mock_process)

    # Mock VFS node
    node = MagicMock()
    node.is_dir.return_value = False
    node.content = b"world"
    node.perm = "-rw-r--r--"
    mock_session.fs.get_node.return_value = node

    rc = await handler.handle("scp -f /tmp/world.txt")
    assert rc == 0

    # Verify output (header + content + null)
    # The handler writes to process.channel.write(data.decode('latin-1'))
    calls = mock_process.channel.write.call_args_list
    output = "".join(c[0][0] for c in calls)
    assert "C0644 5 world.txt" in output
    assert "world" in output


@pytest.mark.asyncio
async def test_scp_handler_dir_mode(mock_session):
    mock_process = MagicMock()
    mock_process.stdin = AsyncMock()

    # D0755 0 subdir\n + C0644 4 f.txt\n + data + \0 + E\n
    mock_process.stdin.read.side_effect = [
        b"D",
        b"0",
        b"7",
        b"5",
        b"5",
        b" ",
        b"0",
        b" ",
        b"s",
        b"u",
        b"b",
        b"d",
        b"i",
        b"r",
        b"\n",
        b"C",
        b"0",
        b"6",
        b"4",
        b"4",
        b" ",
        b"4",
        b" ",
        b"f",
        b".",
        b"t",
        b"x",
        b"t",
        b"\n",
        b"d",
        b"a",
        b"t",
        b"a",
        b"\0",
        b"E",
        b"\n",
        b"",
    ]

    handler = ScpHandler(mock_session, process=mock_process)
    rc = await handler.handle("scp -r -t /tmp")
    assert rc == 0

    mock_session.fs.mkdir_p.assert_called_with("/tmp/subdir")
    mock_session.fs.mkfile.assert_called_with(
        "/tmp/subdir/f.txt", content=b"data", owner="root", group="root"
    )


def test_scp_perm_to_mode():
    handler = ScpHandler(MagicMock())
    assert handler._perm_to_mode("drwxr-xr-x") == 0o755
    assert handler._perm_to_mode("-rw-r--r--") == 0o644
    assert handler._perm_to_mode("-r--------") == 0o400
    assert handler._perm_to_mode("") == 0o644
