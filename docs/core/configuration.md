# Configuration Guide

Cyanide is highly customizable through YAML-based configuration files and environment variables.

## ⚙️ Global Configuration (`configs/app.yaml`)

The `app.yaml` file controls the core behavior of the honeypot.

### Networking & Services
- **`ssh.port`**: Port to listen for SSH (default: 2222).
- **`telnet.port`**: Port to listen for Telnet (default: 2223).
- **`backend_mode`**: Either `emulator` (simulated shell), `proxy` (forwarding to a real server), or `pool` (Libvirt VM orchestration).

### Logging & Rotation
Unified rotation policy for `cyanide-server.json`, `cyanide-fs.json`, `cyanide-ml.json` and `cyanide-stats.json`.
- **`logging.directory`**: Master log path (default: `var/log/cyanide`).
- **`logging.logtype`**: Mode to write (`plain` or `rotating`).
- **`logging.rotation.strategy`**: Method for triggering rotation (`time` or `size`).
- **`logging.rotation.when`**: Interval point for timing rotations (e.g `midnight`).
- **`logging.rotation.interval`**: Unit frequency before rotation if strategy=time (default: 1).
- **`logging.rotation.backup_count`**: Historical handlers retention (default: 14).
- **`logging.rotation.max_bytes`**: Maximum single-file scale before rotation if strategy=size (default: 10485760).

### VM Pool Orchestration (Libvirt)
When `backend_mode` is set to `pool`, Cyanide can automatically manage backend VMs.
- **`pool.enabled`**: Enable the orchestration pool (default: false).
- **`pool.mode`**: Set to `libvirt` for full lifecycle management.
- **`pool.max_vms`**: Maximum concurrently running VMs.
- **`pool.recycle_period`**: How often to recycle VMs (in seconds).
- **`pool.libvirt_uri`**: Connection URI (e.g., `qemu:///system`).

### SSH Fingerprinting & Forwarding
- **`ssh.ciphers`**: List of allowed encryption algorithms.
- **`ssh.macs`**: List of allowed MAC algorithms.
- **`ssh.kex_algs`**: List of allowed Key Exchange algorithms.
- **`ssh.forwarding_enabled`**: Enable or disable SSH port forwarding (`-L` / `-R`).
- **`ssh.forward_redirect_enabled`**: Enable rules-based redirection for forwarded traffic.
- **`ssh.forward_redirect_rules`**: Mapping of port -> target host:port.

### Detection Engine (ML)
- **`enabled`**: Toggle the hybrid detection engine.
- **`threshold`**: The anomaly score above which a command is flagged as malicious.
- **`model_path`**: Path to the pre-trained LSTM Autoencoder model.

### Services
- **`quarantine.enabled`**: Toggle automatic malware interception.
- **`stats.enabled`**: Toggle Prometheus metrics export.
- **`telemetry.enabled`**: Toggle Jaeger tracing.

---

## 🎭 OS Profiles (`configs/profiles/`)

Profiles allow Cyanide to masquerade as different Linux distributions. Each profile is a directory containing:

### 1. `base.yaml` (Metadata & Dynamics)
Defines the "Identity" of the OS.
```yaml
metadata:
  os_name: "Ubuntu"
  hostname: "web-server-01"
  kernel_version: "5.15.0-73-generic"
  arch: "x86_64"
  os_id: "ubuntu"
  version_id: "22.04"

dynamic_files:
  /proc/uptime: { provider: uptime_provider }
  /proc/cpuinfo: { provider: cpuinfo_provider }
```

### 2. `static.yaml` (Filesystem Manifest)
Maps virtual paths to content or source files natively within the YAML structure.
- **`content`**: Inline string content directly embedded in the YAML file.
- **`source`**: Path to a file on the host (relative to the profile root) - typically used for large binaries.

*(Note: Physical `root/` directories are deprecated. All filesystem structure is now defined purely in `static.yaml` for consistency and speed.)*

```yaml
static:
  /etc/issue:
    content: "Welcome to {{ os_name }} {{ version_id }}\n"
```

---

## 🌍 Environment Variables

Cyanide utilizes a robust, dynamic environment variable override system. **Every** configuration setting defined natively in `configs/app.yaml` can be overridden using the `CYANIDE_` prefix via your `docker-compose.yml` or shell environment.

### Syntax Rules
1. Prefix the variable with `CYANIDE_`.
2. Convert the YAML key path to uppercase.
3. Replace nested dictionary levels with a single underscore `_` (e.g., `ssh.port` becomes `CYANIDE_SSH_PORT`).
4. Some deep mappings (like logging rotation) use double underscores for specific disambiguation depending on the schema (e.g., `CYANIDE_LOGGING_ROTATION_STRATEGY`).

**Examples:**
- Override the main OS profile (`honeypot.os_profile` -> `CYANIDE_HONEYPOT_OS_PROFILE=ubuntu`)
- Override the ML anomaly threshold (`ml.threshold` -> `CYANIDE_ML_THRESHOLD=0.95`)
- Enable PostgreSQL output (`output.postgresql.enabled` -> `CYANIDE_OUTPUT_POSTGRESQL_ENABLED=true`)
- Override Telnet Backend Mode (`telnet.backend_mode` -> `CYANIDE_TELNET_BACKEND_MODE=proxy`)

*For a full list of all possible environment overrides, refer to `docs/com.txt` within the project root.*
