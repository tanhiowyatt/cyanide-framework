import pytest
from core.fake_filesystem import FakeFilesystem
from core.shell_emulator import ShellEmulator

@pytest.fixture
def shell():
    fs = FakeFilesystem()
    return ShellEmulator(fs, "root")

@pytest.mark.asyncio
async def test_chaining_and(shell):
    # echo "1" && echo "2"
    stdout, stderr, rc = await shell.execute('echo "1" && echo "2"')
    assert "1" in stdout
    assert "2" in stdout
    assert rc == 0

@pytest.mark.asyncio
async def test_chaining_or_fail(shell):
    # badcmd || echo "recovered"
    stdout, stderr, rc = await shell.execute('badcmd || echo "recovered"')
    assert "command not found" in stderr
    assert "recovered" in stdout
    # The last command determines RC? 
    # Logic: badcmd fails (127), || triggers next. echo succeeds (0).
    assert rc == 0

@pytest.mark.asyncio
async def test_chaining_or_skip(shell):
    # echo "ok" || echo "skip"
    stdout, stderr, rc = await shell.execute('echo "ok" || echo "skip"')
    assert "ok" in stdout
    assert "skip" not in stdout
    assert rc == 0

@pytest.mark.asyncio
async def test_redirection_write(shell):
    await shell.execute('echo "content" > /test.txt')
    assert shell.fs.get_content('/test.txt') == "content\n"

@pytest.mark.asyncio
async def test_redirection_append(shell):
    await shell.execute('echo "line1" > /test.txt')
    await shell.execute('echo "line2" >> /test.txt')
    content = shell.fs.get_content('/test.txt')
    assert "line1" in content
    assert "line2" in content

@pytest.mark.asyncio
async def test_pipe_simple(shell):
    # cat file | cat
    await shell.execute('echo "piped" > /source.txt')
    stdout, _, _ = await shell.execute('cat /source.txt | cat')
    assert "piped" in stdout

@pytest.mark.asyncio
async def test_pipe_chain(shell):
    # echo "data" | cat | cat
    stdout, _, _ = await shell.execute('echo "data" | cat | cat')
    assert "data" in stdout

@pytest.mark.asyncio
async def test_complex_scenario(shell):
    # echo "hack" > /tmp/malware && cat /tmp/malware | cat >> /var/log/hacked
    await shell.execute('echo "hack" > /tmp/malware && cat /tmp/malware | cat >> /var/log/hacked')
    assert shell.fs.get_content('/var/log/hacked') == "hack\n"

