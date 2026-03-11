# SSH Service Architecture (`src/cyanide/services/ssh_handler.py`)

Cyanide provides a complete, high-interaction SSH server implementation built upon the asynchronous `asyncssh` library. The integration represents a fully functional OpenSSH-compatible endpoint engineered for forensics, session capturing, and connection interception.

## 1. The SSHServerFactory & Session Lifecycle

The `SSHServerFactory` class dictates how an incoming SSH connection is initially received and authenticated.

### Key Capabilities:
- **Authentication Handlers:** Cyanide supports both `password` and `publickey` authentication.
  - Unlike naive honeypots that blindly accept any credential, Cyanide can optionally parse a `CYANIDE_USERS` list to only permit specific credentials. This weeds out simplistic bots and encourages advanced human attackers to proceed.
  - If a public key is provided natively via the client, Cyanide records the key fingerprint and accepts the payload, allowing it to trace specific threat actors via their unique SSH keypairs across different servers.
- **Connection Logging:** The initial `connection_made` event is trapped. Cyanide extracts the remote client version (e.g. `SSH-2.0-OpenSSH_9.0`) and logs it, identifying the attacker's toolkit before authentication even completes.

## 2. PTY and Session Layer (`CyanideSSHServer`)

Once an attacker passes the `SSHServerFactory` layer, a `CyanideSSHServer` instance is provisioned for their session.

- **PTY (Pseudo-Terminal) Requests:** When the attacker requests a PTY, Cyanide checks the `backend_mode`.
  - In **Emulated** mode, it initializes the `ShellEmulator` bridging strings from the SSH channel into the VFS.
  - In **Proxy** and **Pool** modes, it transparently passes the stream directly to the underlying `TCPProxy` and returns the true remote output.
- **Environment Capturing:** Any `env` variables the attacker attempts to pass over SSH are silently captured and logged as `ssh_env_data`.

## 3. Cryptographic Mimicry & Security Profiling

Cyanide simulates high-security enterprise environments to encourage advanced malware drops.

Through configuration (`CYANIDE_SSH_MACS`, `CYANIDE_SSH_CIPHERS`, `CYANIDE_SSH_KEX_ALGS`), Cyanide limits exactly which cryptographic negotiation algorithms it broadcasts during the handshakes. By broadcasting highly-secure, modern ciphers (e.g., `curve25519-sha256`, `chacha20-poly1305@openssh.com`), Cyanide tricks reconnaissance tools into classifying the honeypot as an up-to-date, heavily fortified target.

This prevents older, noisy botnets from connecting, ensuring that only specialized or heavily motivated adversaries can establish a session.

## 4. Advanced Port Forwarding (Tunnels) Interception

A key differentiator for Cyanide is its rigorous capability to intercept SSH port-forwarding channels (`-L` Local Forwarding, `-R` Remote Forwarding, `-D` Dynamic SOCKS proxy).

When an attacker attempts to establish a tunnel through Cyanide, the `direct_tcpip_requested` and `connection_requested` handler hooks are triggered.

### The Interception Flow:
1. **Request Tracking:** Cyanide captures the `dest_host` and `dest_port` the attacker wishes to tunnel to through the honeypot.
2. **Policy Router Evaluation:** Cyanide evaluates `CYANIDE_SSH_FORWARD_REDIRECT_RULES`.
3. **Redirection (Optional):** If a rule exists (e.g., mapping port `80` to a safe internal sinkhole sandbox), Cyanide transparently alters the `dest_host` and routes the tunnel silently to the safe sandbox, making the attacker believe they successfully breached the internal network.
4. **Denial:** If `CYANIDE_SSH_FORWARDING_ENABLED` is false, Cyanide denies the channel softly, emulating a correct `Administratively Prohibited` firewall response.
