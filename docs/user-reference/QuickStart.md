# Quick Start Guide

Welcome to **Cyanide**! This guide will help you deploy your medium-interaction framework in minutes.

---

##  Prerequisites

Before you begin, ensure you have the following installed:
*   **Docker & Docker Compose** (Recommended for ease of use)
*   **Python 3.9+** (Required if running without Docker)
*   **Git** (To clone the repository)

---

##  Method 1: Docker (Recommended)

Using Docker is the most reliable way to ensure Cyanide runs in a consistent environment with all dependencies managed.

### 1. Clone & Enter
```bash
git clone https://github.com/tanhiowyatt/cyanide-framework.git
cd cyanide-framework
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
Open a new terminal and attempt to connect to your framework:
```bash
ssh root@localhost -p 2222
```
> [!NOTE]
> The default password is `admin`. You can change this later in your configuration.

---

##  Method 2: PyPI Installation

For lightweight deployments or dedicated virtual environments.

### 1. Install via Pip
```bash
pip install cyanide-framework
```

### 2. Initialize & Run
Simply run the command to start the framework using default settings:
```bash
cyanide-framework
```

---

## What's Next?

Now that your framework is live, here is how to take it to the next level:

*   **Customization**: Adjust your `docker-compose.yml` to enable Telnet or change the SSH version string.
*   **Deep Config**: Explore the [Advanced Usage Guide](AdvancedUsage.md) for a full reference of environment variables.
*   **Alerting**: Connect your logs to Slack or ELK via the [Integrations Guide](Integrations.md).

---

> [!CAUTION]
> **Safety First!**
> Always deploy frameworks in isolated network segments (VLANs/DMZs). Ensure that the framework host does not have access to sensitive internal resources.

---
<p align="center">
  <i>Revision: 1.0 - May 2026 - Cyanide Framework</i>
</p>
