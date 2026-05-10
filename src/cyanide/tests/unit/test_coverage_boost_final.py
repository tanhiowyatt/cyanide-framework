from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cyanide.core.geoip import GeoIP
from cyanide.core.stats import StatsManager
from cyanide.core.vm_pool import SimplePool
from cyanide.network.ssh_proxy import ProxyClientChannel, ProxyServerSession
from cyanide.services.ioc_reporter import IOCReporter
from cyanide.vfs.commands.wget import WgetCommand
from cyanide.vfs.engine import FakeFilesystem


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


@pytest.mark.asyncio
async def test_geoip_boost():
    geoip = GeoIP()

    # Local network
    res = await geoip.lookup("127.0.0.1")
    assert res["country"] == "Local Network"

    # Mock aiohttp
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

    # Patch asyncio.get_event_loop().getnameinfo
    with patch("asyncio.get_event_loop") as mock_get_loop:
        mock_loop = MagicMock()
        mock_loop.getnameinfo = AsyncMock(return_value=("dns.google", 0))
        mock_get_loop.return_value = mock_loop

        ptr = await geoip.lookup_ptr("8.8.8.8")
        assert ptr == "dns.google"

        mock_loop.getnameinfo.side_effect = Exception()
        ptr = await geoip.lookup_ptr("8.8.8.8")
        assert ptr is None


@pytest.mark.asyncio
async def test_stats_manager_prometheus_boost():
    stats = StatsManager()
    stats.on_connect("ssh", "1.2.3.4")
    stats.on_auth("root", "admin", False)

    output = stats.to_prometheus()
    assert "cyanide_active_sessions 1" in output
    assert "cyanide_auth_failures_total 1" in output


@pytest.mark.asyncio
async def test_wget_command_boost():
    emu = MagicMock()
    emu.fs = MagicMock()
    emu.fs.resolve_path = MagicMock(return_value="/root/file.txt")
    emu.username = "root"
    emu.quarantine_callback = None

    wget = WgetCommand(emu)
    wget.validate_url = MagicMock(return_value=(True, "", "1.2.3.4"))

    # Test file output
    mock_resp = MockResponse(200, bytes_data=b"content")
    with patch("aiohttp.ClientSession", return_value=MockSession(mock_resp)):
        await wget.execute(["http://example.com/file.txt"])
        emu.fs.mkfile.assert_called()
        _, kwargs = emu.fs.mkfile.call_args
        assert kwargs["content"] == "content"


@pytest.mark.asyncio
async def test_ioc_reporter_boost(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    config = {"logging": {"directory": str(log_dir)}}
    logger = MagicMock()

    reporter = IOCReporter(config, logger)
    # add_ioc(self, ioc_type, value, description, source_session, severity="medium")
    reporter.add_ioc("ip", "1.2.3.4", "Malicious IP", "session1")

    # Export reports
    reporter.generate_reports(quiet=True)
    assert reporter.report_dir.exists()


@pytest.mark.asyncio
async def test_vm_pool_boost():
    config = {"pool": {"enabled": True, "targets": "127.0.0.1:22,192.168.1.100:22"}}
    pool = SimplePool(config)
    assert len(pool.targets) == 2
    assert ("127.0.0.1", 22) in pool.targets


@pytest.mark.asyncio
async def test_ssh_proxy_boost():
    pool = MagicMock()
    pool.reserve_target = AsyncMock(return_value=("1.2.3.4", 22))

    # Mock transport/channel
    chan = MagicMock()
    chan.get_extra_info.return_value = ("1.2.3.4", 12345)

    fs = MagicMock()

    with patch("cyanide.network.ssh_proxy.logger") as mock_logger:
        # ProxyServerSession(pool, target_host, target_port, session_id, src_ip, fs)
        session = ProxyServerSession(pool, "1.2.3.4", 22, "session1", "1.2.3.4", fs)
        session.connection_made(chan)

        # Test data transfer
        session.data_received(b"test data", 0)

        # Test ProxyClientChannel
        client_chan = ProxyClientChannel("session1", "1.2.3.4", chan)
        client_chan.data_received(b"response", 0)

        # Verify logging
        assert mock_logger.info.called


@pytest.mark.asyncio
async def test_vfs_engine_render_boost():
    fs = FakeFilesystem(os_profile="debian")

    # Test _render with bytes
    res = fs._render(b"test")
    assert res == b"test"

    # Test _render with string
    res = fs._render("test")
    assert res == "test"

    # Test _render with jinja
    fs.context = MagicMock()
    fs.context.to_dict.return_value = {"var": "val"}
    res = fs._render("{{ var }}")
    assert res == "val"
