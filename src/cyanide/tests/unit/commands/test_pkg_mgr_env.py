import pytest

from cyanide.core.config import load_config
from cyanide.core.emulator import ShellEmulator
from cyanide.vfs.engine import FakeFilesystem


@pytest.mark.asyncio
async def test_package_manager_override(monkeypatch):
    # Test that we can override package managers via environment
    monkeypatch.setenv("CYANIDE_FRAMEWORK_PACKAGE_MANAGER", "yum,rpm")

    # Load config with env override
    config = load_config()
    assert "yum" in config["package_managers"]
    assert "rpm" in config["package_managers"]
    assert "apt" not in config["package_managers"]

    fs = FakeFilesystem(os_profile="debian")  # Profile is debian, which would normally have apt
    emulator = ShellEmulator(fs, username="root", config=config)

    # apt should now be NOT FOUND even on debian profile
    out, err, rc = await emulator.execute("apt update")
    assert rc == 127
    assert "command not found" in err

    # yum should be FOUND because of override
    out, err, rc = await emulator.execute("yum update")
    assert rc == 0
    assert "No packages marked for update" in out
