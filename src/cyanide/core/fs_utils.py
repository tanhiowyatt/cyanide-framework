import random
import os
from pathlib import Path
from typing import List


def get_fs_config_dir() -> Path:
    """Return the absolute path to the config/profiles directory."""
    current_dir = Path(__file__).parent
    # Go up 3 levels: core -> cyanide -> src -> root
    root_dir = current_dir.parent.parent.parent
    return root_dir / "configs" / "profiles"


def list_profiles() -> List[str]:
    """List all available OS profiles (subdirectories in configs/profiles)."""
    fs_dir = get_fs_config_dir()
    if not fs_dir.exists():
        return ["ubuntu"]
        
    profiles = []
    for item in fs_dir.iterdir():
        if item.is_dir() and (item / "base.yaml").exists():
            profiles.append(item.name)
            
    return profiles or ["ubuntu"]


def resolve_os_profile(profile_name: str) -> str:
    """
    Resolve the OS profile name.
    
    If profile is 'random', pick a random available profile.
    Otherwise, return the profile name if it exists.
    """
    profiles = list_profiles()
    
    if profile_name == "random":
        return random.choice(profiles)
        
    if profile_name in profiles:
        return profile_name
        
    # Fallback
    return "ubuntu"
