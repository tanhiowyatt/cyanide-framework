import asyncio

from .base import Command


class ChmodCommand(Command):
    async def execute(self, args, input_data=""):
        await asyncio.sleep(0)
        if len(args) < 2:
            return "", "chmod: missing operand\n", 1

        mode_arg = args[0]
        targets = args[1:]

        for target in targets:
            path = self.emulator.resolve_path(target)
            node = self.fs.get_node(path)
            if not node:
                return (
                    "",
                    f"chmod: cannot access '{target}': No such file or directory\n",
                    1,
                )

            current_perm = node.perm  # e.g., "-rwxr-xr-x"
            prefix = current_perm[0]
            perms = current_perm[1:]  # e.g., "rwxr-xr-x"

            new_perms = list(perms)

            if mode_arg.isdigit():
                # Octal mode
                try:
                    oct_val = int(mode_arg, 8)
                    new_perms = self._octal_to_str(oct_val)
                except ValueError:
                    continue
            else:
                # Relative mode: [ugoa]*[+-=][rwx]*
                import re

                match = re.match(r"([ugoa]*)([+-=])([rwx]*)", mode_arg)
                if match:
                    who, op, what = match.groups()
                    if not who or "a" in who:
                        who = "ugo"

                    for w in who:
                        start_idx = {"u": 0, "g": 3, "o": 6}[w]
                        for i, char in enumerate("rwx"):
                            if char in what:
                                if op == "+":
                                    new_perms[start_idx + i] = char
                                elif op == "-":
                                    new_perms[start_idx + i] = "-"
                                elif op == "=":
                                    # This is more complex, but for now just set it
                                    new_perms[start_idx + i] = char
                        if op == "=":
                            # clear other bits in this group that weren't in 'what'
                            for i, char in enumerate("rwx"):
                                if char not in what:
                                    new_perms[start_idx + i] = "-"

            self.fs.chmod(path, prefix + "".join(new_perms))

        return "", "", 0

    def _octal_to_str(self, octal: int) -> list:
        """Convert octal mode (e.g. 0o755) to string list (e.g. ['r','w','x','r','-','x','r','-','x'])."""
        res = []
        for i in range(2, -1, -1):
            digit = (octal >> (i * 3)) & 0o7
            res.append("r" if digit & 4 else "-")
            res.append("w" if digit & 2 else "-")
            res.append("x" if digit & 1 else "-")
        return res
