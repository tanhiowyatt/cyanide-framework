#  Networking Documentation

This section explains Cyanide's networking stack, focusing on its protocol handling and protocol-specific proxying.

## Overview
Cyanide facilitates communication between attackers and the honeyport engine via a custom asynchronous networking layer. It supports both emulated direct interaction and specialized MiTM (Man-in-the-Middle) proxying to isolated backends.

## How it Works
Communication is handled via `asyncio` transport layers. For SSH, we utilize `asyncssh` for protocol negotiation, while the **Proxy Layer** intercepts the decrypted stream and allows for real-time traffic modification and credential harvesting.

## Configuration
Network settings (ports, host binding, os_profile) are managed in `configs/app.yaml` under the `server` and `ssh` blocks. For more info, see the **[Configuration Guide](../core/configuration.md)**.

##  Detailed Documents

*   **[Core Networking Architecture](network.md)**: Details on the asynchronous bridge between attacker IPs and virtual services.
*   **[Proxy Dispatch](network.md#2-proxy-dispatch-srccyanidenetworktcpproxypy)**: How TCP streams are transparently forwarded in Proxy/Pool modes.
*   **[Anti-Fingerprinting](network.md#3-defensive-anti-fingerprinting-jitter)**: Implementing randomization to defeat automated scanners.

## See Also
*    **[Framework Services](../services/index.md)**: Individual protocol servers (SSH, Telnet).
*    **[Test Suite](../tests/index.md)**: Network failure and latency injection tests.

---
<p align="center">
  <i>Revision: 1.0 - May 2026 - Cyanide Framework</i>
</p>
