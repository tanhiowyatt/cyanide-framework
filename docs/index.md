# Cyanide Honeypot Documentation

Cyanide is a high-interaction SSH/Telnet/SMTP honeypot designed for capturing attacker activity, analyzing behavior with ML, and collecting malware samples.

## Project Structure

*   **/bin**: Executable entry points for the honeypot and utility scripts.
*   **/src**: The main source code of the application.
    *   **core**: The heart of the system (Server, Fake Filesystem, Shell Emulator).
    *   **commands**: Implementations of emulated shell commands (ls, cd, wget, etc.).
    *   **proxy**: Network proxies for SSH, Telnet, and generic TCP forwarding.
    *   **cyanide**: Shared utilities, logging, and filesystem persistence.
*   **/ai-models**: Machine Learning components for traffic analysis and anomaly detection.
*   **/etc**: Configuration files.
*   **/tools**: Helper scripts for dataset generation and log monitoring.
*   **/var**: Runtime data (logs, quarantine, databases).

## Quick Links

1.  [Core Engine & Proxy Architecture](core_and_proxy.md) - Details on `server.py`, `vm_pool.py`, and proxies.
2.  [Filesystem & Commands](fs_and_commands.md) - How the fake FS works and how to add commands.
3.  [AI & Machine Learning](ai_ml.md) - Documentation for `cyanideML` module.
4.  [Tools & Binaries](tools_and_bin.md) - Guide to CLI tools like `cyanide-replay`.
6.  [Configuration](configuration.md) - Reference for `cyanide.cfg`.
7.  [Developer Guide](development.md) - How to contribute, test, and extend.

---

# User Guide: Quick Start

# User Guide: Quick Start

**Note: This project is designed to run exclusively within Docker.**

## 1. Prerequisites

Ensure you have **Docker** and **Docker Compose** installed on your machine.

## 2. Starting the Honeypot

Use the provided compose file to build and start the service:

```bash
docker compose -f docker/docker-compose.yml up --build -d
```

Check the status:
```bash
docker compose -f docker/docker-compose.yml ps
```

## 3. Testing the Connection

Connect to the honeypot exposed on localhost ports:

**SSH:**
```bash
# Default password: admin
ssh root@localhost -p 2222
```

**Telnet:**
```bash
telnet localhost 2223
```

## 4. Monitoring Logs

To view the live logs from the container:

```bash
docker compose -f docker/docker-compose.yml logs -f
```

## 5. Stopping
```bash
docker compose -f docker/docker-compose.yml down
```
