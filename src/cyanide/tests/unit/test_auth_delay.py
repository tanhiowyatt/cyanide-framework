from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cyanide.core.server import SSHServerFactory


@pytest.fixture
def mock_framework():
    hp = MagicMock()
    hp.config = {"ssh": {"auth_delay": 1.0}, "telnet": {"auth_delay": 1.0}}
    hp.is_valid_user.return_value = True
    hp.logger = MagicMock()
    hp.stats = MagicMock()
    hp.tracer = MagicMock()
    hp.services = MagicMock()
    return hp


@pytest.mark.asyncio
async def test_ssh_auth_delay(mock_framework):
    factory = SSHServerFactory(mock_framework)
    factory.conn_id = "test_conn"
    factory.src_ip = "1.2.3.4"

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        success = await factory.validate_password("user", "pass")
        assert success is True
        mock_sleep.assert_called_once_with(1.0)


@pytest.mark.asyncio
async def test_ssh_no_delay_on_failure(mock_framework):
    mock_framework.is_valid_user.return_value = False
    factory = SSHServerFactory(mock_framework)

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        success = await factory.validate_password("user", "wrong")
        assert success is False
        mock_sleep.assert_not_called()
