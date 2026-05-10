"""
Discord Webhook Output Plugin — Cyanide Framework.

Behaviour
---------
* Fires an alert message ONLY when a ``CRITICAL_ALERT`` (honeytoken hit) event
  arrives.  All other events are silently ignored.
* Polls the configured ``webhook_url``'s parent channel for the ``/report``
  slash-command via Discord's Webhook execute endpoint (the plugin is not a
  full bot, so it cannot read channel messages).  Instead, a dedicated *Bot
  token* with ``bot_token`` config key enables the separate polling loop that
  watches a text channel (``report_channel_id``) for the literal text
  ``/report`` and replies by uploading two files:
    - ``cyanide_iocs.stix.json``
    - ``cyanide_iocs.misp.json``

Config keys
-----------
::

    discord:
      enabled: true
      webhook_url: "https://discord.com/api/webhooks/<ID>/<TOKEN>"
      username: "Cyanide Framework"
      # Optional — enables /report command listener
      bot_token: ""
      report_channel_id: ""
      log_dir: "var/log/cyanide"    # resolved automatically from logging.directory
"""

import io
import logging
import os
import threading
import time
from typing import Any, Dict

import requests

from .base import OutputPlugin

# Constants
_DISCORD_API = "https://discord.com/api/v10"
_POLL_INTERVAL = 5  # seconds between polling for /report command


class Plugin(OutputPlugin):
    """
    Discord Webhook Output Plugin.
    Requires ``requests``.
    """

    def __init__(self, config: Dict[str, Any]):
        # batch_size=1 / batch_timeout=0 → immediate dispatch for honeytoken hits
        config.setdefault("batch_size", 1)
        config.setdefault("batch_timeout", 2.0)
        super().__init__(config)

        self.webhook_url: str = config.get("webhook_url", "")
        self.username: str = config.get("username", "Cyanide Framework")
        self.bot_token: str = config.get("bot_token", "")
        self.report_channel_id: str = str(config.get("report_channel_id", ""))
        self._poll_interval: float = float(config.get("poll_interval", _POLL_INTERVAL))

        # Resolve report file paths from log_dir
        self._log_dir: str = config.get("log_dir", "var/log/cyanide")

        self._last_message_id: str = ""
        self._report_thread: threading.Thread | None = None

    # Plugin lifecycle

    def start(self):
        super().start()
        if self.bot_token and self.report_channel_id:
            self._report_thread = threading.Thread(
                target=self._report_poll_loop, daemon=True, name="discord-report-poll"
            )
            self._report_thread.start()
            logging.info("[Discord] /report command listener started.")

    # Event filtering — only CRITICAL_ALERT passes through

    def emit(self, event: Dict[str, Any]):
        """Accept only honeytoken hit events."""
        if event.get("eventid") != "CRITICAL_ALERT":
            return
        super().emit(event)

    # Formatting

    def _format_honeytoken_alert(self, event: Dict[str, Any]) -> str:
        src_ip = event.get("src_ip", "unknown")
        session = event.get("session", "unknown")
        path = event.get("path", event.get("data", {}).get("path", "unknown"))
        action = event.get("action", event.get("data", {}).get("action", "unknown"))
        timestamp = event.get("timestamp", "")

        return (
            "🚨 **HONEYTOKEN TRIGGERED** 🚨\n"
            f"**Path**: `{path}`\n"
            f"**Action**: `{action}`\n"
            f"**Attacker IP**: `{src_ip}`\n"
            f"**Session**: `{session}`\n"
            f"**Time**: `{timestamp}`"
        )

    # Flush — send via webhook execute

    def flush(self, events: list[Dict[str, Any]]):
        if not self.webhook_url:
            return
        for event in events:
            if event.get("eventid") != "CRITICAL_ALERT":
                continue
            payload = {
                "username": self.username,
                "content": self._format_honeytoken_alert(event),
            }
            try:
                resp = requests.post(self.webhook_url, json=payload, timeout=10)
                if resp.status_code not in (200, 204):
                    logging.error(
                        f"[Discord] Webhook error: status={resp.status_code} body={resp.text[:200]}"
                    )
            except Exception as exc:
                logging.error(f"[Discord] Delivery failure: {exc}")

    def write(self, event: Dict[str, Any]):
        self.flush([event])

    # /report command polling loop (requires bot_token)

    def _report_poll_loop(self):
        """Poll the target channel for the '/report' message and respond with files."""
        headers = {
            "Authorization": f"Bot {self.bot_token}",
            "User-Agent": "CyanideFramework/1.0",
        }
        url = f"{_DISCORD_API}/channels/{self.report_channel_id}/messages?limit=5"

        while True:
            time.sleep(self._poll_interval)
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code != 200:
                    logging.debug(f"[Discord] Poll error: {resp.status_code}")
                    continue

                messages = resp.json()
                if isinstance(messages, list):
                    self._process_poll_messages(messages, headers)
                else:
                    logging.debug(f"[Discord] Poll returned non-list: {messages}")

            except Exception as exc:
                logging.error(f"[Discord] Report poll error: {exc}")

    def _process_poll_messages(self, messages: list, headers: dict):
        """Process a list of messages from the polling loop."""
        for msg in messages:
            msg_id = msg.get("id", "")
            content = msg.get("content", "").strip().lower()

            # Skip already-processed messages
            if msg_id <= self._last_message_id:
                continue

            if content == "/report":
                self._last_message_id = msg_id
                self._send_report_files(headers)
                break

        # Keep track of newest seen message
        if messages:
            newest = messages[0].get("id", "")
            if newest > self._last_message_id:
                self._last_message_id = newest

    def _send_report_files(self, headers: dict):
        """Upload STIX and MISP report files to the configured channel."""
        stix_path = os.path.join(self._log_dir, "reports", "cyanide_iocs.stix.json")
        misp_path = os.path.join(self._log_dir, "reports", "cyanide_iocs.misp.json")

        files_to_send = []
        for path, label in [(stix_path, "STIX 2.1"), (misp_path, "MISP")]:
            if os.path.exists(path):
                try:
                    with open(path, "rb") as fh:
                        files_to_send.append((os.path.basename(path), fh.read(), label))
                except OSError as exc:
                    logging.error(f"[Discord] Cannot read report {path}: {exc}")
            else:
                logging.warning(f"[Discord] Report not found: {path}")

        if not files_to_send:
            # Send a text notice if no reports exist yet
            self._send_channel_message(
                headers,
                "⚠️ No IOC reports have been generated yet. Reports are produced automatically "
                "when IOC reporting is enabled and events occur.",
            )
            return

        url = f"{_DISCORD_API}/channels/{self.report_channel_id}/messages"
        multipart: list[tuple] = [
            ("content", (None, "📄 **Cyanide IOC Reports**", "text/plain")),
        ]
        for idx, (fname, data, label) in enumerate(files_to_send):
            multipart.append(
                (f"files[{idx}]", (fname, io.BytesIO(data), "application/json")),
            )

        try:
            resp = requests.post(url, headers=headers, files=multipart, timeout=30)
            if resp.status_code not in (200, 201):
                logging.error(
                    f"[Discord] File upload error: status={resp.status_code} body={resp.text[:200]}"
                )
            else:
                logging.info("[Discord] IOC report files sent successfully.")
        except Exception as exc:
            logging.error(f"[Discord] File upload failure: {exc}")

    def _send_channel_message(self, headers: dict, content: str):
        url = f"{_DISCORD_API}/channels/{self.report_channel_id}/messages"
        try:
            resp = requests.post(url, headers=headers, json={"content": content}, timeout=10)
            if resp.status_code not in (200, 201):
                logging.error(f"[Discord] Message send error: {resp.status_code}")
        except Exception as exc:
            logging.error(f"[Discord] Message send failure: {exc}")
