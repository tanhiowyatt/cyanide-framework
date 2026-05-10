from unittest.mock import MagicMock

import pytest

from cyanide.vfs.commands.mv import MvCommand
from cyanide.vfs.commands.touch import TouchCommand
from cyanide.vfs.commands.uptime import UptimeCommand


@pytest.fixture
def mock_vfs_emulator():
    emulator = MagicMock()
    emulator.fs = MagicMock()
    emulator.username = "root"
    emulator.resolve_path = MagicMock(side_effect=lambda p: p)
    return emulator


@pytest.mark.asyncio
async def test_mv_extra(mock_vfs_emulator):
    cmd = MvCommand(mock_vfs_emulator)

    # Missing operands
    out, err, code = await cmd.execute(["file1"])
    assert code == 1
    assert "missing file operand" in err

    # Non-existent source
    mock_vfs_emulator.fs.exists.return_value = False
    out, err, code = await cmd.execute(["src", "dest"])
    assert code == 1
    assert "cannot stat" in err

    # Move failure
    mock_vfs_emulator.fs.exists.return_value = True
    mock_vfs_emulator.fs.move.return_value = False
    out, err, code = await cmd.execute(["src", "dest"])
    assert code == 1
    assert "cannot move" in err


@pytest.mark.asyncio
async def test_touch_extra(mock_vfs_emulator):
    cmd = TouchCommand(mock_vfs_emulator)

    # No args
    out, err, code = await cmd.execute([])
    assert code == 1
    assert "missing file operand" in err

    # touch flag (ignored)
    mock_vfs_emulator.fs.mkfile.return_value = "/file"
    out, err, code = await cmd.execute(["-a", "file"])
    assert code == 0

    # mkfile failure
    mock_vfs_emulator.fs.mkfile.return_value = None
    out, err, code = await cmd.execute(["dir/file"])
    assert code == 1
    assert "cannot touch" in err


@pytest.mark.asyncio
async def test_uptime_extra(mock_vfs_emulator):
    cmd = UptimeCommand(mock_vfs_emulator)

    # /proc/uptime missing
    mock_vfs_emulator.fs.get_content.return_value = None
    out, err, code = await cmd.execute([])
    assert code == 0
    assert "up 1:00" in out  # Default 3600s

    # /proc/uptime malformed
    mock_vfs_emulator.fs.get_content.return_value = "invalid"
    out, err, code = await cmd.execute([])
    assert code == 0
    assert "up 1:00" in out
