# Advanced & Hidden Features

Cyanide contains several "Expert" features designed for advanced threat intelligence gathering and deeper attacker attribution.

---

## 1. Honeytoken Tripwires (`fs_audit`)

Cyanide supports configurable honeytokensfiles or directories that should never be accessed by legitimate users. Any interaction with these paths triggers a **CRITICAL_ALERT**.

> [!IMPORTANT]
> **Explicit Configuration Required**: 
> Default tripwires have been removed to prevent fingerprinting. You must define your honeytokens in your configuration. See the **[Advanced Configuration Guide](../../user-reference/AdvancedUsage.md)** for details.

*   **Logic**: Monitoring of `read`, `write`, and `delete` operations.
*   **Signal**: Provides a high-fidelity indicator of a manual, sophisticated attacker.

---

##  2. Integrated HTTP Log Browser

The metrics server (port `9090`) includes a built-in, read-only browser for your logs.

*   **URL**: `http://<your-ip>:9090/logs/`
*   **Security**: Restricted to the log directory with path traversal protection.
*   **Use Case**: Inspecting TTY recordings and JSON logs via a web browser without SSH access.

---

##  3. SMTP Capture Proxy

Cyanide can act as an SMTP relay to capture spamming attempts or credential exfiltration.

*   **Mode**: Emulated or Proxy.
*   **Default Sink**: MailHog (included in the default stack).
*   **Benefit**: Traps attacker emails for forensic analysis without allowing actual spam to exit your network.

---

## 4. Anti-Bot & Behavioral Analysis

Cyanide doesn't just log commands; it analyzes the **soul** of the interaction.

### Keystroke Dynamics
Monitors the timing of characters to distinguish between scripts, "copy-paste," and human typing.
*   **Bot Score**: A value from `0.0` to `1.0`.
*   **Jitter Analysis**: High variance = Human; Low variance = Script.
*   **Threshold**: Sessions are flagged with `is_bot=true` at `> 0.7`.

### Real-time IoC Extraction
Every command is scanned for:
*   IPv4 Addresses
*   HTTP/HTTPS URLs
*   Domain names

---

##  5. SSH Expert Features

### Public Key Harvester
Cyanide tricks clients into sending their public keys.
*   **The Trap**: It announces support for Public Key auth, collects the key/fingerprint, and then rejects it to force a password fallback.
*   **Benefit**: Captures the attacker's unique identity even before a successful login.

### Client Fingerprinting (HASSH)
Analyzes the SSH handshake algorithms to identify the attacker's toolkit (OpenSSH vs. PuTTY vs. Custom Botnet).

---

## 6. Maintenance & Scalability

### `CleanupManager`
Automated service to prevent disk exhaustion.
*   **Policy**: Prunes logs and quarantine files older than the retention limit (e.g., 7 days).
*   **Mechanics**: Scans configured directories on a background interval.

For a full list of maintenance and scalability settings, refer to the **[Advanced Configuration Guide](../../user-reference/AdvancedUsage.md)**.

---
<p align="center">
  <i>Revision: 1.0  April 2026  Cyanide Honeypot</i>
</p>
