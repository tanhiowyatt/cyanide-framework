from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cyanide.services.telnet_handler import TelnetHandler


@pytest.fixture
def mock_server(mock_logger):
    server = MagicMock()
    server.logger = mock_logger
    server.services = MagicMock()
    server.stats = MagicMock()
    server.is_valid_user.return_value = True
    server.get_filesystem.return_value = MagicMock()
    return server


@pytest.fixture
def telnet_handler(mock_server):
    config = {"telnet": {"timeout": 60, "banner": "Test Banner\n"}}
    return TelnetHandler(mock_server, config)


@pytest.mark.asyncio
async def test_telnet_auth_success(telnet_handler, mock_server):
    reader = AsyncMock()
    writer = MagicMock()
    writer.drain = AsyncMock()
    writer.get_extra_info.return_value = ("1.2.3.4", 12345)

    with patch.object(telnet_handler, "_read_line_simple", side_effect=["root", "cyanide"]):
        with patch.object(telnet_handler, "_run_shell") as mock_run_shell:
            await telnet_handler.handle_connection(reader, writer)
            writer.close.assert_called()
            mock_run_shell.assert_called_once()
            assert mock_server.is_valid_user.called


@pytest.mark.asyncio
async def test_telnet_auth_failure(telnet_handler, mock_server):
    reader = AsyncMock()
    writer = MagicMock()
    writer.drain = AsyncMock()
    writer.get_extra_info.return_value = ("1.2.3.4", 12345)

    mock_server.is_valid_user.return_value = False

    with patch.object(telnet_handler, "_read_line_simple", side_effect=["root", "wrong"]):
        with patch.object(telnet_handler, "_run_shell") as mock_run_shell:
            await telnet_handler.handle_connection(reader, writer)
            writer.close.assert_called()
            mock_run_shell.assert_not_called()


@pytest.mark.asyncio
async def test_telnet_run_shell(telnet_handler):
    reader = AsyncMock()
    writer = MagicMock()
    writer.drain = AsyncMock()
    shell = MagicMock()
    shell.cwd = "/root"
    shell.pending_input_callback = None
    shell.pending_input_prompt = None
    shell.execute = AsyncMock(return_value=("output\n", "", 0))

    with patch.object(telnet_handler, "_read_line_advanced", side_effect=["ls", "exit"]):
        await telnet_handler._run_shell(reader, writer, shell, "root", "session_id")

        assert shell.execute.call_count == 1
        shell.execute.assert_called_with("ls")
