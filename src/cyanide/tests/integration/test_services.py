import asyncio

import asyncssh
import pytest
import pytest_asyncio
import telnetlib3

from cyanide.core.server import CyanideServer


@pytest.fixture
def server_config(tmp_path):
    return {
        "ssh": {"enabled": True, "port": 0, "backend_mode": "emulated"},
        "telnet": {"enabled": True, "port": 0, "backend_mode": "emulated"},
        "metrics": {"enabled": False},
        "logging": {"directory": str(tmp_path / "logs")},
        "quarantine_path": str(tmp_path / "quarantine"),
        "users": [{"user": "root", "pass": "root"}, {"user": "admin", "pass": "admin"}],
        "ml": {"enabled": False},
    }


@pytest_asyncio.fixture
async def framework_server(server_config):
    server = CyanideServer(server_config)
    task = asyncio.create_task(server.start())

    for _ in range(10):
        if server.ssh_server and server.telnet_server:
            break
        await asyncio.sleep(0.5)

    yield server

    await server.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_ssh_connection(framework_server):
    """Test that SSH server accepts connections."""
    port = framework_server.ssh_server.sockets[0].getsockname()[1]
    print(f"Testing SSH on port {port}")
    try:
        async with asyncssh.connect(
            "127.0.0.1",
            port=port,
            known_hosts=None,
            username="root",
            password="root",
            client_keys=None,
        ) as conn:
            assert conn.get_extra_info("peername") is not None
    except Exception as e:
        pytest.fail(f"SSH connection failed: {e}")


@pytest.mark.asyncio
async def test_ssh_auth_failure(framework_server):
    """Test invalid SSH credentials."""
    port = framework_server.ssh_server.sockets[0].getsockname()[1]
    with pytest.raises(asyncssh.PermissionDenied):
        async with asyncssh.connect(
            "127.0.0.1",
            port=port,
            known_hosts=None,
            username="root",
            password="wrongpassword",
            client_keys=None,
        ):
            pass


@pytest.mark.asyncio
async def test_telnet_connection(framework_server):
    """Test Telnet connection and auth."""
    port = framework_server.telnet_server.sockets[0].getsockname()[1]
    print(f"Testing Telnet on port {port}")
    reader, writer = await telnetlib3.open_connection("127.0.0.1", port)

    from typing import Any

    out: Any = await reader.readuntil(b"Login: ")
    assert b"Login: " in out
    writer.write("root\n")  # type: ignore

    out = await reader.readuntil(b"Password: ")
    assert b"Password" in out
    writer.write("root\n")  # type: ignore

    out = await reader.readuntil(b"# ")
    assert b"root@" in out and b"# " in out

    writer.close()
