import json
import logging
import logging.handlers
import socket
from typing import Any, Dict

from .base import OutputPlugin


class Plugin(OutputPlugin):
    """
    Syslog Output Plugin for UNIX sockets and network Syslog forwarding.
    """

    DEFAULT_SYSLOG_ADDR = "/dev/log"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.address = config.get("address", self.DEFAULT_SYSLOG_ADDR)
        self.facility = config.get("facility", "user")
        self.enabled = config.get("enabled", False)

        facility_map = {
            "auth": logging.handlers.SysLogHandler.LOG_AUTH,
            "cron": logging.handlers.SysLogHandler.LOG_CRON,
            "daemon": logging.handlers.SysLogHandler.LOG_DAEMON,
            "local0": logging.handlers.SysLogHandler.LOG_LOCAL0,
            "local1": logging.handlers.SysLogHandler.LOG_LOCAL1,
            "local2": logging.handlers.SysLogHandler.LOG_LOCAL2,
            "local3": logging.handlers.SysLogHandler.LOG_LOCAL3,
            "local4": logging.handlers.SysLogHandler.LOG_LOCAL4,
            "local5": logging.handlers.SysLogHandler.LOG_LOCAL5,
            "local6": logging.handlers.SysLogHandler.LOG_LOCAL6,
            "local7": logging.handlers.SysLogHandler.LOG_LOCAL7,
            "user": logging.handlers.SysLogHandler.LOG_USER,
        }
        fac = facility_map.get(self.facility.lower(), logging.handlers.SysLogHandler.LOG_USER)

        self.logger = logging.getLogger("cyanide_syslog_plugin")
        self.logger.setLevel(logging.INFO)

        if self.logger.handlers:
            self.logger.handlers.clear()

        try:
            handler = None

            if isinstance(self.address, str) and self.address == self.DEFAULT_SYSLOG_ADDR:
                if not self._check_dev_log():
                    logging.warning(
                        f"[Syslog] {self.DEFAULT_SYSLOG_ADDR} not accessible, disabling plugin"
                    )
                    self.enabled = False
                    return

            if isinstance(self.address, str):
                handler = logging.handlers.SysLogHandler(address=self.address, facility=fac)

            elif isinstance(self.address, (list, tuple)) and len(self.address) == 2:
                handler = logging.handlers.SysLogHandler(
                    address=(self.address[0], int(self.address[1])),
                    facility=fac,
                    socktype=socket.SOCK_DGRAM,
                )

            if handler:
                formatter = logging.Formatter("Cyanide: %(message)s")
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                logging.info(f"[Syslog] Initialized with address: {self.address}")

        except PermissionError as e:
            logging.error(f"[Syslog] Permission denied for {self.address}: {e}")
            self.enabled = False
        except Exception as e:
            logging.error(f"[Syslog] Initialization failure: {e}")
            self.enabled = False

    def _check_dev_log(self) -> bool:
        """Checks the availability of /dev/log"""
        try:
            test_sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            test_sock.connect(self.DEFAULT_SYSLOG_ADDR)
            test_sock.close()
            return True
        except Exception:
            return False

    def write(self, event: Dict[str, Any]):
        if not self.enabled:
            return

        try:
            payload = json.dumps(event, ensure_ascii=False)
            self.logger.info(payload)
        except Exception as e:
            logging.error(f"[Syslog] Write failure: {e}")
