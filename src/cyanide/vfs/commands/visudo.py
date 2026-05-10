import asyncio

from .base import Command
from .editor import VimCommand


class VisudoCommand(Command):
    """Modern visudo emulation using the full-screen Vim interface."""

    async def execute(self, args: list[str], input_data: str = "") -> tuple[str, str, int]:
        await asyncio.sleep(0.1)
        if self.emulator.username != "root":
            return (
                "",
                "visudo: /etc/sudoers: Permission denied\n",
                1,
            )

        # Delegate to the new visual Vim editor for /etc/sudoers
        vim = VimCommand(self.emulator)
        return await vim.execute(["/etc/sudoers"])
