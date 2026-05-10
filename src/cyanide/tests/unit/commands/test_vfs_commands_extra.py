from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cyanide.vfs.commands.cp import CpCommand
from cyanide.vfs.commands.doas import DoasCommand


@pytest.mark.asyncio
async def test_doas_usage():
    mock_emu = MagicMock()
    cmd = DoasCommand(mock_emu)
    result = await cmd.execute([])
    assert "usage: doas" in result[1]
    assert result[2] == 1


@pytest.mark.asyncio
async def test_doas_as_root():
    mock_emu = MagicMock()
    mock_emu.username = "root"
    # Mock _on_delegated_auth
    with patch.object(DoasCommand, "_on_delegated_auth", new_callable=AsyncMock) as mock_auth:
        mock_auth.return_value = ("out", "err", 0)
        cmd = DoasCommand(mock_emu)
        result = await cmd.execute(["ls"])
        assert result[0] == "out"


@pytest.mark.asyncio
async def test_cp_usage():
    mock_emu = MagicMock()
    cmd = CpCommand(mock_emu)
    result = await cmd.execute([])
    assert "missing file operand" in result[1]


@pytest.mark.asyncio
async def test_cp_no_stat():
    mock_emu = MagicMock()
    mock_emu.resolve_path.side_effect = lambda p: p
    mock_fs = MagicMock()
    mock_fs.exists.return_value = False
    mock_emu.fs = mock_fs

    cmd = CpCommand(mock_emu)
    result = await cmd.execute(["src", "dest"])
    assert "cannot stat" in result[1]


@pytest.mark.asyncio
async def test_doas_non_root():
    mock_emu = MagicMock()
    mock_emu.username = "user"
    mock_emu.pending_input_prompt = ""

    cmd = DoasCommand(mock_emu)
    with patch.object(DoasCommand, "_on_delegated_auth", new_callable=AsyncMock) as mock_auth:
        mock_auth.return_value = ("out", "", 0)
        result = await cmd.execute(["ls"])
        # Should NOT set up pending input anymore
        # In a MagicMock, accessing the property creates a Mock, so we check if it was called
        assert not mock_emu.pending_input_callback.called
        assert result == ("out", "", 0)


@pytest.mark.asyncio
async def test_doas_delegated_auth():
    mock_emu = MagicMock()
    mock_emu.fs = MagicMock()
    mock_emu.cwd = "/tmp"
    mock_emu.quarantine_callback = None

    cmd = DoasCommand(mock_emu)

    with patch("cyanide.core.emulator.ShellEmulator") as mock_shell_cls:
        mock_shell_inst = mock_shell_cls.return_value
        mock_shell_inst.execute = AsyncMock(return_value=("out", "", 0))

        result = await cmd._on_delegated_auth(["whoami"])

        assert result == ("out", "", 0)
        mock_shell_inst.execute.assert_called_with("whoami")
