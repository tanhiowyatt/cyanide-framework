# Tools and Binaries

## bin/

Executable scripts exposed to the user.

*   **`cyanide`**: The main entry point. supports `start`, `stop`, `status` commands.
*   **`cyanide-replay`**: Replays captured TTY logs (from `var/log/cyanide/tty/`).
    *   Usage: `cyanide-replay var/log/cyanide/tty/ssh_X.X.X.X_sessionID/`
*   **`cyanide-fsctl`**: Utility to inspect or modify the pickled filesystem (`fs.pickle`).
    *   Usage: `cyanide-fsctl --fs path/to/fs.pickle touch /home/admin/newfile`
*   **`cyanide-createfs`**: Script to generate a fresh `fs.pickle` from the default configuration defined in the code.

## tools/

Helper scripts for development and analysis.

*   **`generate_dataset.py`**: Creates synthetic log data for training the ML model.
    *   Generates `var/log/cyanide/cyanide_synthetic.json`.
*   **`watch_logs.py`**: A `tail -f` equivalent that pretty-prints the JSON logs to the console in a readable format.
*   **`dataset_builder.py`**: Tool to merge or Clean existing datasets.

---

# User Instructions

## How to Replay an Attacker Session

When an attacker interacts with the honeypot (via SSH or Telnet), their complete TTY session is compressed and logged. You can watch exactly what they saw and typed like a movie.

1.  **Locate the session log:**
    Check `var/log/cyanide/tty/` in your local project folder (mounted volume).
    ```bash
    ls -l var/log/cyanide/tty/
    # Example: ssh_192.168.1.50_a1b2c3d4/
    ```

2.  **Play the session:**
    You need to run the replay tool *inside* the container, or have Python locally.
    
    *Using Docker (Preferred):*
    ```bash
    # Syntax: docker exec -it <container> ./bin/cyanide-replay <path_inside_container>
    # Note: Inside container, path is /app/var/log/cyanide/tty/...
    
    docker exec -it cyanide_honeypot ./bin/cyanide-replay /app/var/log/cyanide/tty/ssh_192.168.1.50_a1b2c3d4/
    ```

    *   **Controls:** The replay runs in real-time.
    *   **Output:** You will see the attacker's shell prompts, typing mistakes, and command output exactly as it appeared to them.

## How to Modify the Fake Filesystem

Sometimes you want to leave a "honey file" (bait) for attackers to find, like `passwords.txt`.

1.  **Check current filesystem state:**
    ```bash
    docker exec -it cyanide_honeypot ./bin/cyanide-fsctl --fs /app/share/cyanide/fs.pickle list /home/admin
    ```

2.  **Add a bait file:**
    Use `fsctl` inside the container.
    
    ```bash
    docker exec -it cyanide_honeypot ./bin/cyanide-fsctl --fs /app/share/cyanide/fs.pickle touch /home/admin/payroll.csv
    ```

    *Regenerating from code:*
    1. Edit `src/core/fake_filesystem.py` locally.
    2. Rebuild the container to apply code changes:
    ```bash
    docker compose -f docker/docker-compose.yml up --build -d
    # The container startup (main.py) or an entrypoint should generate the FS if missing, 
    # or you can run ./bin/cyanide-createfs inside manually.
    ```

## Advanced: Creating a Custom Filesystem Snapshot

If you want the honeypot to look exactly like a specific server (e.g., a specific release of Ubuntu or a server with installed apps), you can clone a directory structure into a pickle file.

**Warning:** Do not clone your entire root `/` of a production server indiscriminately, as it will copy sensitive files (shadow, keys) into the pickle which might be exposed if the honeypot is compromised.

1.  **Prepare a directory:**
    Create a folder locally with the file structure you want.
    ```bash
    mkdir my_custom_os
    mkdir -p my_custom_os/etc
    echo "Custom OS 1.0" > my_custom_os/etc/issue
    ```

2.  **Generate the snapshot:**
    You need to run this *inside* the container for access to the python libraries, or locally if configured.
    
    ```bash
    # Mount your custom folder into the container temporarily or copy it
    docker cp my_custom_os/ cyanide_honeypot:/tmp/my_template/
    
    # Run the creation tool
    docker exec -it cyanide_honeypot ./bin/cyanide-createfs /tmp/my_template/ --output /app/share/cyanide/fs.pickle
    ```

3.  **Persistence:**
    The default `fs.pickle` in `/app/share/cyanide/` is overwritten. Since this is a volume (usually), it will persist.
    
    To revert to the default fake filesystem, delete the pickle file and restart the container (if the startup script logic regenerates it from defaults).

