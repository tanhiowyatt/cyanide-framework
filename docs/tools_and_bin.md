# Tools and Scripts

## scripts/

Executable scripts exposed to the user.

*   **`cyanide`**: The main entry point. supports `start`, `stop`, `status`, `restart` commands.
*   **`cyanide-replay`**: Replays captured TTY logs (from `var/log/cyanide/tty/`).
    *   Usage: `./scripts/cyanide-replay var/log/cyanide/tty/<session_dir>/`
*   **`cyanide-clean`**: Clean up old logs and quarantined files.

## Root Scripts

Helper scripts for development and analysis.

*   **`generate_mass_fs.py`**: Creates a massive `fs.yaml` for testing.
*   **`generate_profiles.py`**: Generates OS-specific YAML templates in `config/fs-config/`.

---

# User Instructions

## How to Replay an Attacker Session

When an attacker interacts with the honeypot (via SSH or Telnet), their complete TTY session is logged. You can watch exactly what they saw and typed.

1.  **Locate the session log:**
    Check `var/log/cyanide/tty/` in your local project folder (mounted volume).
    ```bash
    ls -l var/log/cyanide/tty/
    ```

2.  **Play the session:**
    Run the replay tool from the root of the project:
    
    ```bash
    ./scripts/cyanide-replay var/log/cyanide/tty/ssh_X.X.X.X_sessionID/
    ```

## How to Modify the Fake Filesystem

Edit `config/fs-config/fs.yaml` directly:

```bash
# On host machine:
nano config/fs-config/fs.yaml

# Add a honey file:
# - name: confidential.txt
#   type: file
#   perm: "-rw-------"
#   content: |
#     API_KEY=sk-1...

# Restart container:
docker compose restart
```

**That's it!** No special tools needed.

