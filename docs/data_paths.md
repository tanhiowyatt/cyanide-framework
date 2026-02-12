# Data Paths Documentation

This document explains the purpose and structure of the static data directories used by Cyanide Honeypot.

## `fs_yaml` (Filesystem Configuration)

**Configuration Key:** `FS_YAML` (env) or `fs_yaml` (cfg)  
**Default Path:** `config/fs-config/fs.yaml`

### Purpose
Defines the virtual filesystem template. OS-specific profiles use this as a base.

### Directory Structure: `config/fs-config/`
- `fs.yaml`: The base template.
- `fs.ubuntu_22_04.yaml`: Generated profile for Ubuntu.
- `fs.debian_11.yaml`: Generated profile for Debian.
- `fs.centos_7.yaml`: Generated profile for CentOS.

### How to Customize
1. **Edit the base:**
   ```bash
   nano config/fs-config/fs.yaml
   ```
2. **Regenerate profiles:**
   ```bash
   python3 generate_profiles.py
   ```
3. **Restart honeypot:**
   ```bash
   docker compose restart
   ```

### Benefits
✅ **YAML Based** — Human-readable and editable.
✅ **OS Specific** — Accurate emulation of different distros.
✅ **Safe** — No binary deserialization.

## `var/` (Persistent Data)
- **`var/log/cyanide/`**: JSON logs and TTY session recordings.
- **`var/lib/cyanide/quarantine/`**: Isolated files captured from attackers.
