# Core Service Documentation

The Core Engine of **Cyanide** is responsible for the overall lifecycle management of the honeypot, including configuration parsing, event orchestration, and the main server loop.

## Overview
Cyanide's core handles the transition between incoming network connections and the internal emulation logic. It acts as the "brain" that initializes services (SSH, Telnet), manages global security settings, and routes events to the analytics engine.

## How it Works
The core utilizes a central `CyanideServer` class built on top of `asyncio`. It starts multiple protocol-specific listeners and coordinates access to shared resources like the Virtual Filesystem (VFS) and the Statistics Manager.

##  Detailed Documents

*   **[Core Overview](core.md)**: Deep dive into the central `CyanideServer`, its event loop, and major system components.
*   **[Caching Engine](caching.md)**: Performance optimization tactics for static file profiles.

## See Also
*    **[VFS Documentation](../vfs/index.md)**: How the core interacts with the virtual filesystem.
*    **[ML & Analytics](../ml-analytics/index.md)**: Threat detection logic.

---
<p align="center">
  <i>Revision: 1.0  April 2026  Cyanide Honeypot</i>
</p>
