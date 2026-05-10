import pytest

from cyanide.core.emulator import ShellEmulator
from cyanide.vfs.engine import FakeFilesystem


@pytest.fixture
def debian_emulator():
    fs = FakeFilesystem(os_profile="debian")
    return ShellEmulator(fs, username="root")


@pytest.fixture
def rhel_emulator():
    fs = FakeFilesystem(os_profile="rhel")
    return ShellEmulator(fs, username="root")


@pytest.mark.asyncio
async def test_apt_on_debian(debian_emulator):
    out, err, rc = await debian_emulator.execute("apt update")
    assert rc == 0
    assert "Reading package lists... Done" in out

    out, err, rc = await debian_emulator.execute("apt-get install curl")
    assert rc == 0
    assert "Unpacking curl" in out

    out, err, rc = await debian_emulator.execute("dpkg -i file.deb")
    assert rc == 2


@pytest.mark.asyncio
async def test_apt_on_rhel(rhel_emulator):
    out, err, rc = await rhel_emulator.execute("apt update")
    assert rc == 127
    assert "command not found" in err

    out, err, rc = await rhel_emulator.execute("dpkg -i file.deb")
    assert rc == 127
    assert "command not found" in err


@pytest.mark.asyncio
async def test_yum_on_rhel(rhel_emulator):
    out, err, rc = await rhel_emulator.execute("yum update")
    assert rc == 0
    assert "No packages marked for update" in out

    out, err, rc = await rhel_emulator.execute("dnf install curl")
    assert rc == 0
    assert "Complete!" in out

    out, err, rc = await rhel_emulator.execute("rpm -qa")
    assert rc == 0
    assert "coreutils" in out


@pytest.mark.asyncio
async def test_yum_on_debian(debian_emulator):
    out, err, rc = await debian_emulator.execute("yum update")
    assert rc == 127
    assert "command not found" in err

    out, err, rc = await debian_emulator.execute("rpm -qa")
    assert rc == 127
    assert "command not found" in err
