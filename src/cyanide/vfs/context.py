from dataclasses import asdict, dataclass, field
from typing import Any, Dict


@dataclass
class Context:
    """Global system metadata context for VFS templates and providers."""

    os_name: str
    kernel_version: str
    hostname: str
    arch: str
    ssh_banner: str = "SSH-2.0-OpenSSH_8.0"
    version_id: str = ""
    os_id: str = ""
    install_date: str = ""
    uptime: str = ""
    system_templates: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for Jinja2 rendering."""
        return asdict(self)
