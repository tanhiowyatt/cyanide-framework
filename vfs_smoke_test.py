import asyncio
import os
import sys
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).parent / "src"))

from cyanide.core.server import HoneypotServer
from cyanide.core.emulator import ShellEmulator

async def verify_profile(server, profile_name):
    print(f"\n--- Verifying Profile: {profile_name} ---")
    server.os_profile = profile_name
    fs = server.get_filesystem()
    emulator = ShellEmulator(fs, username="root")
    
    files_to_check = [
        "/etc/issue",
        "/etc/hostname",
        "/etc/hosts",
        "/etc/group",
        "/etc/ssh/sshd_config",
        "/root/.bashrc"
    ]
    
    for f in files_to_check:
        stdout, stderr, code = await emulator.execute(f"cat {f}")
        if code == 0:
            print(f"[OK] {f} content (first line): {stdout.strip().splitlines()[0] if stdout.strip() else 'EMPTY'}")
        else:
            print(f"[FAIL] {f} - {stderr.strip()}")

async def smoke_test():
    config = {
        "os_profile": "ubuntu",
        "vfs_root": "configs/profiles",
        "logging": {"directory": "var/log/cyanide"},
        "users": [{"user": "root", "pass": "root"}]
    }
    
    # Ensure log dir exists
    os.makedirs("var/log/cyanide", exist_ok=True)
    
    server = HoneypotServer(config)
    
    for profile in ["ubuntu", "debian", "centos"]:
        await verify_profile(server, profile)

if __name__ == "__main__":
    asyncio.run(smoke_test())
