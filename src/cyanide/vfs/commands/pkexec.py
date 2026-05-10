from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from .base import Command


class PkexecCommand(Command):
    async def _on_delegated_auth(self, args: list[str]) -> tuple[str, str, int]:
        import shlex

        from cyanide.core.emulator import ShellEmulator

        temp_shell = ShellEmulator(
            self.fs, self.emulator.username, quarantine_callback=self.emulator.quarantine_callback
        )
        temp_shell.cwd = self.emulator.cwd
        cmd_line = shlex.join(args)
        return await temp_shell.execute(cmd_line)  # type: ignore[no-any-return]

    async def execute(self, args, input_data=""):
        if not args:
            return "", "pkexec: must specify a program to execute\n", 1

        # Execute automatically without password prompt
        return await self._on_delegated_auth(args)
