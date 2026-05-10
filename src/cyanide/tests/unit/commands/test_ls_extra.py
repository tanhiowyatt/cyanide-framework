import posixpath
from unittest.mock import MagicMock

import pytest

from cyanide.vfs.commands.ls import LsCommand
from cyanide.vfs.nodes import Directory, File


@pytest.fixture
def mock_ls_emulator():
    emulator = MagicMock()
    emulator.cwd = "/"
    emulator.resolve_path = MagicMock(
        side_effect=lambda p: posixpath.abspath(posixpath.join("/", p))
    )

    # Create a small VFS tree
    root = Directory("/", perm="drwxr-xr-x", owner="root", group="root")
    subdir = Directory("subdir", parent=root, perm="drwxr-xr-x", owner="root", group="root")
    file1 = File(
        "file1.txt", content=b"content", parent=root, perm="-rw-r--r--", owner="root", group="root"
    )
    file2 = File(
        "file2.txt",
        content=b"content",
        parent=subdir,
        perm="-rw-r--r--",
        owner="root",
        group="root",
    )

    root._children_getter = lambda: {"subdir": subdir, "file1.txt": file1}
    subdir._children_getter = lambda: {"file2.txt": file2}

    fs = MagicMock()
    fs.get_node = MagicMock(
        side_effect=lambda p: {
            "/": root,
            "/subdir": subdir,
            "/file1.txt": file1,
            "/subdir/file2.txt": file2,
        }.get(p)
    )

    emulator.fs = fs
    return emulator


@pytest.mark.asyncio
async def test_ls_recursive(mock_ls_emulator):
    cmd = LsCommand(mock_ls_emulator)
    out, err, code = await cmd.execute(["-R", "/"])
    assert code == 0
    assert "/:" in out
    assert "subdir" in out
    assert "file1.txt" in out
    assert "/subdir:" in out
    assert "file2.txt" in out


@pytest.mark.asyncio
async def test_ls_not_found(mock_ls_emulator):
    cmd = LsCommand(mock_ls_emulator)
    out, err, code = await cmd.execute(["/nonexistent"])
    assert code == 2
    assert "cannot access '/nonexistent'" in err


@pytest.mark.asyncio
async def test_ls_file_direct(mock_ls_emulator):
    cmd = LsCommand(mock_ls_emulator)
    out, err, code = await cmd.execute(["/file1.txt"])
    assert code == 0
    assert "file1.txt" in out


@pytest.mark.asyncio
async def test_ls_long_format(mock_ls_emulator):
    cmd = LsCommand(mock_ls_emulator)
    out, err, code = await cmd.execute(["-l", "/file1.txt"])
    assert code == 0
    assert "-rw-r--r--" in out
    assert "root" in out
    assert "file1.txt" in out


@pytest.mark.asyncio
async def test_ls_show_all(mock_ls_emulator):
    cmd = LsCommand(mock_ls_emulator)
    # Add a hidden file
    root = mock_ls_emulator.fs.get_node("/")
    hidden = File(
        ".hidden", content=b"h", parent=root, perm="-rw-r--r--", owner="root", group="root"
    )
    old_getter = root._children_getter
    root._children_getter = lambda: {**old_getter(), ".hidden": hidden}

    out, err, code = await cmd.execute(["-a", "/"])
    assert code == 0
    assert "." in out
    assert ".." in out
    assert ".hidden" in out


@pytest.mark.asyncio
async def test_ls_recursive_long(mock_ls_emulator):
    cmd = LsCommand(mock_ls_emulator)
    out, err, code = await cmd.execute(["-alR", "/"])
    assert code == 0
    assert "/subdir:" in out
    assert "file2.txt" in out


@pytest.mark.asyncio
async def test_ls_recursive_no_all_with_hidden(mock_ls_emulator):
    cmd = LsCommand(mock_ls_emulator)
    # Add a hidden subdir
    root = mock_ls_emulator.fs.get_node("/")
    hidden_dir = Directory(".hiddendir", parent=root, perm="drwxr-xr-x", owner="root", group="root")
    hidden_dir._children_getter = lambda: {}
    old_getter = root._children_getter
    root._children_getter = lambda: {**old_getter(), ".hiddendir": hidden_dir}

    out, err, code = await cmd.execute(["-R", "/"])
    assert code == 0
    assert ".hiddendir" not in out


@pytest.mark.asyncio
async def test_ls_long_format_date_fallback(mock_ls_emulator, monkeypatch):
    from cyanide.vfs.commands.ls import LsCommand

    cmd = LsCommand(mock_ls_emulator)

    root = mock_ls_emulator.fs.get_node("/")
    file_bad_date = File(
        "bad_date.txt", content=b"x", parent=root, perm="-rw-r--r--", owner="root", group="root"
    )
    file_bad_date.mtime = "invalid-date-string"

    old_getter = root._children_getter
    root._children_getter = lambda: {**old_getter(), "bad_date.txt": file_bad_date}

    # Update get_node mock to include the new file
    old_side_effect = mock_ls_emulator.fs.get_node.side_effect

    def new_side_effect(p):
        if p == "/bad_date.txt":
            return file_bad_date
        return old_side_effect(p)

    mock_ls_emulator.fs.get_node.side_effect = new_side_effect

    # Mock dateutil.parser to raise ValueError
    import sys
    from unittest.mock import MagicMock

    mock_parser = MagicMock()
    mock_parser.parse.side_effect = ValueError("bad date")

    # This is a bit tricky to monkeypatch a module that might not be imported yet
    # or is imported inside the method.
    # We can patch 'dateutil.parser' if it's already in sys.modules
    # or we can mock the import itself.

    with monkeypatch.context() as m:
        m.setitem(sys.modules, "dateutil", MagicMock())
        m.setitem(sys.modules, "dateutil.parser", mock_parser)

        out, err, code = await cmd.execute(["-l", "/bad_date.txt"])
        assert code == 0
        assert "bad_date.txt" in out
        # Should have current date/time which we won't strictly check but it didn't crash
