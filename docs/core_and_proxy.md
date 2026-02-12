# Core Engine and Network Proxy Documentation

This section covers the core logic of the honeypot, located in `src/core` and `src/proxy`.

## src/core

The `src/core` directory contains the orchestration logic for the honeypot.

### `server.py`
**Class:** `HoneypotServer`
The main event loop and service orchestrator.
*   **Functions:**
    *   `start()`: Initializes SSH, Telnet, and Metrics servers. Handles `backend_mode` selection (emulated/proxy/pool).
    *   `handle_telnet(reader, writer)`: Handles incoming Telnet connections, manages sessions, and connects the `ShellEmulator`.
    *   `_analyze_command(cmd, ...)`: Passes commands to the ML filter for anomaly detection.
    *   `save_quarantine_file(...)`: Saves downloaded malware to the quarantine directory with quota checks.

### `fake_filesystem.py`
**Class:** `FakeFilesystem`
Simulates a Linux filesystem structure in memory (loaded from YAML).
*   **Functions:**
    *   `mkfile(path, content, ...)`: Creates a fake file.
    *   `mkdir_p(path, ...)`: Creates a fake directory recursively.
    *   `remove(path)`: Deletes a file or directory (supports recursive deletion).
    *   `get_content(path)`: Retrieves content of a file, triggering audit callbacks (honeytokens).

### `shell_emulator.py`
**Class:** `ShellEmulator`
Parses and executes command lines input by the attacker.
*   **Functions:**
    *   `execute(command_line)`: Parses chains (`&&`, `||`, `;`), pipes (`|`), and redirections (`>`, `>>`).
    *   `_register_commands()`: Loads available commands from the `commands` registry.

### `vm_pool.py`
**Class:** `VMPool`
Manages a pool of external backend targets (e.g., QEMU VMs).
*   **Functions:**
    *   `get_target()`: Returns a `(host, port)` tuple from the configured pool strategy (currently random).

### `sftp.py`
**Class:** `CyanideSFTPServer`
Handles SFTP file transfers, saving uploaded files directly to quarantine.

### `vt_scanner.py`
**Class:** `VTScanner`
Asynchronously scans intercepted files using the VirusTotal API.

---

## src/proxy

The `src/proxy` directory functionality for relaying traffic to real servers or other honey-tokens.

### `ssh_proxy.py`
**Class:** `HoneypotSSHServer` (Man-in-the-Middle)
*   Intercepts SSH connections.
*   Logs credentials and commands.
*   Forwards decrypted traffic to a backend server.

### `tcp_proxy.py`
**Class:** `TCPProxy`
Generic TCP forwarder (used for SMTP, Pure SSH/Telnet proxying).
*   **Functions:**
    *   `start()`: Starts the listening server.
    *   `handle_client(...)`: Accepts connection, connects to target (via `VMPool` or static config).
    *   `forward(...)`: Pipes data between client and target, logging payloads (first 100 bytes hex) for analysis.
