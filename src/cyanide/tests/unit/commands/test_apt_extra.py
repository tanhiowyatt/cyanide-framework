from unittest.mock import MagicMock

import pytest

from cyanide.vfs.commands.apt import AptCommand


@pytest.fixture
def mock_apt_emulator():
    emulator = MagicMock()
    emulator.config = {}
    emulator.fs = MagicMock()
    emulator.fs.os_profile = "debian"
    emulator.fs.stats = MagicMock()
    emulator.resolve_path = MagicMock(side_effect=lambda p: p)
    return emulator


@pytest.mark.asyncio
async def test_apt_basic(mock_apt_emulator):
    cmd = AptCommand(mock_apt_emulator)

    # No args
    out, err, code = await cmd.execute([])
    assert code == 0
    assert "Usage: apt" in out

    # Update
    out, err, code = await cmd.execute(["update"])
    assert code == 0
    assert "Reading package lists" in out

    # Upgrade
    out, err, code = await cmd.execute(["upgrade"])
    assert code == 0
    assert "Calculating upgrade" in out

    # Search
    out, err, code = await cmd.execute(["search", "python"])
    assert code == 0
    assert "python - matching package" in out

    # Search no pattern
    out, err, code = await cmd.execute(["search"])
    assert code == 100
    assert "at least one search pattern" in err


@pytest.mark.asyncio
async def test_apt_install_remove(mock_apt_emulator):
    cmd = AptCommand(mock_apt_emulator)

    # Install
    out, err, code = await cmd.execute(["install", "vim"])
    assert code == 0
    assert "NEW packages will be installed" in out
    assert "vim" in out
    mock_apt_emulator.fs.stats.on_file_op.assert_called_with("download", "apt://vim")

    # Remove
    out, err, code = await cmd.execute(["remove", "vim"])
    assert code == 0
    assert "Removing vim" in out


@pytest.mark.asyncio
async def test_apt_errors(mock_apt_emulator):
    cmd = AptCommand(mock_apt_emulator)

    # Invalid op
    out, err, code = await cmd.execute(["invalid"])
    assert code == 100
    assert "Invalid operation" in err

    # No packages for install
    out, err, code = await cmd.execute(["install"])
    assert code == 100
    assert "No packages found" in err


@pytest.mark.asyncio
async def test_dpkg_basic(mock_apt_emulator):
    from cyanide.vfs.commands.dpkg import DpkgCommand

    cmd = DpkgCommand(mock_apt_emulator)

    # No args
    out, err, code = await cmd.execute([])
    assert code == 2
    assert "need an action option" in err

    # List
    out, err, code = await cmd.execute(["-l"])
    assert code == 0
    assert "Name" in out
    assert "bash" in out

    # Install no targets
    out, err, code = await cmd.execute(["-i"])
    assert code == 2
    assert "--install needs at least one package" in err


@pytest.mark.asyncio
async def test_dpkg_install_success(mock_apt_emulator):
    from cyanide.vfs.commands.dpkg import DpkgCommand

    cmd = DpkgCommand(mock_apt_emulator)

    mock_apt_emulator.resolve_path.side_effect = lambda p: p
    mock_apt_emulator.fs.exists.return_value = True

    out, err, code = await cmd.execute(["-i", "vim.deb"])
    assert code == 0
    assert "Unpacking vim" in out
    mock_apt_emulator.fs.stats.on_file_op.assert_called_with("download", "dpkg://vim")


@pytest.mark.asyncio
async def test_dpkg_install_fail(mock_apt_emulator):
    from cyanide.vfs.commands.dpkg import DpkgCommand

    cmd = DpkgCommand(mock_apt_emulator)

    mock_apt_emulator.resolve_path.side_effect = lambda p: p
    mock_apt_emulator.fs.exists.return_value = False

    out, err, code = await cmd.execute(["-i", "nonexistent.deb"])
    assert code == 2
    assert "cannot access archive" in err
