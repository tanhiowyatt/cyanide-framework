# 📁 Virtual Filesystem (VFS) Documentation

The **Virtual Filesystem** layer provides a convincing Linux environment for the attacker. It manages dynamic file generation, memory overlays, and per-session file state mutations.

## Overview
Instead of exposing the host system's disk, Cyanide uses a purely in-memory filesystem representation. This allows for total isolation while still providing the attacker with a rich, interactive environment (files, directories, pipes).

## How it Works
The VFS resolves all attacker requests to `Node` objects. Changes are stored in a session-specific **memory overlay**, meaning an attacker can "delete" `/bin/ls` or "create" a folder without affecting the base installation or other concurrent sessions.

## Configuration
FileSystem structure is defined via **OS Profiles** in `configs/profiles/`. These YAML files specify the base file list, permissions, and initial content. Dynamic files (like `/proc/cpuinfo`) use custom providers.

## 📑 Detailed Documents

*   **[VFS Architecture](vfs.md)**: Details on the engine, proxy nodes, and profile-based OS manifests.
*   **[Shell Emulator Architecture](shell_emulator.md)**: Details on the custom AST parser, logic gates, and command dispatching.
*   **[Caching Strategy](../core/caching.md)**: Performance optimizations for high-throughput I/O scenarios.
*   **[Core Engine](vfs.md)**: Details on file resolution layers, memory overlays, and Jinja2 templating.
*   **[Dynamic Providers](vfs.md#3-dynamic-providers-srccyanidevfsdynamicpy)**: How paths like `/proc/uptime` are realistically emulated.
*   **[Shell Emulator](shell_emulator.md)**: Deep dive into the asynchronous command processor.
*   **[Command Implementation](vfs.md#5-command-implementation-srccyanidevfscommands)**: How `awk`, `cat`, and `ping` are natively implemented for speed.
*   **[Profiles Guide](profiles_guide.md)**: Reference for creating custom OS personas (Ubuntu, CentOS).

## See Also
*   🏛️ **[Core Architecture](../core/core.md#system-overview)**: The high-level service orchestration.
*   🛠️ **[Honeypot Services](../services/index.md)**: How SSH/Telnet sessions utilize the VFS.

---
<p align="center">
  <i>Revision: 1.0 • April 2026 • Cyanide Honeypot</i>
</p>
