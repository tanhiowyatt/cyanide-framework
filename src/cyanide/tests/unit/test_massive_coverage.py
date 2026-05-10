from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cyanide.core.cleanup import CleanupManager
from cyanide.ml.classifier import KnowledgeBase
from cyanide.vfs.commands.apt import AptCommand
from cyanide.vfs.commands.cd import CdCommand
from cyanide.vfs.commands.chmod import ChmodCommand
from cyanide.vfs.commands.grep import GrepCommand
from cyanide.vfs.commands.ip import IpCommand
from cyanide.vfs.commands.ls import LsCommand
from cyanide.vfs.commands.mv import MvCommand
from cyanide.vfs.commands.ps import PsCommand
from cyanide.vfs.commands.rmdir import RmdirCommand
from cyanide.vfs.commands.uptime import UptimeCommand
from cyanide.vfs.commands.yum import YumCommand
from cyanide.vfs.nodes import Directory, File


@pytest.fixture
def mock_config():
    return {
        "cleanup": {
            "enabled": True,
            "interval": 1,
            "retention_days": 1,
            "paths": ["/tmp/test_cleanup"],
        },
        "package_managers": ["all"],
    }


@pytest.fixture
def fs():
    mock_fs = MagicMock()
    mock_fs.mkfile = MagicMock()
    mock_fs.is_dir = MagicMock(return_value=False)

    # Real-ish nodes to allow isinstance
    root = Directory("root", None)
    test_file = File("test_file", root)
    test_file.perm = "-rwxr-xr-x"
    test_file.owner = "root"
    test_file.group = "root"
    test_file.size = 100
    root.children["test_file"] = test_file

    mock_fs.get_node = MagicMock(return_value=test_file)
    mock_fs.resolve_node = MagicMock(return_value=test_file)
    mock_fs.os_profile = "debian"
    return mock_fs


@pytest.fixture
def emulator(fs, mock_config):
    emu = MagicMock()
    emu.fs = fs
    emu.username = "root"
    emu.cwd = "/root"
    emu.resolve_path = lambda p: f"/root/{p}" if not p.startswith("/") else p
    emu.pending_input_callback = None
    emu.logger = MagicMock()
    emu.width = 80
    emu.height = 24
    emu.config = mock_config
    return emu


def test_cleanup_manager_full(mock_config):
    manager = CleanupManager(mock_config)
    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.rglob", return_value=[Path("/tmp/old_file")]):
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_mtime = 0
                    mock_stat.return_value.st_size = 100
                    res = manager.cleanup_files(dry_run=True)
                    assert res["deleted"] == 1


def test_knowledge_base_more_edge_cases():
    kb = KnowledgeBase()
    kb.is_built = True
    match = {
        "similarity": 0.2,
        "technique_id": "T1000",
        "technique_name": "Test",
        "source": "unknown",
    }
    with patch.object(kb, "search", return_value=[match]):
        with patch.object(kb, "_fallback_classify", return_value={"classified": True}):
            res = kb.classify_command("ls")
            assert res["classified"] is True


@pytest.mark.asyncio
async def test_all_the_things_coverage_boost(emulator):
    # grep
    grep = GrepCommand(emulator)
    await grep.execute(["pattern"], input_data="pattern")

    # ls -aR
    ls = LsCommand(emulator)
    root = Directory("root", None)
    child = Directory("child", root)
    root.children["child"] = child
    with patch.object(emulator.fs, "get_node", return_value=root):
        await ls.execute(["-aR"])

    # chmod octal
    chmod = ChmodCommand(emulator)
    await chmod.execute(["755", "file"])

    # ps
    await PsCommand(emulator).execute(["aux"])

    # ip, mv, rmdir, cd, uptime
    await IpCommand(emulator).execute(["link"])
    await MvCommand(emulator).execute(["a", "b"])
    await RmdirCommand(emulator).execute(["dir"])
    await CdCommand(emulator).execute(["/tmp"])
    await UptimeCommand(emulator).execute([])


@pytest.mark.asyncio
async def test_pkg_mgr_more(emulator):
    apt = AptCommand(emulator)
    with patch.object(apt, "is_pkg_mgr_supported", return_value=True):
        await apt.execute(["update"])
        await apt.execute(["upgrade"])
        await apt.execute(["install", "vim"])

    yum = YumCommand(emulator)
    with patch.object(yum, "is_pkg_mgr_supported", return_value=True):
        await yum.execute(["update"])
        await yum.execute(["upgrade"])
        await yum.execute(["install", "vim"])


def test_editor_vim_G_and_x(emulator):
    from cyanide.vfs.commands.editor import VimCommand

    cmd = VimCommand(emulator)
    cmd._reset_state("test.txt")
    cmd.mode = "NORMAL"
    cmd.lines = ["a", "b", "c"]
    cmd.cursor_y = 0
    cmd._handle_input("G")
    assert cmd.cursor_y == 2
    cmd.lines = ["abc"]
    cmd.cursor_y = 0
    cmd.cursor_x = 1
    cmd._handle_input("x")
    assert cmd.lines == ["ac"]
