import json
import logging
import time
from datetime import datetime
from typing import Any, Dict

import requests
import urllib3

from .base import OutputPlugin

urllib3.disable_warnings()


class Plugin(OutputPlugin):
    """
    Splunk HTTP Event Collector (HEC) Output Plugin.
    Requires requests.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.url = config.get("url", "https://127.0.0.1:8088/services/collector/event")
        self.token = config.get("token", "")
        self.source = config.get("source", "cyanide")
        self.sourcetype = config.get("sourcetype", "_json")
        self.verify_ssl = config.get("verify_ssl", False)

    def write(self, event: Dict[str, Any]):
        if not self.token:
            return

        headers = {
            "Authorization": f"Splunk {self.token}",
            "Content-Type": "application/json",
        }

        event_ts = event.get("timestamp")
        if event_ts:
            dt = datetime.fromisoformat(event_ts.replace("+00:00", "+0000"))
            event_time = int(dt.timestamp())
        else:
            event_time = int(time.time())

        payload = {
            "time": event_time,
            "source": self.source,
            "sourcetype": self.sourcetype,
            "event": event,
        }

        try:
            resp = requests.post(
                self.url,
                headers=headers,
                data=json.dumps(payload),
                verify=self.verify_ssl,
                timeout=5,
            )
            if resp.status_code not in (200, 201, 202):
                logging.error(f"[Splunk] Write error: status={resp.status_code} text={resp.text}")
        except Exception as e:
            logging.error(f"[Splunk] Delivery failure: {e}")
