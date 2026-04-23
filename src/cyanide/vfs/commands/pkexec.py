from .base import Command


class PkexecCommand(Command):
    async def execute(self, args, input_data=""):
        if not args:
            return "", "pkexec: must specify a program to execute\n", 1

        if self.emulator.username == "root":
            return await self._execute_subcommand(args)

        self.emulator.pending_input_callback = lambda _: self._on_delegated_auth(args)
        self.emulator.pending_input_prompt = f"==== AUTHENTICATING FOR org.freedesktop.policykit.exec ====\nAuthentication is required to run {args[0]} as the super user\nAuthenticating as: {self.emulator.username}\nPassword: "
        return self.emulator.pending_input_prompt, "", 0

    async def _on_delegated_auth(self, args: list[str]) -> tuple[str, str, int]:
        self.emulator.username = "root"
        return await self._execute_subcommand(args)
