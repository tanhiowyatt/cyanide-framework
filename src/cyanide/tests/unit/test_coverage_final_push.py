from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cyanide.core.paths import get_default_config_path, get_profiles_dir
from cyanide.core.server import SSHSession
from cyanide.network.ssh_proxy import ProxyServerSession
from cyanide.vfs.commands.editor import NanoCommand, VimCommand
from cyanide.vfs.engine import FakeFilesystem
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
    root = Directory("root", None)
    test_file = File("test_file", root)
    root.children["test_file"] = test_file
    mock_fs.get_node = MagicMock(return_value=test_file)
    mock_fs.resolve_node = MagicMock(return_value=test_file)
    mock_fs.os_profile = "debian"
    mock_fs.exists = MagicMock(return_value=True)
    mock_fs.get_content = MagicMock(return_value="test content")
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
    emu.session_id = "test_sess"
    return emu


@pytest.mark.asyncio
async def test_editor_vim_modes_coverage(emulator):
    vim = VimCommand(emulator)
    vim._reset_state("test.txt")

    # NORMAL mode: G with empty lines
    vim.mode = "NORMAL"
    vim.lines = []
    vim._handle_input("G")

    # NORMAL mode: o (open line below)
    vim.lines = ["line1"]
    vim.cursor_y = 0
    vim._handle_input("o")
    assert vim.mode == "INSERT"

    # NORMAL mode: dd (delete line)
    vim.mode = "NORMAL"
    vim.lines = ["a", "b"]
    vim._handle_input("dd")

    # COLON mode: backspace
    vim.mode = "COLON"
    vim.colon_buffer = "w"
    vim._handle_input("\x7f")
    assert vim.colon_buffer == ""
    vim._handle_input("\x7f")  # Back to NORMAL
    assert vim.mode == "NORMAL"

    # INSERT mode: backspace
    vim.mode = "INSERT"
    vim.lines = ["a", ""]
    vim.cursor_y = 1
    vim.cursor_x = 0
    vim._handle_input("\x7f")  # Should pop the empty line
    assert len(vim.lines) == 1

    # INSERT mode: enter
    vim.lines = ["a"]
    vim._handle_input("\n")
    assert len(vim.lines) == 2


@pytest.mark.asyncio
async def test_editor_nano_modes_coverage(emulator):
    nano = NanoCommand(emulator)
    nano._reset_state("test.txt")

    # Nano: handle_input is sync
    with patch.object(nano, "_render", return_value=""):
        nano._handle_input("\x0f")  # Ctrl+O
        assert "Wrote" in nano.message

        nano.dirty = True
        nano._handle_input("\x18")  # Ctrl+X
        assert "Save modified buffer?" in nano.message
        assert nano.emulator.pending_input_callback == nano._handle_exit_confirm

        # Test help
        nano._handle_input("\x07")
        assert "Help" in nano.message


def test_paths_coverage():
    with patch("pathlib.Path.exists", return_value=False):
        path = get_default_config_path()
        assert "app.yaml" in str(path)

    with patch("pathlib.Path.is_dir", return_value=False):
        path = get_profiles_dir()
        assert "profiles" in str(path)


@pytest.mark.asyncio
async def test_server_session_bot_detection_coverage(emulator):
    framework = MagicMock()
    framework.stats = MagicMock()
    session = SSHSession(framework, emulator.fs, "1.2.3.4", 12345, "s1")

    session.keystrokes = [1.0, 1.001, 1.002, 1.003]
    is_bot = session._calculate_is_bot(False, 10)
    assert is_bot is True

    session.keystrokes = [1.0, 1.2, 1.5, 1.9]
    is_bot = session._calculate_is_bot(False, 10)

    session._close_session = AsyncMock()
    res = session._handle_system_commands("exit")
    assert res is True


@pytest.mark.asyncio
async def test_ssh_session_in_editor_coverage(emulator):
    framework = MagicMock()
    framework.stats = MagicMock()
    session = SSHSession(framework, emulator.fs, "1.2.3.4", 12345, "s1")
    session.shell = emulator
    session.shell.pending_input_callback = AsyncMock(return_value=("", "", 0))
    session.shell.execute = AsyncMock(return_value=("resp", "", 0))
    session._write = MagicMock()
    session.process = None  # Ensure process is None to avoid drain() issues

    # Test data processing when in editor
    # Call _process_input directly since data_received is sync and creates a task
    await session._process_input("\x1b[Atest")
    assert session._write.called


@pytest.mark.asyncio
async def test_vfs_engine_render_coverage(emulator):
    engine = FakeFilesystem(os_profile="debian")
    # Target _render
    assert engine._render("") == ""
    assert engine._render(b"bytes") == b"bytes"
    assert engine._render("normal text") == "normal text"

    # Test with jinja
    engine.context = MagicMock()
    engine.context.to_dict = MagicMock(return_value={"var": "val"})
    assert engine._render("{{ var }}") == "val"

    # Test error path in render
    with patch.object(engine.jinja_env, "from_string", side_effect=Exception("fail")):
        assert engine._render("{{ fail }}") == "{{ fail }}"


@pytest.mark.asyncio
async def test_ssh_proxy_error_paths():
    pool = MagicMock()
    pool.reserve_target = AsyncMock(return_value=("host", 22))

    proxy = ProxyServerSession(pool, "target", 22, "s1", "5.6.7.8", MagicMock())

    chan = MagicMock()
    proxy.connection_made(chan)

    with patch("asyncssh.connect", side_effect=Exception("fail")):
        await proxy._connect_backend()
