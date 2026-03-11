# 🚀 Advanced & Hidden Features

Cyanide contains several "Pro" features that are not enabled by default or are designed for advanced threat intelligence gathering.

## 1. Honeytoken Tripwires (`fs_audit`)

Cyanide has built-in honeytokens—files that no regular user or automated bot should ever touch. Accessing these triggers a **CRITICAL_ALERT** in the logs and is tracked specifically in the statistics.

### Default Tripwires:
- `/home/admin/secret.conf`
- `/home/admin/flag.txt`
- `/etc/shadow`
- `/var/spool/cron/crontabs/root`
- `/root/.ssh/id_rsa`

Any `read` or `write` operation on these paths is flagged immediately, providing a high-fidelity signal of a manual, sophisticated attacker.

## 2. Integrated HTTP Log Browser

The metrics server (default port `9090`) includes a built-in, read-only file browser for your logs. This allows you to inspect TTY recordings and JSON logs via a web browser without needing SSH access to the host.

- **URL**: `http://<your-ip>:9090/logs/`
- **Features**: 
  - Directory listing of `var/log/cyanide/`.
  - Direct reading of `.json` and `.log` files.
  - Path traversal protection (restricted to the log directory).

## 3. SMTP Capture Proxy

Cyanide can act as an SMTP relay to capture spamming attempts or credential exfiltration via email.

- **Listen Port**: 25 (configurable via `smtp.listen_port`).
- **Target**: Redirects traffic to a local SMTP sink (like **MailHog** in the default Docker stack).
- **Benefit**: Attackers believe they are successfully sending mail, but the content is trapped and logged for analysis.

## 4. Advanced Observability (Prometheus & Health)

Beyond the standard stats dashboard, Cyanide exposes a professional-grade monitoring interface.

### Endpoints:
- **`/metrics`**: Full Prometheus-formatted metrics (Total sessions, unique IPs, DNS cache hits, file operation rates, etc.).
- **`/health`**: JSON status check for the SSH and Telnet services, used for automated uptime monitoring (e.g., K8s liveness probes).
- **`/stats`**: The raw JSON data used by the `stats.py` CLI tool.

## 5. Persistence & Mimicry Stability

### Host Key Persistence
Unlike simple honeypots that generate new SSH keys on every restart, Cyanide generates and stores persistent host keys in `var/lib/cyanide/keys/`. 
- **Benefit**: Regular scanners will see the same SSH fingerprint over time, making the honeypot appear as a stable, long-running production server rather than a transient script.

### TTY Dual-Logging
Every session is logged in TWO formats simultaneously:
1. **JSONL (`.jsonl`)**: For easy parsing and grep-searching of session input/output.
2. **Timing/Data (`timing`, `data`)**: For realistic replay using the standard `scriptreplay` command.

## 6. SSH Expert Features (Mimicry & Attribution)

### Public Key "Harvester"
Cyanide supports SSH Public Key authentication, but it is configured as a trap.
- **The Trick**: It tells the client it supports public keys. When the client sends its public key, Cyanide **logs the raw key and its fingerprint** and then **rejects it**, forcing the attacker to fallback to password authentication.
- **Benefit**: You capture the attacker's identity (public key) even if they never successfully log in.

### Client Fingerprinting (HASSH)
During the SSH handshake, Cyanide extracts the exact list of negotiated algorithms (KEX, Cipher, MAC, Compression).
- **Event**: `client_fingerprint`
- **Benefit**: Different SSH clients (OpenSSH, Paramiko, PuTTY, various botnets) have unique algorithm signatures. This allows for high-confidence identification of the attacker's toolkit.

### Port Forwarding Policy Router
Cyanide can intercept SSH tunnels (`-L` or `-R`).
- **Modes**:
  - `Redirect`: Silently move the tunnel target to a local sink (e.g., redirecting a database tunnel to a MySQL honeypot).
  - `Allow & Log`: Let the tunnel pass through but log every byte transferred through the tunnel for forensic analysis.

## 7. Anti-Bot & Behavioral Analysis

### Keystroke Dynamics
Cyanide monitors the timing between individual characters entered by the attacker.
- **Bot Detection**: If the average delay between characters is less than **10ms**, or if an entire command arrives in a single packet (paste), the session is flagged with `is_bot=true`.
- **Jitter Mimicry**: To confuse automated scanners, Cyanide adds randomized millisecond delays to every response, breaking simple "echo" timing attacks.

### Real-time IoC Extraction
Every command entered into the shell is automatically scanned using regex for:
- IPv4 addresses
- HTTP/HTTPS URLs

If found, an `ioc_detected` event is logged immediately, allowing for real-time alerting on potential Command & Control (C2) domains.

### Profile-Driven Telnet Banners
Unlike other honeypots that use a static login prompt, Cyanide's Telnet service is tightly integrated with the VFS.
- **Dynamic `/etc/issue`**: It reads the welcome banner directly from the active OS profile's `/etc/issue` file.
- **Escape Expansion**: It supports standard Linux escape sequences like `\n` (hostname) and `\l` (tty line), making the pre-login environment indistinguishable from a real server.

## 8. Professional Observability Stack

Cyanide is designed for enterprise-grade deployments where visibility is critical.

### OpenTelemetry (OTEL) & Jaeger
The core engine is instrumented with OpenTelemetry.
- **Distributed Tracing**: If enabled, every command execution and network event generates a trace span.
- **Performance Analysis**: You can visualize the entire lifecycle of an attack in **Jaeger** or any OTLP-compatible backend (Honeycomb, New Relic, etc.).
- **Debug Mode**: Setting `CYANIDE_DEBUG_TRACE=1` will dump all trace spans directly to the console for local debugging.

### Automated Maintenance (`CleanupManager`)
To prevent disk exhaustion in high-traffic environments, Cyanide includes an automated cleanup service.
- **Policy**: Older logs and quarantine files are automatically pruned based on a configurable retention policy (default: 7 days).
- **Paths**: Target directories are configurable via `cleanup.paths`.
