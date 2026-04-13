# 🔧 Project Tooling & Operations

This section is dedicated to the scripts in `scripts/management/` and the workflows employed by developers and maintainers of the Cyanide platform.

## Overview
Running a production honeypot requires robust monitoring and forensic toolsets. Cyanide provides built-in utilities for real-time traffic visualization and replaying attacker session data exactly as it was typed.

## How it Works
Cyanide's tools interact directly with the log files (`cyanide-fs.json`) and TTY capture files using Python-based parsers. The `cyanide stats` command provides immediate situational awareness, while `scriptreplay` is used for in-depth forensic investigation.

## Configuration
Diagnostic tools usually rely on default log paths (`var/log/cyanide/`). If you've modified these in `app.yaml`, make sure to pass the custom paths to the tools via CLI flags or by updating their internal constants.

## 📑 Detailed Documents

*   **[Operations Guide](operations.md)**: Comprehensive manual on system monitoring, logging, and TTY playback.
*   **[Output Integrations](../../user-reference/Integrations.md)**: Details on the asynchronous output system, supported SIEMs, and custom plugin development.
*   **[Forensics & Malware Handling](operations.md#forensics-malware-handling)**: How captured artifacts are quarantined and analyzed.
*   **[Session Playback](operations.md#2-session-replay)**: Utilizing `scriptreplay` for granular session investigation.

## See Also
*   🧪 **[Tests Documentation](../tests/index.md)**: Development-centric tests for each tool.
*   🏢 **[Management Architecture](../core/architecture.md)**: How core tools interface with the main server process.

---
<p align="center">
  <i>Revision: 1.0 • April 2026 • Cyanide Honeypot</i>
</p>
