import shlex
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from .base import Command


class SudoCommand(Command):
    """Execute a command as another user (mock)."""

    async def execute(self, args: list[str], input_data: str = "") -> tuple[str, str, int]:
        """Execute command as root or switch user."""
        result = self._parse_sudo_args(args)
        if "err" in result:
            return "", result["err"], 1
        if "output" in result:
            return result["output"], "", 0

        target_user = result["target_user"]
        command_args = result["command_args"]
        interactive = result["interactive"]

        if not command_args:
            if interactive:
                return self._handle_interactive(target_user)
            return "", self._usage(), 1

        return await self._handle_command(target_user, command_args, interactive)

    def _parse_sudo_args(self, args: list[str]) -> dict:
        """Parse sudo arguments and return a result dictionary."""
        res = {"target_user": "root", "command_args": [], "interactive": False}
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "-u":
                if i + 1 < len(args):
                    res["target_user"] = args[i + 1]
                    i += 2
                else:
                    return {"err": "sudo: option requires an argument -- 'u'\n"}
            elif arg == "-l":
                return {"output": self._list_privileges()}
            elif arg in ("-i", "-s"):
                res["interactive"] = True
                i += 1
            elif arg.startswith("-"):
                i += 1
            else:
                res["command_args"] = args[i:]
                break
        return res

    def _list_privileges(self) -> str:
        """Return the output for 'sudo -l'."""
        return (
            f"Matching Defaults entries for {self.emulator.username} on server:\n"
            f"    env_reset, mail_badpass, secure_path=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\n\n"
            f"User {self.emulator.username} may run the following commands on server:\n"
            f"    (ALL : ALL) ALL\n"
        )

    def _handle_interactive(self, target_user: str) -> tuple[str, str, int]:
        # Switch the current emulator user and update CWD.
        if target_user != "root":
            self.emulator.username = target_user

        home = self.emulator.get_home_dir(target_user)
        self.emulator.cwd = home
        if not self.fs.exists(home):
            self.emulator.cwd = "/"
        return "", "", 0

    async def _handle_command(
        self, target_user: str, command_args: list[str], interactive: bool
    ) -> tuple[str, str, int]:
        """Execute a sub-command as the target user."""
        from cyanide.core.emulator import ShellEmulator

        # Use original username if target is root to maintain connection identity
        effective_user = self.emulator.username if target_user == "root" else target_user
        temp_shell = ShellEmulator(self.fs, effective_user, self.emulator.quarantine_callback)
        if not interactive:
            temp_shell.cwd = self.emulator.cwd

        cmd_line = shlex.join(command_args)
        return await temp_shell.execute(cmd_line)  # type: ignore[no-any-return]

    def _usage(self) -> str:
        """Return the sudo usage message."""
        return "usage: sudo -h | -K | -k | -V\nusage: sudo -v [-AknS] [-g group] [-h host] [-p prompt] [-u user]\n"
