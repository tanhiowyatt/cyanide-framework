"""
Telegram Bot Output Plugin — Cyanide Framework.

Behaviour
---------
* Fires a ``sendMessage`` ONLY when a ``CRITICAL_ALERT`` (honeytoken hit)
  event arrives.  All other events are silently ignored.
* Polls ``getUpdates`` for incoming ``/report`` messages and replies by
  uploading two documents via ``sendDocument``:
    - ``cyanide_iocs.stix.json``
    - ``cyanide_iocs.misp.json``

Config keys
-----------
::

    telegram:
      enabled: true
      token: "123456:ABC-DEF..."
      chat_id: "987654321"
      log_dir: "var/log/cyanide"    # resolved automatically from logging.directory
"""

import logging
import os
import threading
import time
from typing import Any, Dict

import requests

from .base import OutputPlugin

_TG_BASE = "https://api.telegram.org/bot{token}/{method}"
_POLL_TIMEOUT = 30  # long-poll timeout in seconds (getUpdates)
_POLL_INTERVAL = 2  # delay between poll cycles after an error
_PARSE_MODE = "HTML"


def _api(token: str, method: str) -> str:
    return _TG_BASE.format(token=token, method=method)


class Plugin(OutputPlugin):
    """
    Telegram Bot API Output Plugin.
    Requires ``requests``.
    """

    def __init__(self, config: Dict[str, Any]):
        config.setdefault("batch_size", 1)
        config.setdefault("batch_timeout", 2.0)
        super().__init__(config)

        self.token: str = config.get("token", "")
        self.chat_id: str = str(config.get("chat_id", ""))

        # Resolve report file paths
        self._log_dir: str = config.get("log_dir", "var/log/cyanide")

        self._update_offset: int = 0
        self._poll_thread: threading.Thread | None = None

    # Plugin lifecycle

    def start(self):
        super().start()
        if self.token and self.chat_id:
            self._poll_thread = threading.Thread(
                target=self._update_poll_loop, daemon=True, name="telegram-update-poll"
            )
            self._poll_thread.start()
            logging.info("[Telegram] /report command listener started.")

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
            "🚨 <b>HONEYTOKEN TRIGGERED</b> 🚨\n"
            f"<b>Path:</b> <code>{path}</code>\n"
            f"<b>Action:</b> <code>{action}</code>\n"
            f"<b>Attacker IP:</b> <code>{src_ip}</code>\n"
            f"<b>Session:</b> <code>{session}</code>\n"
            f"<b>Time:</b> <code>{timestamp}</code>"
        )

    # Flush — sendMessage for honeytoken alerts

    def flush(self, events: list[Dict[str, Any]]):
        if not self.token or not self.chat_id:
            return
        for event in events:
            if event.get("eventid") != "CRITICAL_ALERT":
                continue
            payload = {
                "chat_id": self.chat_id,
                "text": self._format_honeytoken_alert(event),
                "parse_mode": _PARSE_MODE,
            }
            try:
                resp = requests.post(_api(self.token, "sendMessage"), json=payload, timeout=10)
                if not resp.ok:
                    logging.error(
                        f"[Telegram] sendMessage error: status={resp.status_code} "
                        f"body={resp.text[:200]}"
                    )
            except Exception as exc:
                logging.error(f"[Telegram] Delivery failure: {exc}")

    def write(self, event: Dict[str, Any]):
        self.flush([event])

    # getUpdates polling loop

    def _update_poll_loop(self):
        """Long-poll Telegram getUpdates, react to /report command."""
        url = _api(self.token, "getUpdates")
        while self.running:
            try:
                params: Dict[str, Any] = {
                    "timeout": _POLL_TIMEOUT,
                    "allowed_updates": ["message"],
                }
                if self._update_offset:
                    params["offset"] = self._update_offset

                resp = requests.get(url, params=params, timeout=_POLL_TIMEOUT + 5)
                if not resp.ok:
                    logging.debug(f"[Telegram] getUpdates error: {resp.status_code}")
                    time.sleep(_POLL_INTERVAL)
                    continue

                data = resp.json()
                self._process_updates(data.get("result", []))
                # Yield to other threads between poll cycles.  Without this
                # Python 3.12's revised GIL scheduling can starve the daemon
                # thread and cause the test (and real usage) to miss updates.
                time.sleep(0.05)

            except Exception as exc:
                logging.error(f"[Telegram] Poll error: {exc}")
                time.sleep(_POLL_INTERVAL)

    def _process_updates(self, updates: list):
        """Process a list of updates from the Telegram API."""
        for update in updates:
            update_id: int = update.get("update_id", 0)
            self._update_offset = update_id + 1

            msg = update.get("message", {})
            text = (msg.get("text") or "").strip().lower()
            chat_id_incoming = str(msg.get("chat", {}).get("id", ""))

            # Only respond to messages from the configured chat
            if chat_id_incoming != self.chat_id:
                continue

            if text in ("/report", "/report@cyanidebot"):
                self._send_report_documents()

    # /report — send IOC files as Telegram documents

    def _send_report_documents(self):
        """Send STIX and MISP report files as Telegram documents."""
        stix_path = os.path.join(self._log_dir, "reports", "cyanide_iocs.stix.json")
        misp_path = os.path.join(self._log_dir, "reports", "cyanide_iocs.misp.json")

        found_any = False
        for path, label in [(stix_path, "STIX 2.1 IOC Bundle"), (misp_path, "MISP IOC Event")]:
            if not os.path.exists(path):
                logging.warning(f"[Telegram] Report not found: {path}")
                continue
            found_any = True
            try:
                with open(path, "rb") as fh:
                    file_data = fh.read()

                caption = f"📄 <b>Cyanide Report — {label}</b>"
                resp = requests.post(
                    _api(self.token, "sendDocument"),
                    data={
                        "chat_id": self.chat_id,
                        "caption": caption,
                        "parse_mode": _PARSE_MODE,
                    },
                    files={"document": (os.path.basename(path), file_data, "application/json")},
                    timeout=30,
                )
                if not resp.ok:
                    logging.error(
                        f"[Telegram] sendDocument error: status={resp.status_code} "
                        f"body={resp.text[:200]}"
                    )
                else:
                    logging.info(f"[Telegram] Sent report file: {os.path.basename(path)}")
            except OSError as exc:
                logging.error(f"[Telegram] Cannot read report {path}: {exc}")
            except Exception as exc:
                logging.error(f"[Telegram] sendDocument failure: {exc}")

        if not found_any:
            self._send_text(
                "⚠️ No IOC reports have been generated yet. Reports are produced automatically "
                "when IOC reporting is enabled and events occur."
            )

    def _send_text(self, text: str):
        try:
            requests.post(
                _api(self.token, "sendMessage"),
                json={"chat_id": self.chat_id, "text": text, "parse_mode": _PARSE_MODE},
                timeout=10,
            )
        except Exception as exc:
            logging.error(f"[Telegram] sendMessage failure: {exc}")
