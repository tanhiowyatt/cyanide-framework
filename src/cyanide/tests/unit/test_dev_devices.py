from unittest.mock import MagicMock

import pytest

from cyanide.core.emulator import ShellEmulator
from cyanide.vfs.engine import FakeFilesystem
from cyanide.vfs.sftp import CyanideSFTPHandler


@pytest.fixture
def fs():
    return FakeFilesystem()


@pytest.fixture
def emulator(fs):
    return ShellEmulator(fs, username="root")


def test_dev_devices_existence(fs):
    for path in ("/dev/random", "/dev/urandom", "/dev/sda"):
        assert fs.exists(path)
        assert fs.is_file(path)
        assert not fs.is_dir(path)
        node = fs.get_node(path)
        assert node is not None
        if path == "/dev/sda":
            assert node.perm == "brw-rw----"
            assert node.group == "disk"
            assert node.size == 40 * 1024 * 1024 * 1024
        else:
            assert node.perm == "crw-rw-rw-"
            assert node.group == "root"
            assert node.size == 0


def test_dev_devices_listing(fs):
    items = fs.list_dir("/dev")
    assert "null" in items
    assert "random" in items
    assert "urandom" in items
    assert "sda" in items


def test_dev_devices_read(fs):
    content_random1 = fs.get_content("/dev/random")
    content_random2 = fs.get_content("/dev/random")
    assert isinstance(content_random1, bytes)
    assert len(content_random1) == 65536
    # Due to randomness, they must differ
    assert content_random1 != content_random2

    content_urandom1 = fs.get_content("/dev/urandom")
    assert isinstance(content_urandom1, bytes)
    assert len(content_urandom1) == 65536

    content_sda = fs.get_content("/dev/sda")
    assert isinstance(content_sda, bytes)
    assert len(content_sda) == 65536
    # Byte 510 and 511 of /dev/sda must contain the MBR signature 55 AA
    assert content_sda[510] == 0x55
    assert content_sda[511] == 0xAA


def test_dev_devices_write_discard(fs):
    for path in ("/dev/random", "/dev/urandom", "/dev/sda"):
        node = fs.mkfile(path, content="some random bytes data")
        assert node is not None
        # /dev/sda should still return MBR at beginning, random/urandom return different randoms
        content = fs.get_content(path)
        if path == "/dev/sda":
            assert content[510] == 0x55
            assert content[511] == 0xAA
        # Path should not pollute memory overlay
        assert path not in fs.memory_overlay


def test_dev_devices_mkdir_fails(fs):
    for path in ("/dev/random", "/dev/urandom", "/dev/sda"):
        assert not fs.mkdir_p(path)
        assert not fs.mkdir_p(f"{path}/subdir")


@pytest.mark.asyncio
async def test_dd_command(emulator, fs):
    # Test dd with /dev/urandom
    stdout, stderr, rc = await emulator.execute("dd if=/dev/urandom of=/tmp/noise bs=10 count=5")
    assert rc == 0
    assert "5+0 records in" in stderr
    assert "5+0 records out" in stderr
    assert fs.exists("/tmp/noise")
    noise_content = fs.get_content("/tmp/noise")
    assert isinstance(noise_content, bytes)
    assert len(noise_content) == 50

    # Test dd with /dev/sda (seeking first 512 bytes MBR)
    stdout, stderr, rc = await emulator.execute("dd if=/dev/sda of=/tmp/mbr bs=512 count=1")
    assert rc == 0
    assert "1+0 records in" in stderr
    assert fs.exists("/tmp/mbr")
    mbr_content = fs.get_content("/tmp/mbr")
    assert len(mbr_content) == 512
    assert mbr_content[510] == 0x55
    assert mbr_content[511] == 0xAA

    # Test dd skip option on /dev/sda
    stdout, stderr, rc = await emulator.execute("dd if=/dev/sda of=/tmp/sec1 bs=512 count=1 skip=1")
    assert rc == 0
    sec1_content = fs.get_content("/tmp/sec1")
    assert len(sec1_content) == 512
    expected_sec1 = fs._generate_sda_data(512, 512)
    assert sec1_content == expected_sec1


@pytest.mark.asyncio
async def test_sftp_handling():
    # Mock SSH channel and factory
    mock_chan = MagicMock()
    mock_conn = MagicMock()
    mock_factory = MagicMock()
    mock_factory.fs = FakeFilesystem()
    mock_factory.framework.logger = MagicMock()
    mock_factory.conn_id = "test_conn"
    mock_factory.src_ip = "127.0.0.1"
    mock_conn.get_extra_info.return_value = "root"
    mock_conn.cyanide_factory = mock_factory
    mock_chan.get_connection.return_value = mock_conn

    # Instantiate SFTP Handler
    handler = CyanideSFTPHandler(mock_chan)

    # 1. Test SFTP read on /dev/urandom
    handle_urandom = await handler.open("/dev/urandom", 1, None)
    data1 = await handler.read(handle_urandom, 0, 100)
    data2 = await handler.read(handle_urandom, 100, 100)
    assert len(data1) == 100
    assert len(data2) == 100
    assert data1 != data2
    await handler.close(handle_urandom)

    # 2. Test SFTP read on /dev/sda
    handle_sda = await handler.open("/dev/sda", 1, None)
    # Read first 512 bytes (MBR)
    mbr_data = await handler.read(handle_sda, 0, 512)
    assert len(mbr_data) == 512
    assert mbr_data[510] == 0x55
    assert mbr_data[511] == 0xAA

    # Read sector 1
    sec1_data = await handler.read(handle_sda, 512, 512)
    assert len(sec1_data) == 512
    assert sec1_data != mbr_data
    await handler.close(handle_sda)


@pytest.mark.asyncio
async def test_df_command(emulator):
    stdout, stderr, rc = await emulator.execute("df -h")
    assert rc == 0
    assert "/dev/sda1" in stdout
    assert "40G" in stdout
