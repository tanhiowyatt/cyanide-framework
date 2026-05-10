from unittest.mock import MagicMock

import pytest

from cyanide.vfs.commands.awk import AwkCommand
from cyanide.vfs.commands.grep import GrepCommand


@pytest.fixture
def mock_text_emulator():
    emulator = MagicMock()
    emulator.fs = MagicMock()
    emulator.resolve_path = MagicMock(side_effect=lambda p: p)
    return emulator


@pytest.mark.asyncio
async def test_awk_unknown_args(mock_text_emulator):
    cmd = AwkCommand(mock_text_emulator)
    # Test unknown arguments to trigger logging
    out, err, code = await cmd.execute(["-F", ":", "--unknown", "{print $1}", "file.txt"])
    # It should still work but log the unknown arg
    assert code == 0


@pytest.mark.asyncio
async def test_awk_directory_error(mock_text_emulator):
    cmd = AwkCommand(mock_text_emulator)
    mock_text_emulator.fs.is_file.return_value = False
    mock_text_emulator.fs.is_dir.return_value = True
    out, err, code = await cmd.execute(["{print $1}", "dir"])
    assert code == 2
    assert "awk: dir: Is a directory" in err


@pytest.mark.asyncio
async def test_grep_extra(mock_text_emulator):
    cmd = GrepCommand(mock_text_emulator)

    # Grep with no pattern
    out, err, code = await cmd.execute([])
    assert code == 2
    assert "Usage: grep" in err

    # Grep with directory as input
    mock_text_emulator.fs.get_content.return_value = None  # Represents a directory or missing file
    mock_text_emulator.fs.exists.return_value = True

    out, err, code = await cmd.execute(["pattern", "dir"])
    assert code == 1  # No matches

    # Grep exception
    mock_text_emulator.fs.get_content.side_effect = Exception("read error")
    out, err, code = await cmd.execute(["pattern", "file"])
    assert code == 2
    assert "grep: read error" in err
