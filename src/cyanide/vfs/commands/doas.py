from .base import Command


class DoasCommand(Command):
    async def execute(self, args, input_data=""):
        if not args:
            return (
                "",
                "usage: doas [-nSs] [-a style] [-C conf] [-u user] command [args]\n",
                1,
            )

        if self.emulator.username == "root":
            return await self._execute_subcommand(args)

        # Set up password prompt and internal callback that uses delegation
        self.emulator.pending_input_callback = lambda _: self._on_delegated_auth(args)
        self.emulator.pending_input_prompt = f"[cyanide] password for {self.emulator.username}: "
        return "", "", 0

    async def _on_delegated_auth(self, args: list[str]) -> tuple[str, str, int]:
        import shlex
        from typing import cast

        from cyanide.core.emulator import ShellEmulator

        temp_shell = ShellEmulator(
            self.fs, "root", quarantine_callback=self.emulator.quarantine_callback
        )
        temp_shell.cwd = self.emulator.cwd
        cmd_line = shlex.join(args)
        return cast(tuple[str, str, int], await temp_shell.execute(cmd_line))
