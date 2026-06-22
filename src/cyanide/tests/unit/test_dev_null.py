import pytest

from cyanide.core.emulator import ShellEmulator
from cyanide.vfs.engine import FakeFilesystem


@pytest.fixture
def fs():
    return FakeFilesystem()


@pytest.fixture
def emulator(fs):
    return ShellEmulator(fs, username="root")


def test_dev_null_existence(fs):
    assert fs.exists("/dev/null")
    assert fs.is_file("/dev/null")
    assert not fs.is_dir("/dev/null")


def test_dev_null_read_empty(fs):
    assert fs.get_content("/dev/null") == ""


def test_dev_null_write_discard(fs):
    # Try writing to /dev/null
    node = fs.mkfile("/dev/null", content="some data")
    assert node is not None
    assert node.name == "null"
    # Content must still be empty
    assert fs.get_content("/dev/null") == ""
    # Make sure it didn't pollute memory_overlay
    assert "/dev/null" not in fs.memory_overlay


def test_dev_null_listing(fs):
    items = fs.list_dir("/dev")
    assert "null" in items


def test_dev_null_mkdir_fails(fs):
    assert not fs.mkdir_p("/dev/null")
    assert not fs.mkdir_p("/dev/null/subdir")


def test_dev_null_remove_and_recreate(fs):
    assert fs.remove("/dev/null") is True
    assert not fs.exists("/dev/null")
    assert "null" not in fs.list_dir("/dev")

    # Recreate it
    node = fs.mkfile("/dev/null", content="")
    assert node is not None
    assert fs.exists("/dev/null")
    assert "null" in fs.list_dir("/dev")


@pytest.mark.asyncio
async def test_shell_redirection_dev_null(emulator, fs):
    # Execute an echo command redirected to /dev/null
    stdout, stderr, rc = await emulator.execute("echo 'hello world' > /dev/null")
    assert rc == 0
    assert stdout == ""
    assert stderr == ""
    # Verify /dev/null is still empty
    assert fs.get_content("/dev/null") == ""
    assert "/dev/null" not in fs.memory_overlay


@pytest.mark.asyncio
async def test_hostname_command(emulator, fs):
    # Default hostname is debian-server
    assert fs.context.hostname == "debian-server"

    stdout, stderr, rc = await emulator.execute("hostname")
    assert rc == 0
    assert stdout == "debian-server\n"
    assert stderr == ""

    # FQDN
    stdout, stderr, rc = await emulator.execute("hostname -f")
    assert rc == 0
    assert stdout == "debian-server.localdomain\n"

    # Domain
    stdout, stderr, rc = await emulator.execute("hostname -d")
    assert rc == 0
    assert stdout == "localdomain\n"

    # IP
    stdout, stderr, rc = await emulator.execute("hostname -i")
    assert rc == 0
    assert stdout == "192.168.1.15\n"

    # Non-root cannot set hostname
    emulator.username = "guest"
    stdout, stderr, rc = await emulator.execute("hostname newhost")
    assert rc == 1
    assert "you must be root to change the host name" in stderr

    # Root can set hostname
    emulator.username = "root"
    stdout, stderr, rc = await emulator.execute("hostname newhost")
    assert rc == 0
    assert fs.context.hostname == "newhost"

    # Get updated hostname
    stdout, stderr, rc = await emulator.execute("hostname")
    assert rc == 0
    assert stdout == "newhost\n"
