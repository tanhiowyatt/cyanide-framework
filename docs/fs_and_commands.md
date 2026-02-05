# Filesystem and Commands Documentation

## src/cyanide/fs

Utilities for managing the persistence of the Fake Filesystem.

### `pickle.py`
Methods for saving and loading the filesystem state.
*   `save_fs(fs_root, path)`: Serializes the filesystem tree to a pickle file.
*   `load_fs(path)`: Deserializes the filesystem.

---

## src/commands

This directory contains the implementations of individual shell commands. Each file typically corresponds to one or more commands.

### `base.py`
**Class:** `Command/Executable`
Base class for all commands.
*   `execute(args, input_data)`: Must be implemented by subclasses. `input_data` contains stdin (from pipes).

### `file_ops.py`
Handles file manipulation.
*   **Classes:**
    *   `TouchCommand`: Updates timestamps or creates empty files.
    *   `MkdirCommand`: Creates directories (supports `-p`).
    *   `RmCommand`: Removes files (supports `-rf`).
    *   `RmdirCommand`: Removes empty directories.
    *   `CpCommand`: Copies files.
    *   `MvCommand`: Moves/Renames files.

### `ls.py` (`LsCommand`)
List directory contents. Supports flags like `-l`, `-a`, `-la`. Formats output to look like real Linux `ls`.

### `cd.py` (`CdCommand`)
Changes the current working directory of the `ShellEmulator`. Handles `..`, `.`, `~`, and `-`.

### `cat.py` (`CatCommand`)
Outputs file content to stdout.

### `net_ops.py` / `misc.py`
*   `WgetCommand` / `CurlCommand`: Simulates downloading files. *Critical for malware collection.* Saves files to the filesystem and triggers quarantine.

### Adding a New Command
1. Create a new file in `src/commands/` (e.g., `mycmd.py`).
2. Inherit from `Command`.
3. Implement `async def execute(self, args, input_data)`.
4. Register the command in `src/commands/__init__.py` inside `COMMAND_MAP`.
