import logging
from typing import Any, Dict

import requests

from .base import OutputPlugin


class Plugin(OutputPlugin):
    """
    Slack Webhook Output Plugin.
    Optimized for high-priority critical alerts (Honeytoken triggers).
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.webhook_url = config.get("webhook_url", "")
        self.username = config.get("username", "Cyanide Framework")
        self.icon_emoji = config.get("icon_emoji", ":skull_and_crossbones:")
        self.max_length = config.get("max_content_length", 4000)

    def emit(self, event: Dict[str, Any]):
        """Filter events: only CRITICAL_ALERT (honeytoken hits) allowed."""
        if not self.running:
            return
        if event.get("eventid") != "CRITICAL_ALERT":
            return
        super().emit(event)

    def _format_alert(self, event: Dict[str, Any]) -> str:
        """Format critical honeytoken alert for Slack."""
        session = event.get("session", "unknown")
        src_ip = event.get("src_ip", "unknown")
        path = event.get("path", "unknown")
        action = event.get("action", "unknown")

        return (
            f"🚨 *CRITICAL ALERT*: `Honeytoken Triggered` 🚨\n"
            f"*Path*: `{path}`\n"
            f"*Action*: `{action}`\n"
            f"*Attacker IP*: `{src_ip}`\n"
            f"*Session*: `{session}`\n"
            f"---"
        )

    def flush(self, events: list[Dict[str, Any]]):
        """Send formatted alerts to Slack webhook."""
        if not self.webhook_url or not events:
            return

        for event in events:
            msg = self._format_alert(event)
            # Slack has a limit of 40000 characters, but 4000 is safer for visibility
            if len(msg) > self.max_length:
                msg = msg[: self.max_length - 3] + "..."

            payload = {
                "username": self.username,
                "icon_emoji": self.icon_emoji,
                "text": msg,
            }

            try:
                resp = requests.post(self.webhook_url, json=payload, timeout=10)
                if resp.status_code not in (200, 201, 204):
                    logging.error(
                        f"[Slack] Write error: status={resp.status_code} text={resp.text}"
                    )
            except Exception as e:
                logging.error(f"[Slack] Delivery failure: {e}")

    def write(self, event: Dict[str, Any]):
        self.flush([event])
