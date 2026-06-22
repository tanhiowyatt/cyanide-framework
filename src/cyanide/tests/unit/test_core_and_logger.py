from pathlib import Path
from unittest.mock import MagicMock, patch

from cyanide.core.paths import (
    get_default_config_path,
    get_package_root,
    get_profiles_dir,
)
from cyanide.core.terminal_utils import process_terminal_input
from cyanide.logger import CyanideLogger


def test_process_terminal_input():
    assert process_terminal_input("abc") == "abc"
    assert process_terminal_input("abc\x08") == "ab"
    assert process_terminal_input("abc\x7f") == "ab"
    assert process_terminal_input("\x08") == ""
    assert process_terminal_input("abc\x03") == ""
    assert process_terminal_input("abc\x15") == ""
    assert process_terminal_input("a\x01b\x02c") == "abc"
    assert process_terminal_input("a\nb\rc\td\x1be") == "a\nb\rc\td\x1be"
    assert process_terminal_input("a\x01b", preserve_control=True) == "a\x01b"
    assert process_terminal_input("a\x01b\x08", preserve_control=True) == "a\x01"


def test_paths_package_root():
    root = get_package_root()
    assert root.name == "cyanide"
    assert (root / "core").is_dir()


def test_paths_config_path(tmp_path, monkeypatch):
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    app_yaml = config_dir / "app.yaml"
    app_yaml.touch()

    monkeypatch.chdir(tmp_path)
    assert get_default_config_path() == Path("configs/app.yaml")

    app_yaml.unlink()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setattr(Path, "home", lambda: home_dir)

    home_cfg = home_dir / ".cyanide" / "app.yaml"
    home_cfg.parent.mkdir()
    home_cfg.touch()

    assert get_default_config_path() == home_cfg


def test_paths_profiles_dir(tmp_path, monkeypatch):
    profiles_dir = tmp_path / "configs" / "profiles"
    profiles_dir.mkdir(parents=True)

    monkeypatch.chdir(tmp_path)
    assert get_profiles_dir() == Path("configs/profiles")


def test_logger_initialization(tmp_path):
    log_dir = tmp_path / "logs"
    config = {
        "logging": {"directory": str(log_dir)},
        "output": {"mock_plugin": {"enabled": True}},
    }

    with patch("importlib.import_module") as mock_import:
        mock_plugin_module = MagicMock()
        mock_plugin_class = MagicMock()
        mock_import.return_value = mock_plugin_module
        mock_plugin_module.Plugin = mock_plugin_class

        logger = CyanideLogger(config)

        assert logger.log_dir == log_dir.resolve()
        assert log_dir.exists()
        assert logger.server_log is not None
        assert logger.fs_log is not None


def test_logger_events(tmp_path):
    log_dir = tmp_path / "logs"
    config = {"logging": {"directory": str(log_dir)}}
    logger = CyanideLogger(config)

    logger.log_event("session1", "ssh.connect", {"src_ip": "1.2.3.4"})
    assert (log_dir / "cyanide-vfs.json").exists()

    logger.log_event("session1", "tty.input", {"data": "ls"})
    assert (log_dir / "cyanide-tty.json").exists()

    logger.log_event("session1", "stats", {"cpu": 10})
    assert (log_dir / "cyanide-stats.json").exists()

    logger.log_event("session1", "server.start", {"port": 22})
    assert (log_dir / "cyanide-server.json").exists()


def test_logger_geoip(tmp_path):
    logger = CyanideLogger({"logging": {"directory": str(tmp_path)}})

    entry = logger._prepare_log_entry("s1", "test", {"src_ip": "127.0.0.1"})
    assert entry["geoip"]["country"] == "Local Network"

    entry = logger._prepare_log_entry(
        "s2", "test", {"src_ip": "8.8.8.8", "geoip": {"country": "US"}}
    )
    assert entry["geoip"]["country"] == "US"


def test_logger_session_mirroring(tmp_path):
    log_dir = tmp_path / "logs"
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    jsonl = session_dir / "session.jsonl"
    ml_json = session_dir / "ml.json"

    logger = CyanideLogger({"logging": {"directory": str(log_dir)}})
    logger.register_session_log("s1", jsonl, ml_json)

    logger.log_event("s1", "command.input", {"cmd": "whoami"})
    assert jsonl.exists()
    assert "whoami" in jsonl.read_text()

    logger.log_event("s1", "ml_thought", {"thought": "attacking"})
    assert ml_json.exists()
    assert "attacking" in ml_json.read_text()

    logger.unregister_session_log("s1")
    logger.log_event("s1", "command.input", {"cmd": "after_unreg"})
    assert "after_unreg" not in jsonl.read_text()


def test_logger_sanitization(tmp_path):
    logger = CyanideLogger({"logging": {"directory": str(tmp_path)}})
    data = {"path": Path("/tmp/test"), "list": [Path("a"), Path("b")]}
    sanitized = logger._sanitize_log_entry(data)
    assert sanitized["path"] == "/tmp/test"
    assert sanitized["list"] == ["a", "b"]


def test_logger_serialization_error(tmp_path, capsys):
    logger = CyanideLogger({"logging": {"directory": str(tmp_path)}})

    class Unserializable:
        pass

    logger.log_event("s1", "test", {"obj": Unserializable()})
    captured = capsys.readouterr()
    assert "ERROR: CyanideLogger failed to serialize event" in captured.err
