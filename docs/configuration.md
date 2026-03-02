# Configuration Guide

Cyanide is highly customizable through YAML-based configuration files and environment variables.

## ⚙️ Global Configuration (`configs/app.yaml`)

The `app.yaml` file controls the core behavior of the honeypot.

### Networking & Services
- **`ssh.port`**: Port to listen for SSH (default: 2222).
- **`telnet.port`**: Port to listen for Telnet (default: 2223).
- **`backend_mode`**: Either `emulator` (simulated shell) or `proxy` (forwarding to a real server).

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
Maps virtual paths to content or source files.
- **`content`**: Inline string content (supports Jinja2 templating).
- **`source`**: Path to a file on the host (relative to the profile root).
- **`root/` mapping**: Uses glob patterns to mirror directories.
```yaml
static:
  /etc/issue:
    content: "Welcome to {{ os_name }} {{ version_id }}\n"
  /bin/**:
    source: "ubuntu/root/bin/"
```

---

## 🌍 Environment Variables

Environment variables defined in your `docker-compose.yml` or shell will override settings in `app.yaml`:

- `OS_PROFILE`: Force a specific profile (e.g., `debian`). Default is `random`.
- `ML_THRESHOLD`: Override the anomaly detection threshold.
- `SERVER_PORT`: Override the primary listening port.
