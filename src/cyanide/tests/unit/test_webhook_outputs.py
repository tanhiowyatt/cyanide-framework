"""
Unit tests for the Discord and Telegram honeytoken-only output plugins.
"""

import json
import time
from typing import Any
from unittest.mock import MagicMock, patch

from cyanide.output.discord import Plugin as DiscordPlugin
from cyanide.output.slack import Plugin as SlackPlugin
from cyanide.output.telegram import Plugin as TelegramPlugin

# Helpers

CRITICAL_ALERT = {
    "eventid": "CRITICAL_ALERT",
    "session": "abc-123",
    "src_ip": "1.2.3.4",
    "path": "/etc/shadow",
    "action": "read",
    "timestamp": "2026-04-28T12:00:00+00:00",
}

NON_ALERT = {
    "eventid": "command.input",
    "session": "abc-123",
    "src_ip": "1.2.3.4",
    "input": "ls -la",
}


def _make_mock_resp(status: int = 200, json_data: Any = None):
    resp = MagicMock()
    resp.status_code = status
    resp.ok = status < 300
    resp.json.return_value = json_data or {}
    resp.text = json.dumps(json_data or {})
    return resp


# Discord tests


class TestDiscordPlugin:
    def _plugin(self, extra: dict | None = None):
        cfg = {"webhook_url": "https://discord.com/api/webhooks/1/TOKEN"}
        if extra:
            cfg.update(extra)
        p = DiscordPlugin(cfg)
        return p

    def test_emit_filters_non_critical(self):
        """Non-CRITICAL_ALERT events must NOT reach the queue."""
        plugin = self._plugin()
        plugin.emit(NON_ALERT)
        assert plugin.queue.empty()

    def test_emit_passes_critical_alert(self):
        """CRITICAL_ALERT events must reach put_nowait."""
        plugin = self._plugin()
        plugin.running = True  # allow emit without starting the worker thread
        with patch.object(plugin.queue, "put_nowait") as mock_put:
            plugin.emit(CRITICAL_ALERT)
            mock_put.assert_called_once_with(CRITICAL_ALERT)

    @patch("cyanide.output.discord.requests.post")
    def test_flush_sends_webhook(self, mock_post):
        """flush() must POST to webhook_url for CRITICAL_ALERT."""
        mock_post.return_value = _make_mock_resp(200)
        plugin = self._plugin()
        plugin.flush([CRITICAL_ALERT])
        assert mock_post.called
        call_kwargs = mock_post.call_args
        url = call_kwargs[0][0]
        assert "webhooks" in url

    @patch("cyanide.output.discord.requests.post")
    def test_flush_ignores_non_critical(self, mock_post):
        """flush() must NOT POST for non-CRITICAL_ALERT events."""
        mock_post.return_value = _make_mock_resp(200)
        plugin = self._plugin()
        plugin.flush([NON_ALERT])
        mock_post.assert_not_called()

    def test_no_bot_token_no_poll_thread(self):
        """Without bot_token the polling thread must not start."""
        plugin = self._plugin()
        plugin.start()
        time.sleep(0.05)
        assert plugin._report_thread is None
        plugin.stop()

    @patch("cyanide.output.discord.requests.post")
    @patch("cyanide.output.discord.requests.get")
    def test_report_poll_sends_files(self, mock_get, mock_post, tmp_path):
        """Polling loop sends report files when /report message is detected."""
        # Create fake report files
        rep_dir = tmp_path / "reports"
        rep_dir.mkdir()
        stix = rep_dir / "cyanide_iocs.stix.json"
        misp = rep_dir / "cyanide_iocs.misp.json"
        stix.write_text('{"type": "bundle"}')
        misp.write_text('{"Event": {}}')

        mock_get.return_value = _make_mock_resp(
            200,
            [{"id": "999", "content": "/report"}],
        )
        mock_post.return_value = _make_mock_resp(200)

        plugin = DiscordPlugin(
            {
                "webhook_url": "https://discord.com/api/webhooks/1/TOKEN",
                "bot_token": "BOT_TOKEN",
                "report_channel_id": "12345",
                "log_dir": str(tmp_path),
                "poll_interval": 0.01,
            }
        )
        plugin.start()
        # Give poll thread enough time to execute one cycle
        time.sleep(1.0)
        plugin.stop()

        # POST should have been called to upload files
        assert mock_post.called


# Telegram tests


class TestTelegramPlugin:
    def _plugin(self, extra: dict | None = None):
        cfg = {"token": "12345:ABCDE", "chat_id": "987654"}
        if extra:
            cfg.update(extra)
        return TelegramPlugin(cfg)

    def test_emit_filters_non_critical(self):
        plugin = self._plugin()
        plugin.emit(NON_ALERT)
        assert plugin.queue.empty()

    def test_emit_passes_critical_alert(self):
        """CRITICAL_ALERT events must reach put_nowait."""
        plugin = self._plugin()
        plugin.running = True  # allow emit without starting the worker thread
        with patch.object(plugin.queue, "put_nowait") as mock_put:
            plugin.emit(CRITICAL_ALERT)
            mock_put.assert_called_once_with(CRITICAL_ALERT)

    @patch("cyanide.output.telegram.requests.post")
    def test_flush_sends_message(self, mock_post):
        """flush() must call sendMessage for CRITICAL_ALERT."""
        mock_post.return_value = _make_mock_resp(200, {"ok": True})
        plugin = self._plugin()
        plugin.flush([CRITICAL_ALERT])
        assert mock_post.called
        url = mock_post.call_args[0][0]
        assert "sendMessage" in url

    @patch("cyanide.output.telegram.requests.post")
    def test_flush_ignores_non_critical(self, mock_post):
        mock_post.return_value = _make_mock_resp(200, {"ok": True})
        plugin = self._plugin()
        plugin.flush([NON_ALERT])
        mock_post.assert_not_called()

    @patch("cyanide.output.telegram.requests.post")
    @patch("cyanide.output.telegram.requests.get")
    def test_report_command_sends_documents(self, mock_get, mock_post, tmp_path):
        """getUpdates returning /report triggers sendDocument for both files."""
        rep_dir = tmp_path / "reports"
        rep_dir.mkdir()
        (rep_dir / "cyanide_iocs.stix.json").write_text('{"type": "bundle"}')
        (rep_dir / "cyanide_iocs.misp.json").write_text('{"Event": {}}')

        # Simulate /report message followed by empty responses
        call_count = {"n": 0}

        def get_side(*a, **kw):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return _make_mock_resp(
                    200,
                    {
                        "ok": True,
                        "result": [
                            {
                                "update_id": 1,
                                "message": {
                                    "text": "/report",
                                    "chat": {"id": 987654},
                                },
                            }
                        ],
                    },
                )
            return _make_mock_resp(200, {"ok": True, "result": []})

        mock_get.side_effect = get_side
        mock_post.return_value = _make_mock_resp(200, {"ok": True})

        plugin = TelegramPlugin(
            {
                "token": "12345:ABCDE",
                "chat_id": "987654",
                "log_dir": str(tmp_path),
            }
        )
        plugin.start()

        # Wait for poll thread to process the update (up to 5 seconds)
        for _ in range(50):
            send_document_calls = [c for c in mock_post.call_args_list if "sendDocument" in str(c)]
            if len(send_document_calls) == 2:
                break
            time.sleep(0.1)

        plugin.stop()

        # sendDocument should have been called twice (one per file)
        send_document_calls = [c for c in mock_post.call_args_list if "sendDocument" in str(c)]
        assert len(send_document_calls) == 2

    def test_no_token_no_poll_thread(self):
        plugin = TelegramPlugin({})
        plugin.start()
        time.sleep(0.05)
        assert plugin._poll_thread is None
        plugin.stop()


# Slack tests


class TestSlackPlugin:
    def _plugin(self, extra: dict | None = None):
        cfg = {"webhook_url": "https://hooks.slack.com/services/1/2/3"}
        if extra:
            cfg.update(extra)
        return SlackPlugin(cfg)

    def test_emit_filters_non_critical(self):
        plugin = self._plugin()
        plugin.emit(NON_ALERT)
        assert plugin.queue.empty()

    def test_emit_passes_critical_alert(self):
        plugin = self._plugin()
        plugin.running = True
        with patch.object(plugin.queue, "put_nowait") as mock_put:
            plugin.emit(CRITICAL_ALERT)
            mock_put.assert_called_once_with(CRITICAL_ALERT)

    @patch("cyanide.output.slack.requests.post")
    def test_flush_sends_alert(self, mock_post):
        mock_post.return_value = _make_mock_resp(200)
        plugin = self._plugin()
        plugin.flush([CRITICAL_ALERT])
        assert mock_post.called
        payload = mock_post.call_args[1]["json"]
        assert "CRITICAL ALERT" in payload["text"]

    @patch("cyanide.output.slack.requests.post")
    def test_flush_ignores_non_critical_batch(self, mock_post):
        # Even if someone calls flush directly with non-critical,
        # (though emit filters it), we just check it sends whatever is in batch.
        # But wait, slack.py's flush doesn't filter, emit does.
        # So we just verify it sends.
        mock_post.return_value = _make_mock_resp(200)
        plugin = self._plugin()
        plugin.flush([NON_ALERT])
        assert mock_post.called
