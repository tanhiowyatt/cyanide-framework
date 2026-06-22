import asyncio
import os

from .base import Command


class DdCommand(Command):
    """Copy a file, converting and formatting according to the operands."""

    async def execute(self, args: list[str], input_data: str = "") -> tuple[str, str, int]:
        await asyncio.sleep(0)

        if_path = None
        of_path = None
        bs = 512
        count = None
        skip = 0
        seek = 0

        for arg in args:
            if arg.startswith("if="):
                if_path = arg[3:]
            elif arg.startswith("of="):
                of_path = arg[3:]
            elif arg.startswith("bs="):
                try:
                    bs_str = arg[3:]
                    multiplier = 1
                    if bs_str.lower().endswith("k"):
                        multiplier = 1024
                        bs_str = bs_str[:-1]
                    elif bs_str.lower().endswith("m"):
                        multiplier = 1024 * 1024
                        bs_str = bs_str[:-1]
                    elif bs_str.lower().endswith("g"):
                        multiplier = 1024 * 1024 * 1024
                        bs_str = bs_str[:-1]
                    bs = int(bs_str) * multiplier
                except ValueError:
                    return "", f"dd: invalid number: '{arg[3:]}'\n", 1
            elif arg.startswith("count="):
                try:
                    count = int(arg[6:])
                except ValueError:
                    return "", f"dd: invalid number: '{arg[6:]}'\n", 1
            elif arg.startswith("skip="):
                try:
                    skip = int(arg[5:])
                except ValueError:
                    return "", f"dd: invalid number: '{arg[5:]}'\n", 1
            elif arg.startswith("seek="):
                try:
                    seek = int(arg[5:])
                except ValueError:
                    return "", f"dd: invalid number: '{arg[5:]}'\n", 1

        if not if_path:
            input_bytes = input_data.encode("utf-8") if isinstance(input_data, str) else input_data
        else:
            abs_if_path = self.emulator.resolve_path(if_path)
            if not self.fs.exists(abs_if_path):
                return "", f"dd: failed to open '{if_path}': No such file or directory\n", 1
            if self.fs.is_dir(abs_if_path):
                return "", f"dd: failed to open '{if_path}': Is a directory\n", 1

            if abs_if_path in ("/dev/random", "/dev/urandom"):
                read_len = bs * (count if count is not None else 1000)
                input_bytes = os.urandom(read_len)
            elif abs_if_path == "/dev/sda":
                read_offset = skip * bs
                read_count = count if count is not None else 128
                read_len = bs * read_count
                max_read = 10 * 1024 * 1024  # 10MB limit
                if read_len > max_read:
                    read_len = max_read
                input_bytes = self.fs._generate_sda_data(read_offset, read_len)
            else:
                raw_content = self.fs.get_content(abs_if_path)
                if isinstance(raw_content, str):
                    input_bytes = raw_content.encode("utf-8")
                else:
                    input_bytes = raw_content or b""

        # Apply skip (only if it wasn't /dev/sda where we already read from offset)
        if if_path != "/dev/sda":
            skip_bytes = skip * bs
            if skip_bytes < len(input_bytes):
                input_bytes = input_bytes[skip_bytes:]
            else:
                input_bytes = b""

        if count is not None and if_path not in ("/dev/random", "/dev/urandom", "/dev/sda"):
            input_bytes = input_bytes[: count * bs]

        output_bytes = input_bytes
        records_in = len(output_bytes) // bs
        records_out = records_in
        bytes_copied = len(output_bytes)

        stats = (
            f"{records_in}+0 records in\n"
            f"{records_out}+0 records out\n"
            f"{bytes_copied} bytes copied, 0.001 s, {bytes_copied / 1000.0:.1f} MB/s\n"
        )

        if of_path:
            abs_of_path = self.emulator.resolve_path(of_path)
            if seek > 0 and self.fs.exists(abs_of_path):
                existing = self.fs.get_content(abs_of_path)
                if isinstance(existing, str):
                    existing = existing.encode("utf-8")
                else:
                    existing = existing or b""
                seek_bytes = seek * bs
                if len(existing) < seek_bytes:
                    existing = existing + b"\0" * (seek_bytes - len(existing))
                new_content = existing[:seek_bytes] + output_bytes
            else:
                new_content = b"\0" * (seek * bs) + output_bytes

            self.fs.mkfile(
                abs_of_path, content=new_content, owner=self.username, group=self.username
            )
            return "", stats, 0
        else:
            stdout_str = output_bytes.decode("utf-8", errors="replace")
            return stdout_str, stats, 0
