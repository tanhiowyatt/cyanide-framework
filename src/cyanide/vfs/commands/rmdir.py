import asyncio

from .base import Command


class RmdirCommand(Command):
    async def execute(self, args, input_data=""):
        await asyncio.sleep(0)
        if not args:
            return "", "rmdir: missing operand\n", 1

        for arg in args:
            path = self.emulator.resolve_path(arg)
            node = self.fs.get_node(path)

            if not node:
                return (
                    "",
                    f"rmdir: failed to remove '{arg}': No such file or directory\n",
                    1,
                )

            if not self.fs.is_dir(path):
                return "", f"rmdir: failed to remove '{arg}': Not a directory\n", 1

            if self.fs.list_dir(path):
                return (
                    "",
                    f"rmdir: failed to remove '{arg}': Directory not empty\n",
                    1,
                )

            if not self.fs.remove(path):
                return (
                    "",
                    f"rmdir: failed to remove '{arg}': Operation not permitted\n",
                    1,
                )

        return "", "", 0
