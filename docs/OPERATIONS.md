# Operations & Forensics Guide

This guide covers running, monitoring, and analyzing data from the Cyanide Honeypot.

## 📊 Logging Infrastructure

Cyanide generates high-fidelity JSON logs in `var/log/cyanide/`.

### Log Types
- **`cyanide-server.json`**: System-level logs (startup, service status, errors).
- **`cyanide-fs.json`**: Filesystem audit logs (all file reads, writes, and deletions).
- **`cyanide-ml.json`**: Detection engine output (command anomaly scores and classifier results).
- **`tty/`**: Session recordings compatible with `scriptreplay`.

---

## 🔍 Observability & Monitoring

Cyanide is instrumented for deep visibility using modern observability standards.

### Prometheus (Metrics)
Standard system and honeypot metrics are exposed on port `9090` at `/metrics`. 
- **Session Count**: Total active and historical attacker sessions.
- **VFS Activity**: Rate of file operations.
- **Detection Rates**: Distribution of anomaly scores.

### Jaeger (Tracing)
Distributed tracing for complex session flows (e.g., download -> ML analysis -> quarantine).
- **Endpoint**: `http://localhost:16686` (when using Docker Compose).

---

## 🛠️ Management Scripts

Located in `scripts/management/`:

### 1. Real-time Stats
View a dashboard of active sessions and top attacker IPs.
```bash
python3 scripts/management/stats.py
```

### 2. Session Replay
Replay TTY sessions exactly as they appeared to the attacker.
```bash
scriptreplay var/log/cyanide/tty/<session_id>/timing var/log/cyanide/tty/<session_id>/data
```

---

## 🛡️ Forensics & Malware Handling

### Quarantine Service
Any file downloaded by an attacker (via `wget` or `curl`) is automatically:
1.  **Intercepted**: The actual file is moved to `var/quarantine/`.
2.  **Hashed**: MD5/SHA256 calculations for threat intelligence.
3.  **Analyzed**: Automatically submitted to VirusTotal if an API key is configured.
4.  **Emulated**: A fake, benign file of the same name and size is placed in the VFS to avoid suspicious behavior alerts.

### Biometric Analysis
Cyanide captures keystroke timing to build behavioral profiles of attackers, allowing you to distinguish between human operators and automated bots.
