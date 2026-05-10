import json
import sqlite3
import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock database drivers before importing plugins
mysql_mock = MagicMock()
sys.modules["mysql"] = mysql_mock
sys.modules["mysql.connector"] = mysql_mock.connector

psycopg_mock = MagicMock()
sys.modules["psycopg"] = psycopg_mock

pymongo_mock = MagicMock()
sys.modules["pymongo"] = pymongo_mock

rethinkdb_mock = MagicMock()
sys.modules["rethinkdb"] = rethinkdb_mock

from cyanide.output.mongodb import Plugin as MongoDBPlugin  # noqa: E402
from cyanide.output.mysql import Plugin as MySQLPlugin  # noqa: E402
from cyanide.output.postgresql import Plugin as PostgreSQLPlugin  # noqa: E402
from cyanide.output.rethinkdb import Plugin as RethinkDBPlugin  # noqa: E402
from cyanide.output.slack import Plugin as SlackPlugin  # noqa: E402
from cyanide.output.splunk_hec import Plugin as SplunkHECPlugin  # noqa: E402
from cyanide.output.sqlite import Plugin as SQLitePlugin  # noqa: E402
from cyanide.output.syslog import Plugin as SyslogPlugin  # noqa: E402
from cyanide.output.telegram import Plugin as TelegramPlugin  # noqa: E402


def test_sqlite_plugin(tmp_path):
    db_path = tmp_path / "test.sqlite"
    config = {"path": str(db_path), "table": "test_events"}

    plugin = SQLitePlugin(config)

    # Test initialization
    assert db_path.exists()

    # Test write
    event = {
        "timestamp": "2023-01-01T00:00:00Z",
        "session": "test-session",
        "eventid": "test-event",
        "some_data": "value",
    }
    plugin.write(event)

    # Verify in DB
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM test_events")
        row = cursor.fetchone()
        assert row[1] == "2023-01-01T00:00:00Z"
        assert row[2] == "test-session"
        assert row[3] == "test-event"
        data = json.loads(row[4])
        assert data["some_data"] == "value"
    finally:
        conn.close()

    plugin.close()

    # Test close
    plugin.close()
    assert plugin.conn is None


def test_sqlite_invalid_table():
    with pytest.raises(ValueError):
        SQLitePlugin({"table": "drop table students;--"})


def test_slack_plugin():
    config = {
        "webhook_url": "https://hooks.slack.com/services/test",
        "username": "TestBot",
        "max_content_length": 1000,  # Increased to avoid truncation in test
    }
    plugin = SlackPlugin(config)
    plugin.running = True

    # Test emit filter (only CRITICAL_ALERT)
    non_critical = {"eventid": "INFO"}
    plugin.emit(non_critical)
    # Should not be in queue
    assert plugin.queue.qsize() == 0

    critical = {
        "eventid": "CRITICAL_ALERT",
        "path": "/etc/shadow",
        "action": "read",
        "src_ip": "1.2.3.4",
        "session": "abc",
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        plugin.write(critical)

        assert mock_post.called
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["username"] == "TestBot"
        assert "/etc/shadow" in kwargs["json"]["text"]


def test_telegram_plugin(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    reports_dir = log_dir / "reports"
    reports_dir.mkdir()

    config = {"token": "123:abc", "chat_id": "456", "log_dir": str(log_dir)}

    with patch("requests.post") as mock_post:
        plugin = TelegramPlugin(config)
        plugin.running = True

        event = {"eventid": "CRITICAL_ALERT", "src_ip": "1.1.1.1"}

        mock_post.return_value.status_code = 200
        plugin.write(event)
        assert mock_post.called

        # Test report sending
        stix_file = reports_dir / "cyanide_iocs.stix.json"
        stix_file.write_text("{}")

        mock_post.reset_mock()
        plugin._send_report_documents()
        assert mock_post.called  # Should call sendDocument


def test_mysql_plugin():
    config = {"host": "localhost", "user": "root", "password": "pw", "database": "db"}
    plugin = MySQLPlugin(config)
    event = {"eventid": "test"}
    plugin.write(event)
    assert mysql_mock.connector.connect.called


def test_postgresql_plugin():
    config = {"dsn": "postgres://..."}
    plugin = PostgreSQLPlugin(config)
    event = {"eventid": "test"}
    plugin.write(event)
    assert psycopg_mock.connect.called


def test_mongodb_plugin():
    config = {"uri": "mongodb://..."}
    plugin = MongoDBPlugin(config)
    event = {"eventid": "test"}
    plugin.write(event)
    assert pymongo_mock.MongoClient.called


def test_rethinkdb_plugin():
    config = {"host": "localhost"}
    plugin = RethinkDBPlugin(config)
    event = {"eventid": "test"}
    plugin.write(event)
    # rethinkdb plugin uses rethinkdb.r.connect
    assert rethinkdb_mock.r.connect.called


def test_syslog_plugin():
    config = {"address": "localhost", "port": 514}
    with patch("logging.handlers.SysLogHandler") as mock_handler:
        plugin = SyslogPlugin(config)
        event = {"eventid": "test"}
        plugin.write(event)
        assert mock_handler.called


def test_splunk_hec_plugin():
    config = {"url": "http://splunk:8088", "token": "abc"}
    with patch("requests.post") as mock_post:
        plugin = SplunkHECPlugin(config)
        event = {"eventid": "test"}
        mock_post.return_value.status_code = 200
        plugin.write(event)
        assert mock_post.called
