<p align="center">

  [![Stars](https://img.shields.io/github/stars/tanhiowyatt/cyanide-framework?style=flat&logo=GitHub&color=yellow)](https://github.com/tanhiowyatt/cyanide-framework/stargazers)
  [![CI](https://github.com/tanhiowyatt/cyanide-framework/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/tanhiowyatt/cyanide-framework/actions/workflows/ci.yml)
  [![Security Scan](https://github.com/tanhiowyatt/cyanide-framework/actions/workflows/security_scan.yml/badge.svg)](https://github.com/tanhiowyatt/cyanide-framework/actions/workflows/security_scan.yml)
  [![Quality gate](https://sonarcloud.io/api/project_badges/measure?project=tanhiowyatt_cyanide_framework&metric=alert_status)](https://sonarcloud.io/dashboard?id=tanhiowyatt_cyanide_framework)
  [![Coverage](https://sonarcloud.io/api/project_badges/measure?project=tanhiowyatt_cyanide_framework&metric=coverage)](https://sonarcloud.io/component_measures/metric/coverage/list?id=tanhiowyatt_cyanide_framework)
  [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
  [![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/tanhiowyatt/cyanide-framework)
</p>


<p align="center">
  <a target="_blank" href="https://github.com/tanhiowyatt/cyanide-framework/blob/main/README.md">ENG</a> &nbsp; | &nbsp;
  <a target="_blank" href="https://github.com/tanhiowyatt/cyanide-framework/blob/main/docs/translations/readme-ru.md">RU</a> &nbsp; | &nbsp;
  <a target="_blank" href="https://github.com/tanhiowyatt/cyanide-framework/blob/main/docs/translations/readme-pl.md">PL</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/tanhiowyatt/cyanide-framework/main/src/cyanide/assets/branding/name.png" alt="Cyanide" width="500" height="auto">
</p>

# Cyanide  Medium-Interaction SSH and Telnet Honeypot
 
**Cyanide** is a medium-interaction SSH and Telnet honeypot designed to deceive attackers and analyze their behavior in depth. It combines realistic Linux filesystem emulation, advanced command simulation (with pipes and redirections), robust anti-detection mechanisms, and a hybrid ML engine for anomaly detection.


---

### Features

#### 1) Machine Learning for Automated Attack Classification and IOC Extraction
- The system automatically categorizes network activity into attack types (brute-force, credential stuffing, reconnaissance, exploit attempts) based on session behavior and payload characteristics.
- Events are normalized with extraction of Indicators of Compromise (IOCs), including IP addresses, ports, credentials, user agents/banners, commands, URLs, artifact hashes, and attacker frequency dictionaries.
- A session summary is generated, detailing the attack intent, deviations from baseline norms, and recommended IOCs for blocking or integration into detection rules.

#### 2) Enhanced Realism to Evade Honeypot Detection
- Realistic timing and response variability (errors, delays, message formats) increase misclassification rates by automated honeypot detectors.
- Dynamic environment profiles: service banners, versions, and operational narratives evolve naturally, avoiding static templates.
- Human-like interface behavior: plausible constraints, error messaging, and minor inconsistencies characteristic of production systems.

#### 3) Advanced SOC and Analytics Integrations
- Structured JSON logs with a standardized event schema to facilitate correlation and search.
- Event export to external systems: SIEM/log stacks (ELK/Splunk), webhook alerts (Slack, Discord, Telegram) for real-time notifications.
- Support for batching and message limit control to prevent spam and platform bans.
- Configurable triggers and rules for critical pattern alerts (e.g., anomalous brute-force velocity, dropper uploads, suspicious commands/payloads).

---

###  Documentation

For complete guides on installation, configuration, and integration, visit our **[Documentation Hub](docs/index.md)**.

*   [Quick Start](docs/user-reference/QuickStart.md)
*   [Advanced Configuration](docs/user-reference/AdvancedUsage.md)
*   [Developer Reference](docs/developer-reference/core/index.md)

---

### Quick Start
 
 ```bash
1. Clone the repository
git clone https://github.com/tanhiowyatt/cyanide-framework.git

2. Navigate to the project directory
cd cyanide-framework

3. Launch the environment
docker-compose up -d

4. Connect via SSH, Telnet, or SFTP
ssh root@localhost -p 2222
telnet localhost -p 2222
sftp root@localhost -p 2222

* With Local Changes
docker-compose up -d --build
```

### Quick Start via PyPI

```bash
1. Install the package
pip install cyanide-framework

2. Run the honeypot
cyanide-framework
```

---

### How the Framework Works

Cyanide framework deploys a **decoy service** and guides attackers through a **controlled scenario**: it emulates a realistic service without granting actual host access.

#### Dynamic Profiles and Hardware Emulation
The framework's identity is defined by OS-specific profiles in `src/cyanide/configs/profiles/<os>/`.
- **`base.yaml`**: The master configuration for the profile, containing metadata (kernel version, hostname), honeytokens, and **system templates**.
- **System Templates**: You can now customize the hardware "fingerprint" directly in the YAML.
  - `cpuinfo`: Emulated `/proc/cpuinfo` output.
  - `meminfo`: Emulated `/proc/meminfo` output.
  - `processes`: A list of background processes that will appear in `ps` and `top`.

Example `base.yaml` hardware definition:
```yaml
system_templates:
  cpuinfo: |
    vendor_id	: GenuineIntel
    model name	: Intel(R) Xeon(R) Gold 6140 CPU @ 2.30GHz
    ...
  processes:
    - pid: 1
      user: root
      cmd: "/sbin/init"
```

#### Libvirt Infrastructure (Advanced Emulation)
Cyanide supports an optional **Libvirt backend** for high-fidelity VM-based emulation:
- **VM Pools**: Automatically manage a pool of clones from a base image.
- **NAT & Snapshots**: Seamless networking and instant state rollback for every session.
- **Docker Ready**: The official Docker image includes `libvirt0` runtime dependencies to support remote Libvirt connections (e.g., `qemu+ssh://...`).

To enable, configure the `pool` section in your `cyanide.yaml`:
```yaml
pool:
  enabled: true
  mode: libvirt
  libvirt_uri: "qemu:///system"
  max_vms: 5
```

#### SQLite (Fast Runtime)
YAML serves as the "source code," compiled/cached into **SQLite** (`.compiled.db`) for production:
- Faster loading/decoding than YAML/JSON;
- Smaller footprint, easier caching/distribution;
- More stable high-load performance.

#### Session Flow
The system processes each interaction through a structured **Session Flow**:
-  Incoming event (login/command/payload)
-  State update
-  Profile rules application (YAML/SQLite)
-  Response generation (with realistic timing)
-  Logging + IOC extraction

#### Logs and IOCs
Structured events are captured: IP/session ID, login attempts, commands/payloads, timings, and outcomes. From this, **IOCs** are extracted, attacks classified, and alerts/exported to SOC systems.

---

### Creators 
 
This framework was created by **tanhiowyatt** and **koshanzov**. Our initial collaboration on advanced honeypot prototypes evolved into the current open-source cybersecurity project, focusing on realistic threat simulation, ML-driven attack classification, and seamless SOC integration.

---

### Disclaimer

This software is for educational and research purposes only. Running a framework involves significant risks. The author is not responsible for any damage or misuse.

---

<p align="center">
  <i>Revision: 1.0 - May 2026 - Cyanide Framework</i>
</p>