# Configuration Documentation

The main configuration file is located at `config/cyanide.cfg`.

## [honeypot]
General settings.
*   `hostname`: hostname of the fake server.
*   `log_path`: Directory for logs.
*   `data_path`: Directory for persistence.
*   `fs_yaml`: Primary YAML filesystem template (optional if using profiles).


## [server]
Connection handling settings.
*   `host`: Listen address (0.0.0.0).
*   `max_sessions`: Global connection limit.
*   `session_timeout`: Inactivity timeout in seconds.
*   `os_profile`: OS personality (`ubuntu_22_04`, `debian_11`, `centos_7`, `custom`, or `random`).
    *   If `custom` is selected, the honeypot loads metadata from the `[custom_profile]` section and expects a filesystem at `config/fs-config/fs.custom.yaml`.

## [custom_profile]
Required if `os_profile = custom`.
*   `name`: Descriptive name (e.g., "Generic Router").
*   `ssh_banner`: Version string (e.g., `SSH-2.0-OpenSSH_9.0`).
*   `uname_r`: Kernel release (`6.1.0`).
*   `uname_a`: Full uname output.
*   `etc_issue`: Content of `/etc/issue`.
*   `proc_version`: Content of `/proc/version`.

## [ssh]
SSH Service settings.
*   `enabled`: true/false.
*   `port`: Listening port (default 2222).
*   `version`: SSH Banner string (or handled by os_profile).
*   `backend_mode`:
    *   `emulated`: Use Fake Filesystem (default).
    *   `proxy`: Forward to a single target (`target_host`:`target_port`).
    *   `pool`: Forward to a target from the pool.

## [telnet]
Telnet Service settings.
*   `enabled`: true/false.
*   `port`: Listening port (default 2223).
*   `backend_mode`: `emulated` / `proxy` / `pool`.

## [smtp]
SMTP Proxy settings.
*   `enabled`: true/false.
*   `listen_port`: Port to accept connections (e.g., 2525).
*   `target_host`: Real honeypot/server (e.g., Mailoney).
*   `target_port`: Port of the target.

## [pool]
VM Pool configuration for `backend_mode = pool`.
*   `targets`: Comma-separated list of `host:port` (e.g., `192.168.1.10:22,192.168.1.11:22`).

## [users]
Allowed credentials for Emulated mode.
*   Format: `username = password`
*   Example: `root = 123456`

## [ml]
Machine Learning settings.
*   `enabled`: true/false.

## [cleanup]
Auto-cleanup settings.
*   `enabled`: true/false.
*   `interval`: Check interval in seconds.
*   `retention_days`: Delete logs older than X days.

---

# Configuration Scenarios

## 1. Changing Listening Ports
If you want to run Cyanide on standard ports (22, 23), you must run it as root (not recommended) or use `authbind` / `iptables` redirection.

**Config:**
```ini
[ssh]
port = 2222  <-- Change to desired port
```

**Iptables Redirection (Preferred):**
```bash
sudo iptables -t nat -A PREROUTING -p tcp --dport 22 -j REDIRECT --to-port 2222
```

## 2. Setting Up a VM Pool (Hybrid Mode)
To use real QEMU/KVM backends instead of the fake shell:

1.  Start your VMs and ensure you can SSH into them (e.g., at 192.168.122.10 and .11).
2.  Edit `config/cyanide.cfg`:
```ini
[ssh]
enabled = true
backend_mode = pool

[pool]
targets = 192.168.122.10:22, 192.168.122.11:22
```
3.  Restart Cyanide. Incoming SSH connections will be transparently proxied to one of the VMs.

## 3. Creating Custom Users
To catch attackers using specific credentials (like `oracle:oracle`):

Edit `config/cyanide.cfg`:
```ini
[users]
root = admin
oracle = oracle
test = 1234
```
*Note: In 'emulated' mode, any username not in this list will fail authentication.*
