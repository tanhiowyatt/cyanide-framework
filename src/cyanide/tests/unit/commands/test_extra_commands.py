from unittest.mock import patch

import pytest

from cyanide.core.emulator import ShellEmulator
from cyanide.vfs.commands.chmod import ChmodCommand
from cyanide.vfs.commands.rmdir import RmdirCommand
from cyanide.vfs.commands.su import SuCommand
from cyanide.vfs.commands.sudo import SudoCommand


@pytest.fixture
def shell(mock_fs):
    return ShellEmulator(mock_fs, username="root")


@pytest.mark.asyncio
async def test_chmod(shell, mock_fs):
    cmd = ChmodCommand(shell)
    mock_fs.mkfile("/root/script.sh", perm="-rw-r--r--")

    stdout, stderr, rc = await cmd.execute([])
    assert rc == 1
    assert "missing operand" in stderr

    # Test octal mode
    mock_fs.mkfile("/root/test1.sh", perm="-rw-r--r--")
    await cmd.execute(["777", "test1.sh"])
    assert mock_fs.get_node("/root/test1.sh").perm == "-rwxrwxrwx"

    # Test relative mode (+x)
    mock_fs.mkfile("/root/test2.sh", perm="-rw-r--r--")
    await cmd.execute(["+x", "test2.sh"])
    perm = mock_fs.get_node("/root/test2.sh").perm
    assert perm[3] == "x"
    assert perm[6] == "x"
    assert perm[9] == "x"


@pytest.mark.asyncio
async def test_rmdir(shell, mock_fs):
    cmd = RmdirCommand(shell)

    # Successful removal of empty dir
    mock_fs.mkdir_p("/root/empty_dir")
    stdout, stderr, rc = await cmd.execute(["empty_dir"])
    assert rc == 0
    assert not mock_fs.exists("/root/empty_dir")

    # Failure on non-empty dir
    mock_fs.mkdir_p("/root/full_dir")
    mock_fs.mkfile("/root/full_dir/file.txt")
    stdout, stderr, rc = await cmd.execute(["full_dir"])
    assert rc == 1
    assert "Directory not empty" in stderr
    assert mock_fs.exists("/root/full_dir")


@pytest.mark.asyncio
async def test_su(shell, mock_fs):
    cmd = SuCommand(shell)
    mock_fs.mkdir_p("/home")

    stdout, stderr, rc = await cmd.execute(["-", "guest"])
    assert stdout == ""
    assert "Password: " in shell.pending_input_prompt
    stdout, stderr, rc = cmd._on_password("admin")
    assert rc == 0
    assert shell.username == "guest"
    assert mock_fs.exists("/home/guest")


@pytest.mark.asyncio
async def test_sudo(shell, mock_fs):
    cmd = SudoCommand(shell)

    # sudo -l (list privileges)
    stdout, stderr, rc = await cmd.execute(["-l"])
    assert rc == 0
    assert "may run the following commands" in stdout

    # sudo with no args
    stdout, stderr, rc = await cmd.execute([])
    assert rc == 1
    assert "usage: sudo" in stderr

    # sudo -i (interactive root shell)
    stdout, stderr, rc = await cmd.execute(["-i"])
    assert rc == 0
    assert shell.username == "root"
    assert shell.cwd == "/root"

    # sudo -u guest whoami
    shell.username = "root"
    # Note: sudo.py imports ShellEmulator inside _handle_command
    # To avoid recursion or dependency issues in tests, we can mock the inner execute
    with patch("cyanide.core.emulator.ShellEmulator.execute", return_value=("guest\n", "", 0)):
        stdout, stderr, rc = await cmd.execute(["-u", "guest", "whoami"])
        assert rc == 0
        assert stdout == "guest\n"


@pytest.mark.asyncio
async def test_sudo_invalid_args(shell, mock_fs):
    cmd = SudoCommand(shell)
    # sudo -u (missing user)
    stdout, stderr, rc = await cmd.execute(["-u"])
    assert rc == 1
    assert "option requires an argument" in stderr
