import pytest

from cyanide.core.emulator import ShellEmulator
from cyanide.vfs.engine import FakeFilesystem


@pytest.fixture
def emulator():
    fs = FakeFilesystem()
    return ShellEmulator(fs, username="root")


@pytest.mark.asyncio
async def test_python_interactive(emulator):
    out, err, rc = await emulator.execute("python")
    assert rc == 0
    assert "Python 3.10" in out
    assert emulator.pending_input_prompt == ">>> "
    assert emulator.pending_input_callback is not None

    out, err, rc = await emulator.execute("help")
    assert "interactive help" in out
    assert emulator.pending_input_prompt == ">>> "

    # In imitation mode, unknown names return empty output (silent acknowledgement)
    out, err, rc = await emulator.execute("invalidname")
    assert out == ""
    assert emulator.pending_input_prompt == ">>> "

    out, err, rc = await emulator.execute("exit()")
    assert emulator.pending_input_callback is None


@pytest.mark.asyncio
async def test_editor_functionality(emulator):
    emulator.fs.mkdir_p("/root", owner="root")

    out, err, rc = await emulator.execute("vi /root/test_script.sh")
    assert rc == 0
    assert emulator.pending_input_callback is not None

    await emulator.execute("i")
    await emulator.execute("echo 'Hello World'")
    await emulator.execute("\r")
    await emulator.execute("exit 0")
    await emulator.execute("\r")
    await emulator.execute("\x1b")

    await emulator.execute(":")
    out, err, rc = await emulator.execute("w")
    await emulator.execute("q")
    await emulator.execute("\r")

    assert emulator.pending_input_callback is None

    content = emulator.fs.get_content("/root/test_script.sh")
    assert content == "echo 'Hello World'\nexit 0\n"


@pytest.mark.asyncio
async def test_crontab_functionality(emulator):
    out, err, rc = await emulator.execute("crontab -e")
    assert rc == 0
    assert emulator.pending_input_callback is not None

    await emulator.execute("i")
    await emulator.execute("* * * * * /tmp/owned.sh")
    await emulator.execute("\r")
    await emulator.execute("\x1b")
    await emulator.execute(":")
    out, err, rc = await emulator.execute("w")
    await emulator.execute("q")
    await emulator.execute("\r")
    assert emulator.pending_input_callback is None

    out, err, rc = await emulator.execute("crontab -l")
    assert rc == 0
    assert "* * * * * /tmp/owned.sh" in out

    out, err, rc = await emulator.execute("crontab -r")
    assert rc == 0

    out, err, rc = await emulator.execute("crontab -l")
    assert "no crontab for" in out
