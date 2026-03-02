# Cyanide

![alt text](assets/branding/name.png)

**Cyanide** is a high-interaction SSH & Telnet honeypot designed to deceive and analyze attacker behavior. It combines realistic Linux filesystem emulation, advanced command simulation (pipes, redirections), and deep anti-detection mechanisms with a hybrid ML-based anomaly detection engine.

---

### 🌐 Translations
*   🇷🇺 [Russian (Русский)](docs/README.RU.md)
*   🇵🇱 [Polish (Polski)](docs/README.PL.md)

---

## 🌟 Key Features

### 🧠 Realistic Emulation
*   **Multi-protocol**: SSH (`asyncssh`) and Telnet on customizable ports (default 2222/2223).
*   **Dynamic VFS**: Fully functional in-memory Linux filesystem loaded from YAML profiles. Changes persist per session.
*   **Advanced Shell**: Supports pipes (`|`), redirections (`>`, `>>`), logic (`&&`, `||`), and environment variables.
*   **Anti-Fingerprinting**: 
    *   **Network Jitter**: Randomized response delays (50-300ms).
    *   **OS Profiles**: Realistic masquerade as **Ubuntu**, **Debian**, or **CentOS** with data-driven `ps` lists, dynamic `/proc` files, and historical filesystem timestamps.

### 🛡️ Hybrid Detection System
Cyanide employs a 3-layer detection engine to identify malicious intent:
1.  **ML Anomaly Detector**: Autoencoder neural network detects abnormal command structures (zero-day/obfuscation).
2.  **Security Rule Engine**: Regex-based signatures for known threats (`wget`, `curl | bash`, etc.).
3.  **Context Analyzer**: Semantic analysis of accessed files (`/etc/shadow`) and reputation checks (domains/IPs).

### 📊 Forensics & Logging
*   **TTY Recording**: Full session replay compatible with `scriptreplay` (timing + data).
*   **JSON Structured Logs**: Detailed events for ELK/Splunk integration.
*   **Keystroke Biometrics**: Typing rhythm analysis.
*   **Quarantine**: Automatic isolation of downloaded malware (`wget`).
*   **VirusTotal Integration**: Automatic scanning of quarantined files.

---

## 📚 Documentation Suite

For detailed technical guides, please refer to our specialized documentation:

| Document | Description |
|----------|-------------|
| 🏛️ [**Architecture**](docs/ARCHITECTURE.md) | Deep dive into the Engine, Shell Emulator, and VFS model. |
| 🔧 [**Development**](docs/DEVELOPMENT.md) | Setup, testing protocols, and how to contribute code. |
| 📊 [**Operations**](docs/OPERATIONS.md) | Logging, Monitoring, Forensics, and Replay tools. |

---

## 🚀 Quick Start

**Cyanide is designed to be run as a containerized service.**

```bash
# 1. Start the full stack
docker-compose -f deployments/docker/docker-compose.yml up --build -d

# 2. Monitor attacker activity
docker-compose -f deployments/docker/docker-compose.yml logs -f cyanide
```

---

## 🕵️ Data & Forensics

Attacker interactions are recorded in `var/log/cyanide/` as structured JSON events and full TTY session replays. See the [Operations Guide](docs/OPERATIONS.md) for more details.

---

## ⚠️ Disclaimer
This software is for **educational and research purposes only**. Running a honeypot involves significant risks. The author is not responsible for any damage or misuse.
