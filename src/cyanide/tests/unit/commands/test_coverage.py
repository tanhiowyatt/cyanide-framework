from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cyanide.vfs.commands.apt import AptCommand
from cyanide.vfs.commands.cat import CatCommand
from cyanide.vfs.commands.chmod import ChmodCommand
from cyanide.vfs.commands.curl import CurlCommand
from cyanide.vfs.commands.dd import DdCommand
from cyanide.vfs.commands.editor import NanoCommand, VimCommand
from cyanide.vfs.commands.finger import FingerCommand
from cyanide.vfs.commands.grep import GrepCommand
from cyanide.vfs.commands.hostname import HostnameCommand
from cyanide.vfs.commands.ip import IpCommand
from cyanide.vfs.commands.ls import LsCommand
from cyanide.vfs.commands.mv import MvCommand
from cyanide.vfs.commands.pkexec import PkexecCommand
from cyanide.vfs.commands.ps import PsCommand
from cyanide.vfs.commands.rmdir import RmdirCommand
from cyanide.vfs.commands.su import SuCommand
from cyanide.vfs.commands.systemctl import SystemctlCommand
from cyanide.vfs.commands.uptime import UptimeCommand
from cyanide.vfs.commands.wget import WgetCommand
from cyanide.vfs.commands.yum import YumCommand
from cyanide.vfs.engine import FakeFilesystem
from cyanide.vfs.nodes import Directory
from cyanide.vfs.scp import ScpHandler


class MockResponse:
    def __init__(self, status, json_data=None, bytes_data=None):
        self.status = status
        self._json = json_data
        self._bytes = bytes_data

    async def json(self):
        return self._json

    async def read(self):
        return self._bytes

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class MockSession:
    def __init__(self, resp):
        self.resp = resp
        self.closed = False

    def get(self, *args, **kwargs):
        return self.resp

    async def close(self):
        self.closed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


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
    return FakeFilesystem()


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
    emu.execute = AsyncMock(return_value=("", "", 0))
    return emu


# ==================== WGET COMMAND ====================


@pytest.mark.asyncio
async def test_wget_command_boost():
    emu = MagicMock()
    emu.fs = MagicMock()
    emu.fs.resolve_path = MagicMock(return_value="/root/file.txt")
    emu.username = "root"
    emu.quarantine_callback = None

    wget = WgetCommand(emu)
    wget.validate_url = MagicMock(return_value=(True, "", "1.2.3.4"))

    mock_resp = MockResponse(200, bytes_data=b"content")
    with patch("aiohttp.ClientSession", return_value=MockSession(mock_resp)):
        await wget.execute(["http://example.com/file.txt"])
        emu.fs.mkfile.assert_called()
        _, kwargs = emu.fs.mkfile.call_args
        assert kwargs["content"] == "content"


@pytest.mark.asyncio
async def test_wget_extra_coverage():
    mock_emu = MagicMock()
    cmd = WgetCommand(mock_emu)

    out, err, code = await cmd.execute([])
    assert "missing URL" in err

    out, err, code = await cmd.execute(["not_a_url"])
    assert code != 0


# ==================== CURL COMMAND ====================


@pytest.mark.asyncio
async def test_curl_edge_cases(emulator):
    cmd = CurlCommand(emulator)

    mock_resp = AsyncMock()
    mock_resp.status = 404
    mock_resp.version = None
    mock_resp.headers = {}

    mock_resp.__aenter__.return_value = mock_resp
    with patch("aiohttp.ClientSession.get", return_value=mock_resp):
        stdout, stderr, rc = await cmd.execute(["-s", "http://example.com"])
        assert rc == 22
        assert stderr == ""

    import aiohttp

    with patch("aiohttp.ClientSession.get", side_effect=aiohttp.ClientError("Resolve failed")):
        stdout, stderr, rc = await cmd.execute(["http://example.com"])
        assert rc == 6
        assert "Could not resolve host" in stderr

    with patch("aiohttp.ClientSession.get", side_effect=RuntimeError("Generic error")):
        stdout, stderr, rc = await cmd.execute(["http://example.com"])
        assert rc == 1
        assert "Protocol not supported" in stderr


# ==================== EDITORS (VIM / NANO) ====================


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


def test_editor_vim_G_and_x(emulator):
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


# ==================== SCP HANDLER ====================


@pytest.mark.asyncio
async def test_scp_error_paths(emulator):
    handler = ScpHandler(MagicMock(), process=MagicMock())
    handler.process.stdin.read.side_effect = Exception("Read error")
    data = await handler._read(1)
    assert data == b""

    handler.process.channel.write.side_effect = Exception("Write error")
    handler._write(b"data")

    handler.process.stdin.read.side_effect = [b"a", b""]
    await handler._read_file_data(10)

    handler.fs = None
    handler._save_to_vfs("test", b"content")


@pytest.mark.asyncio
async def test_scp_metadata_edge_cases(emulator):
    handler = ScpHandler(MagicMock())
    is_sink, is_source, path = handler._parse_scp_metadata("scp file")
    assert is_sink is False
    assert is_source is False
    with patch("shlex.split", side_effect=Exception("shlex error")):
        is_sink, is_source, path = handler._parse_scp_metadata("scp -t /tmp")
        assert is_sink is False


# ==================== PKEXEC & SU & DOAS ====================


@pytest.mark.asyncio
async def test_pkexec_coverage():
    mock_emu = MagicMock()
    mock_emu.username = "user"
    mock_emu.execute = AsyncMock(return_value=("pk_out", "", 0))
    cmd = PkexecCommand(mock_emu)

    out, err, code = await cmd.execute([])
    assert "must specify" in err

    mock_emu.username = "root"
    with patch("cyanide.core.emulator.ShellEmulator") as mock_shell_cls:
        mock_shell_inst = mock_shell_cls.return_value
        mock_shell_inst.execute = AsyncMock(return_value=("pk_out", "", 0))
        out, err, code = await cmd.execute(["id"])
        assert out == "pk_out"


@pytest.mark.asyncio
async def test_pkexec_non_root(emulator):
    cmd = PkexecCommand(emulator)
    emulator.username = "user"

    with patch("cyanide.core.emulator.ShellEmulator") as mock_shell_cls:
        mock_shell_inst = mock_shell_cls.return_value
        mock_shell_inst.execute = AsyncMock(return_value=("ls_out", "", 0))
        stdout, stderr, rc = await cmd.execute(["ls"])
        assert stdout == "ls_out"
        assert emulator.pending_input_callback is None


@pytest.mark.asyncio
async def test_su_coverage():
    cmd = SuCommand(MagicMock())
    mock_emu = MagicMock()
    mock_emu.username = "user"
    mock_emu.execute = AsyncMock(return_value=("su_out", "", 0))
    cmd = SuCommand(mock_emu)

    with patch("cyanide.core.emulator.ShellEmulator") as mock_shell_cls:
        mock_shell_inst = mock_shell_cls.return_value
        mock_shell_inst.execute = AsyncMock(return_value=("su_out", "", 0))
        out, err, code = await cmd.execute(["-c", "id"])
        assert out == "su_out"

    mock_emu.pending_input_prompt = ""
    await cmd.execute(["root"])
    assert "Password:" in mock_emu.pending_input_prompt


# ==================== MISCELLANEOUS COMMANDS ====================


@pytest.mark.asyncio
async def test_all_the_things_coverage_boost(emulator):
    grep = GrepCommand(emulator)
    await grep.execute(["pattern"], input_data="pattern")

    ls = LsCommand(emulator)
    root = Directory("root", None)
    child = Directory("child", root)
    root.children["child"] = child
    with patch.object(emulator.fs, "get_node", return_value=root):
        await ls.execute(["-aR"])

    chmod = ChmodCommand(emulator)
    await chmod.execute(["755", "file"])

    await PsCommand(emulator).execute(["aux"])
    await IpCommand(emulator).execute(["link"])
    await MvCommand(emulator).execute(["a", "b"])
    await RmdirCommand(emulator).execute(["dir"])
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


@pytest.mark.asyncio
async def test_cat_wildcard(fs, emulator):
    cmd = CatCommand(emulator)
    fs.mkdir_p("/root")
    fs.mkfile("/root/flag1.txt", content="content1")
    fs.mkfile("/root/flag2.txt", content="content2")
    fs.mkfile("/root/other.txt", content="other")

    stdout, stderr, rc = await cmd.execute(["*flag*"])
    assert "content1" in stdout
    assert "content2" in stdout
    assert "other" not in stdout
    assert rc == 0


@pytest.mark.asyncio
async def test_systemctl_status(emulator):
    cmd = SystemctlCommand(emulator)
    stdout, stderr, rc = await cmd.execute(["status", "nginx"])
    assert "● nginx.service" in stdout
    assert "Active: active (running)" in stdout
    assert rc == 0

    stdout, stderr, rc = await cmd.execute([])
    assert "ssh.service" in stdout
    assert rc == 0


@pytest.mark.asyncio
async def test_finger_user(emulator):
    cmd = FingerCommand(emulator)
    stdout, stderr, rc = await cmd.execute(["root"])
    assert "Login: root" in stdout
    assert "/home/root" in stdout
    assert rc == 0

    stdout, stderr, rc = await cmd.execute([])
    assert "Login" in stdout
    assert "Name" in stdout
    assert rc == 0


@pytest.mark.asyncio
async def test_dd_command_coverage(emulator):
    cmd = DdCommand(emulator)

    # 1. Invalid numbers
    for arg in ["bs=abc", "count=abc", "skip=abc", "seek=abc"]:
        stdout, stderr, rc = await cmd.execute([arg])
        assert rc == 1
        assert "invalid number" in stderr

    # 2. Test bs multipliers
    # bs=2k
    stdout, stderr, rc = await cmd.execute(["bs=2k", "count=1"], input_data="a" * 3000)
    assert rc == 0
    # bs=1m
    stdout, stderr, rc = await cmd.execute(
        ["bs=1m", "count=1"], input_data="a" * (1024 * 1024 + 10)
    )
    assert rc == 0
    # bs=1g
    stdout, stderr, rc = await cmd.execute(["bs=1g", "count=0"], input_data="a")
    assert rc == 0

    # 3. Test if_path not found
    stdout, stderr, rc = await cmd.execute(["if=/nonexistent"])
    assert rc == 1
    assert "No such file or directory" in stderr

    # 4. Test if_path is a directory
    emulator.fs.mkdir_p("/root/dir")
    stdout, stderr, rc = await cmd.execute(["if=/root/dir"])
    assert rc == 1
    assert "Is a directory" in stderr

    # 5. Test if_path is /dev/urandom or /dev/random
    stdout, stderr, rc = await cmd.execute(["if=/dev/urandom", "bs=10", "count=5"])
    assert rc == 0
    assert "50 bytes copied" in stderr

    # 6. Test if_path is /dev/sda
    emulator.fs._generate_sda_data = MagicMock(return_value=b"sda_data")
    stdout, stderr, rc = await cmd.execute(["if=/dev/sda", "bs=4", "count=2"])
    assert rc == 0
    assert stdout == "sda_data"

    # Test read_len > max_read limit for /dev/sda
    emulator.fs._generate_sda_data.return_value = b"large_sda"
    stdout, stderr, rc = await cmd.execute(["if=/dev/sda", "bs=11m", "count=1"])
    assert rc == 0
    emulator.fs._generate_sda_data.assert_called_with(0, 10 * 1024 * 1024)

    # 7. Test regular file input (binary vs string content)
    # Binary content
    emulator.fs.mkfile("/root/binfile", content=b"\x01\x02\x03\x04")
    stdout, stderr, rc = await cmd.execute(["if=/root/binfile", "bs=1"])
    assert rc == 0
    assert stdout == "\x01\x02\x03\x04"

    # String content
    emulator.fs.mkfile("/root/strfile", content="hello")
    stdout, stderr, rc = await cmd.execute(["if=/root/strfile", "bs=1"])
    assert rc == 0
    assert stdout == "hello"

    # raw_content is None (or empty)
    with patch.object(emulator.fs, "get_content", return_value=None):
        stdout, stderr, rc = await cmd.execute(["if=/root/strfile"])
        assert rc == 0
        assert stdout == ""

    # 8. Test skip logic
    stdout, stderr, rc = await cmd.execute(["if=/root/strfile", "bs=1", "skip=2"])
    assert rc == 0
    assert stdout == "llo"

    stdout, stderr, rc = await cmd.execute(["if=/root/strfile", "bs=1", "skip=10"])
    assert rc == 0
    assert stdout == ""

    # 9. Test seek and write to output file (of_path)
    # Output file doesn't exist
    stdout, stderr, rc = await cmd.execute(
        ["if=/root/strfile", "of=/root/outfile1", "bs=1", "seek=3"]
    )
    assert rc == 0
    assert emulator.fs.get_content("/root/outfile1") == b"\0\0\0hello"

    # Output file exists, string content
    emulator.fs.mkfile("/root/outfile2", content="existing")
    stdout, stderr, rc = await cmd.execute(
        ["if=/root/strfile", "of=/root/outfile2", "bs=1", "seek=2"]
    )
    assert rc == 0
    assert emulator.fs.get_content("/root/outfile2") == b"exhello"

    # Output file exists, binary content, seek > len(existing)
    emulator.fs.mkfile("/root/outfile3", content=b"\x01\x02")
    stdout, stderr, rc = await cmd.execute(
        ["if=/root/strfile", "of=/root/outfile3", "bs=1", "seek=4"]
    )
    assert rc == 0
    assert emulator.fs.get_content("/root/outfile3") == b"\x01\x02\0\0hello"


@pytest.mark.asyncio
async def test_hostname_command_coverage(emulator):
    from cyanide.vfs.context import Context

    # 1. No hostname set, no file -> fallback to localhost
    emulator.fs.context = None
    with patch.object(emulator.fs, "exists", return_value=False):
        cmd = HostnameCommand(emulator)
        stdout, stderr, rc = await cmd.execute([])
        assert rc == 0
        assert stdout == "localhost\n"

    # 2. Hostname from /etc/hostname (as bytes)
    def mock_exists(path):
        return path == "/etc/hostname"

    with patch.object(emulator.fs, "exists", side_effect=mock_exists):
        with patch.object(emulator.fs, "get_content", return_value=b"test-bytes-host\n"):
            cmd = HostnameCommand(emulator)
            stdout, stderr, rc = await cmd.execute([])
            assert rc == 0
            assert stdout == "test-bytes-host\n"

    # 3. Hostname template rendering
    ctx = Context(os_name="linux", kernel_version="5.4", hostname="", arch="x86_64")
    emulator.fs.context = ctx
    with patch.object(emulator.fs, "exists", side_effect=mock_exists):
        with patch.object(emulator.fs, "get_content", return_value="tmpl-{{ os_name }}\n"):
            cmd = HostnameCommand(emulator)
            stdout, stderr, rc = await cmd.execute([])
            assert rc == 0
            assert stdout == "tmpl-linux\n"

    # 4. Hostname template rendering exception fallback
    with patch.object(emulator.fs, "exists", side_effect=mock_exists):
        with patch.object(emulator.fs, "get_content", return_value="tmpl-{{ invalid syntax }}"):
            cmd = HostnameCommand(emulator)
            stdout, stderr, rc = await cmd.execute([])
            assert rc == 0
            assert stdout == "localhost\n"

    # 5. Invalid options
    cmd = HostnameCommand(emulator)
    stdout, stderr, rc = await cmd.execute(["-x"])
    assert rc == 1
    assert "invalid option" in stderr

    # 6. Set hostname (not root)
    emulator.username = "user"
    stdout, stderr, rc = await cmd.execute(["newhost"])
    assert rc == 1
    assert "must be root" in stderr

    # 7. Set hostname (root)
    emulator.username = "root"
    emulator.fs.context = ctx
    stdout, stderr, rc = await cmd.execute(["newhost"])
    assert rc == 0
    assert ctx.hostname == "newhost"

    # 8. Show options: -f, -s, -d, -i, -a
    ctx.hostname = "my.sub.domain"
    # -i/I (IP)
    with patch.object(cmd, "get_ip_addr", return_value="192.168.1.10"):
        stdout, stderr, rc = await cmd.execute(["-i"])
        assert rc == 0
        assert stdout == "192.168.1.10\n"
    # -f
    stdout, stderr, rc = await cmd.execute(["-f"])
    assert rc == 0
    assert stdout == "my.sub.domain.localdomain\n"
    # -d
    stdout, stderr, rc = await cmd.execute(["-d"])
    assert rc == 0
    assert stdout == "localdomain\n"
    # -s
    stdout, stderr, rc = await cmd.execute(["-s"])
    assert rc == 0
    assert stdout == "my\n"
    # -a
    stdout, stderr, rc = await cmd.execute(["-a"])
    assert rc == 0
    assert stdout == "\n"


@pytest.mark.asyncio
async def test_yum_command_coverage(emulator):
    from cyanide.vfs.commands.yum import YumCommand

    # 1. Package manager not supported
    cmd = YumCommand(emulator)
    with patch.object(cmd, "is_pkg_mgr_supported", return_value=False):
        stdout, stderr, rc = await cmd.execute(["update"])
        assert rc == 127
        assert "command not found" in stderr

    # 2. Yum supported, but no arguments
    with patch.object(cmd, "is_pkg_mgr_supported", return_value=True):
        stdout, stderr, rc = await cmd.execute([])
        assert rc == 1
        assert "You need to give some command" in stdout

    # 3. Invalid subcommand
    with patch.object(cmd, "is_pkg_mgr_supported", return_value=True):
        stdout, stderr, rc = await cmd.execute(["invalid_subcommand"])
        assert rc == 1
        assert "No such command: invalid_subcommand" in stdout

    # 4. Search subcommand with empty args
    with patch.object(cmd, "is_pkg_mgr_supported", return_value=True):
        stdout, stderr, rc = await cmd.execute(["search"])
        assert rc == 1
        assert "Need to pass a list of pkgs to search" in stdout

    # 5. Search subcommand with args
    with patch.object(cmd, "is_pkg_mgr_supported", return_value=True):
        stdout, stderr, rc = await cmd.execute(["search", "vim"])
        assert rc == 0
        assert "Matched package for vim" in stdout

    # 6. Install/remove/erase without packages
    with patch.object(cmd, "is_pkg_mgr_supported", return_value=True):
        stdout, stderr, rc = await cmd.execute(["install"])
        assert rc == 1
        assert "Need to pass a list of pkgs to install" in stdout

    # 7. Install/remove/erase with only flags (e.g. -y)
    with patch.object(cmd, "is_pkg_mgr_supported", return_value=True):
        stdout, stderr, rc = await cmd.execute(["install", "-y"])
        assert rc == 0
        assert "No packages provided" in stdout

    # 8. Install/remove with stats tracking
    mock_stats = MagicMock()
    emulator.fs.stats = mock_stats
    with patch.object(cmd, "is_pkg_mgr_supported", return_value=True):
        stdout, stderr, rc = await cmd.execute(["install", "nginx"])
        assert rc == 0
        assert "nginx" in stdout
        mock_stats.on_file_op.assert_called_with("download", "yum://nginx")

    # 9. Remove / Erase with packages
    with patch.object(cmd, "is_pkg_mgr_supported", return_value=True):
        stdout, stderr, rc = await cmd.execute(["remove", "nginx"])
        assert rc == 0
        assert "Erasing" in stdout


# ==================== EXTRA COMMANDS BOOSTER TESTS ====================


@pytest.mark.asyncio
async def test_cd_command_extra_booster(emulator):
    from cyanide.vfs.commands.cd import CdCommand

    cmd = CdCommand(emulator)

    # 1. cd with no args, HOME set
    emulator.env = {"HOME": "/root"}
    with patch.object(emulator.fs, "is_dir", return_value=True):
        stdout, stderr, rc = await cmd.execute([])
        assert rc == 0
        assert emulator.cwd == "/root"

    # 2. cd with no args, HOME not set (defaults to "/")
    emulator.env = {}
    with patch.object(emulator.fs, "is_dir", return_value=True):
        stdout, stderr, rc = await cmd.execute([])
        assert rc == 0
        assert emulator.cwd == "/"

    # 3. cd to a path that exists but is not a directory
    def mock_is_dir(path):
        return False

    def mock_exists(path):
        return path == "/root/file"

    with (
        patch.object(emulator.fs, "is_dir", side_effect=mock_is_dir),
        patch.object(emulator.fs, "exists", side_effect=mock_exists),
    ):
        stdout, stderr, rc = await cmd.execute(["/root/file"])
        assert rc == 1
        assert "Not a directory" in stderr


@pytest.mark.asyncio
async def test_ps_command_extra_booster(emulator):
    from cyanide.vfs.commands.ps import PsCommand

    # 1. fs has processes attribute
    emulator.fs.processes = [{"pid": 123, "tty": "pts/1", "time": "00:01:00", "cmd": "custom_proc"}]
    cmd = PsCommand(emulator)
    stdout, stderr, rc = await cmd.execute([])
    assert "custom_proc" in stdout

    # 2. fs doesn't have processes but has profile["processes"]
    mock_fs = MagicMock()
    del mock_fs.processes
    mock_fs.profile = {
        "processes": [{"pid": 456, "tty": "pts/2", "time": "00:02:00", "cmd": "profile_proc"}]
    }
    emulator.fs = mock_fs
    cmd = PsCommand(emulator)
    stdout, stderr, rc = await cmd.execute(["aux"])
    assert "profile_proc" in stdout

    # 3. Neither fs.processes nor profile exists (falls back to else block)
    mock_fs2 = MagicMock()
    del mock_fs2.processes
    del mock_fs2.profile
    emulator.fs = mock_fs2
    cmd = PsCommand(emulator)
    stdout, stderr, rc = await cmd.execute([])
    assert "/sbin/init" in stdout


@pytest.mark.asyncio
async def test_crontab_command_extra_booster(emulator):
    from cyanide.vfs.commands.crontab import CrontabCommand

    # 1. crontab -r when cron file does not exist
    cmd = CrontabCommand(emulator)
    with patch.object(emulator.fs, "exists", return_value=False):
        stdout, stderr, rc = await cmd.execute(["-r"])
        assert rc == 0

    # 2. crontab with usage error (no filename provided for install)
    stdout, stderr, rc = await cmd.execute([])
    assert rc == 1
    assert "file name must be specified" in stdout

    # 3. crontab install from nonexistent file
    with patch.object(emulator.fs, "exists", return_value=False):
        stdout, stderr, rc = await cmd.execute(["somefile"])
        assert rc == 1
        assert "No such file or directory" in stderr

    # 4. crontab install from directory
    def mock_is_dir(path):
        return True

    def mock_exists(path):
        return True

    with (
        patch.object(emulator.fs, "exists", side_effect=mock_exists),
        patch.object(emulator.fs, "is_dir", side_effect=mock_is_dir),
    ):
        stdout, stderr, rc = await cmd.execute(["somedir"])
        assert rc == 1
        assert "Is a directory" in stderr

    # 5. crontab install from valid file
    def mock_is_dir_file(path):
        return False

    def mock_get_content(path):
        return "* * * * * valid_cmd"

    with (
        patch.object(emulator.fs, "exists", return_value=True),
        patch.object(emulator.fs, "is_dir", return_value=False),
        patch.object(emulator.fs, "get_content", return_value="* * * * * valid_cmd"),
        patch.object(emulator.fs, "mkfile") as mock_mkfile,
    ):
        stdout, stderr, rc = await cmd.execute(["valid_file"])
        assert rc == 0
        mock_mkfile.assert_called_once()

    # 6. schedule cron job: parts < 6
    await cmd._schedule_cron_job("* * * * short")

    # 7. schedule cron job: ML flagged as malicious
    mock_analytics = MagicMock()
    mock_analytics.is_malicious.return_value = True
    emulator.analytics = mock_analytics
    cmd._log_event = MagicMock()
    await cmd._schedule_cron_job("* * * * * evil_command")
    cmd._log_event.assert_called_with(
        "cron_simulation_blocked", {"command": "evil_command", "reason": "ML flagged as malicious"}
    )

    # 8. schedule cron job: execution exception
    emulator.analytics.is_malicious.return_value = False
    emulator.execute = AsyncMock(side_effect=Exception("execution failed"))
    with patch("asyncio.sleep"):  # bypass wait
        await cmd._schedule_cron_job("* * * * * failing_command")
        emulator.execute.assert_called_once_with("failing_command")

    # 9. _handle_edit trigger_simulation coverage
    with patch("cyanide.vfs.commands.crontab.VimCommand") as mock_vim_class:
        mock_vim = mock_vim_class.return_value
        mock_vim.execute = AsyncMock(return_value=("", "", 0))

        # We want trigger_simulation to execute
        def mock_exists_cron(path):
            return "crontabs" in path

        with (
            patch.object(emulator.fs, "exists", side_effect=mock_exists_cron),
            patch.object(
                emulator.fs, "get_content", return_value="* * * * * echo 1\n# comment\n\n"
            ),
        ):
            # Execute crontab -e
            await cmd.execute(["-e"])
            # Call on_exit callback
            assert mock_vim.on_exit is not None
            mock_vim.on_exit()

            # 10. Call on_exit when file does not exist (covers 54->exit branch)
            with patch.object(emulator.fs, "exists", return_value=False):
                mock_vim.on_exit()


@pytest.mark.asyncio
async def test_chmod_command_extra_booster(emulator):
    from cyanide.vfs.commands.chmod import ChmodCommand

    cmd = ChmodCommand(emulator)

    # 1. chmod missing operand
    stdout, stderr, rc = await cmd.execute([])
    assert rc == 1
    assert "missing operand" in stderr

    # 2. octal mode value error (e.g. 999)
    # mock exists to bypass not found check
    with patch.object(emulator.fs, "get_node") as mock_get_node:
        mock_node = MagicMock()
        mock_node.perm = "drwxr-xr-x"
        mock_get_node.return_value = mock_node

        # This will raise ValueError inside _apply_octal_mode
        stdout, stderr, rc = await cmd.execute(["999", "file"])
        assert rc == 0

    # 3. relative mode invalid match
    with patch.object(emulator.fs, "get_node") as mock_get_node:
        mock_node = MagicMock()
        mock_node.perm = "drwxr-xr-x"
        mock_get_node.return_value = mock_node

        stdout, stderr, rc = await cmd.execute(["zzz", "file"])
        assert rc == 0

    # 4. relative mode who=empty or "a", operator="-" or "="
    with patch.object(emulator.fs, "get_node") as mock_get_node:
        mock_node = MagicMock()
        mock_node.perm = "drwxr-xr-x"
        mock_get_node.return_value = mock_node

        # empty who -> all (ugo), operator='-', what='x'
        stdout, stderr, rc = await cmd.execute(["-x", "file"])
        assert rc == 0

        # operator='='
        stdout, stderr, rc = await cmd.execute(["a=r", "file"])
        assert rc == 0


@pytest.mark.asyncio
async def test_rmdir_command_extra_booster(emulator):
    from cyanide.vfs.commands.rmdir import RmdirCommand

    cmd = RmdirCommand(emulator)

    # 1. rmdir Not a directory
    with (
        patch.object(emulator.fs, "get_node") as mock_get_node,
        patch.object(emulator.fs, "is_dir", return_value=False),
    ):
        mock_get_node.return_value = MagicMock()
        stdout, stderr, rc = await cmd.execute(["file"])
        assert rc == 1
        assert "Not a directory" in stderr

    # 2. rmdir operation not permitted (remove returns False)
    with (
        patch.object(emulator.fs, "get_node") as mock_get_node,
        patch.object(emulator.fs, "is_dir", return_value=True),
        patch.object(emulator.fs, "list_dir", return_value=[]),
        patch.object(emulator.fs, "remove", return_value=False),
    ):
        mock_get_node.return_value = MagicMock()
        stdout, stderr, rc = await cmd.execute(["dir"])
        assert rc == 1
        assert "Operation not permitted" in stderr
