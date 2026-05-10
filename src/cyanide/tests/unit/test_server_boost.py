from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cyanide.core.server import CyanideServer


@pytest.fixture
def server_config():
    return {
        "honeytokens": ["/etc/passwd"],
        "metrics": {"enabled": True, "token": "secret", "port": 9090},
        "ssh": {"enabled": True, "rekey_limit": "500M"},
        "virustotal": {"api_key": "fake"},
        "package_managers": ["apt"],
    }


@pytest.fixture
def server(server_config):
    with (
        patch("cyanide.core.server.CyanideLogger"),
        patch("cyanide.core.server.setup_telemetry"),
        patch("cyanide.core.server.SessionManager"),
        patch("cyanide.core.server.QuarantineService"),
        patch("cyanide.core.server.AnalyticsService"),
        patch("cyanide.core.server.IOCReporter"),
        patch("cyanide.core.server.TelnetHandler"),
        patch("cyanide.core.server.FakeFilesystem"),
    ):
        srv = CyanideServer(server_config)
        srv.stats = MagicMock()
        srv.stats.start_time = 0
        return srv


def test_fs_audit_hook_honeytoken(server):
    # Honeytoken hit
    server._fs_audit_hook("read", "/etc/passwd", session_id="s1", src_ip="1.2.3.4")
    server.stats.on_honeytoken.assert_called_with("/etc/passwd")

    # Normal audit
    server.stats.reset_mock()
    server._fs_audit_hook("read", "/tmp/normal", session_id="s1", src_ip="1.2.3.4")
    server.stats.on_honeytoken.assert_not_called()


def test_route_metrics_request(server):
    # Health
    server.ssh_server = MagicMock()
    res, mtype = server._route_metrics_request("/health")
    assert "healthy" in res
    assert mtype == "application/json"

    # Metrics
    server.stats.to_prometheus.return_value = "metrics_data"
    res, mtype = server._route_metrics_request("/metrics")
    assert "metrics_data" == res

    # Index
    res, mtype = server._route_metrics_request("/")
    assert "cyanide_control_plane" in res

    # Not found
    res, mtype = server._route_metrics_request("/no-such-path")
    assert "Not Found" in res


@pytest.mark.asyncio
async def test_handle_metrics_request_auth(server):
    reader = AsyncMock()
    writer = AsyncMock()
    writer.write = MagicMock()
    writer.close = MagicMock()

    # Unauthorized
    reader.readuntil.return_value = b"GET /metrics HTTP/1.1\r\n\r\n"
    await server._handle_metrics_request(reader, writer)
    assert any("401 Unauthorized" in str(args) for args in writer.write.call_args_list)

    # Authorized
    writer.reset_mock()
    reader.readuntil.return_value = b"GET /metrics HTTP/1.1\r\nAuthorization: Bearer secret\r\n\r\n"
    server.stats.to_prometheus.return_value = "data"
    await server._handle_metrics_request(reader, writer)
    assert any("200 OK" in str(args) for args in writer.write.call_args_list)


def test_parse_ssh_rekey():
    from cyanide.core.server import CyanideServer

    assert CyanideServer._parse_ssh_rekey("1G") == 1024**3
    assert CyanideServer._parse_ssh_rekey("512M") == 512 * 1024**2
    assert CyanideServer._parse_ssh_rekey("100K") == 100 * 1024
    assert CyanideServer._parse_ssh_rekey("1024") == 1024
    assert CyanideServer._parse_ssh_rekey("") == 1024**3


def test_save_quarantine_file(server):
    # Check if it creates task
    with patch("asyncio.create_task") as mock_task:
        server.save_quarantine_file("malware.exe", b"binary", "s1", "1.1.1.1", "ssh")
        mock_task.assert_called_once()
