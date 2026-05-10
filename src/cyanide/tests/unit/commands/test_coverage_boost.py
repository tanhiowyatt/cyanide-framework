from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cyanide.vfs.commands.cat import CatCommand
from cyanide.vfs.commands.finger import FingerCommand
from cyanide.vfs.commands.pkexec import PkexecCommand
from cyanide.vfs.commands.systemctl import SystemctlCommand
from cyanide.vfs.engine import FakeFilesystem


@pytest.fixture
def fs():
    return FakeFilesystem()


@pytest.fixture
def emulator(fs):
    emu = MagicMock()
    emu.fs = fs
    emu.username = "root"
    emu.cwd = "/root"
    emu.resolve_path = lambda p: f"/root/{p}" if not p.startswith("/") else p
    emu.pending_input_callback = None
    emu.execute = AsyncMock(return_value=("", "", 0))
    return emu


@pytest.mark.asyncio
async def test_cat_wildcard(fs, emulator):
    cmd = CatCommand(emulator)
    fs.mkdir_p("/root")
    fs.mkfile("/root/flag1.txt", content="content1")
    fs.mkfile("/root/flag2.txt", content="content2")
    fs.mkfile("/root/other.txt", content="other")

    # Test cat *flag*
    stdout, stderr, rc = await cmd.execute(["*flag*"])
    assert "content1" in stdout
    assert "content2" in stdout
    assert "other" not in stdout
    assert rc == 0


@pytest.mark.asyncio
async def test_systemctl_status(emulator):
    cmd = SystemctlCommand(emulator)
    # Test systemctl status
    stdout, stderr, rc = await cmd.execute(["status", "nginx"])
    assert "● nginx.service" in stdout
    assert "Active: active (running)" in stdout
    assert rc == 0

    # Test systemctl list
    stdout, stderr, rc = await cmd.execute([])
    assert "ssh.service" in stdout
    assert rc == 0


@pytest.mark.asyncio
async def test_pkexec_non_root(emulator):
    cmd = PkexecCommand(emulator)
    emulator.username = "user"

    # Test pkexec ls
    # pkexec now creates a new ShellEmulator. Mock it to verify execution.
    with patch("cyanide.core.emulator.ShellEmulator") as mock_shell_cls:
        mock_shell_inst = mock_shell_cls.return_value
        mock_shell_inst.execute = AsyncMock(return_value=("ls_out", "", 0))
        stdout, stderr, rc = await cmd.execute(["ls"])
        assert stdout == "ls_out"
        assert emulator.pending_input_callback is None


@pytest.mark.asyncio
async def test_finger_user(emulator):
    cmd = FingerCommand(emulator)
    # Test finger root
    stdout, stderr, rc = await cmd.execute(["root"])
    assert "Login: root" in stdout
    assert "/home/root" in stdout
    assert rc == 0

    # Test finger (list)
    stdout, stderr, rc = await cmd.execute([])
    assert "Login" in stdout
    assert "Name" in stdout
    assert rc == 0
