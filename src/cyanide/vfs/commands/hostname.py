import asyncio

from .base import Command


class HostnameCommand(Command):
    """Show or set the system's host name."""

    async def execute(self, args: list[str], input_data: str = "") -> tuple[str, str, int]:
        await asyncio.sleep(0)

        # Determine current hostname, prioritizing resolved context hostname
        hostname = ""
        if self.fs.context and hasattr(self.fs.context, "hostname"):
            hostname = self.fs.context.hostname

        if not hostname:
            if self.fs.exists("/etc/hostname"):
                content = self.fs.get_content("/etc/hostname")
                if isinstance(content, bytes):
                    content = content.decode("utf-8", errors="replace")
                hostname = content.strip()
                if "{{" in hostname and self.fs.context:
                    try:
                        from jinja2 import Template

                        hostname = Template(hostname).render(**self.fs.context.to_dict()).strip()
                    except Exception:
                        pass

        if not hostname or "{{" in hostname:
            hostname = "localhost"

        if not args:
            return f"{hostname}\n", "", 0

        show_fqdn = False
        show_short = False
        show_domain = False
        show_ip = False
        show_alias = False
        set_name = None

        for arg in args:
            if arg in ("-f", "--fqdn", "--long"):
                show_fqdn = True
            elif arg in ("-s", "--short"):
                show_short = True
            elif arg in ("-d", "--domain"):
                show_domain = True
            elif arg in ("-i", "-I", "--ip-address", "--all-ip-addresses"):
                show_ip = True
            elif arg in ("-a", "--alias"):
                show_alias = True
            elif arg.startswith("-"):
                opt = arg.lstrip("-")
                return "", f"hostname: invalid option -- '{opt}'\n", 1
            else:
                if set_name is None:
                    set_name = arg

        if set_name is not None:
            if self.username != "root":
                return "", "hostname: you must be root to change the host name\n", 1
            if self.fs.context:
                self.fs.context.hostname = set_name
            return "", "", 0

        if show_ip:
            return f"{self.get_ip_addr()}\n", "", 0

        if show_fqdn:
            return f"{hostname}.localdomain\n", "", 0

        if show_domain:
            return "localdomain\n", "", 0

        if show_short:
            return f"{hostname.split('.')[0]}\n", "", 0

        if show_alias:
            return "\n", "", 0

        return f"{hostname}\n", "", 0
