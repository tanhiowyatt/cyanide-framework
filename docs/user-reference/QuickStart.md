# Quick Start Guide

Welcome to **Cyanide**! This guide will help you deploy your medium-interaction honeypot in minutes.

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:
*   **Docker & Docker Compose** (Recommended for ease of use)
*   **Python 3.9+** (Required if running without Docker)
*   **Git** (To clone the repository)

---

## 🐳 Method 1: Docker (Recommended)

Using Docker is the most reliable way to ensure Cyanide runs in a consistent environment with all dependencies managed.

### 1. Clone & Enter
```bash
git clone https://github.com/tanhiowyatt/cyanide-honeypot.git
cd cyanide-honeypot
```

### 2. Launch the Stack
Run the following command to build and start the services in detached mode:
```bash
docker-compose up -d --build
```

### 3. Verify Health
Monitor the startup logs to ensure the SSH and Telnet services are ready:
```bash
docker-compose logs -f
```

### 4. Perform a Test Connection
Open a new terminal and attempt to connect to your honeypot:
```bash
ssh root@localhost -p 2222
```
> [!NOTE]
> The default password is `admin`. You can change this later in your configuration.

---

## 📦 Method 2: PyPI Installation

For lightweight deployments or dedicated virtual environments.

### 1. Install via Pip
```bash
pip install cyanide-honeypot
```

### 2. Initialize & Run
Simply run the command to start the honeypot using default settings:
```bash
cyanide-honeypot
```

---

## What's Next?

Now that your honeypot is live, here is how to take it to the next level:

*   **Customization**: Adjust your `docker-compose.yml` to enable Telnet or change the SSH version string.
*   **Deep Config**: Explore the [Advanced Usage Guide](AdvancedUsage.md) for a full reference of environment variables.
*   **Alerting**: Connect your logs to Slack or ELK via the [Integrations Guide](Integrations.md).

---

> [!CAUTION]
> **Safety First!**
> Always deploy honeypots in isolated network segments (VLANs/DMZs). Ensure that the honeypot host does not have access to sensitive internal resources.

---
<p align="center">
  <i>Revision: 1.0 • April 2026 • Cyanide Honeypot</i>
</p>
