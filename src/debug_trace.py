import os
import sys

# Add src to path
sys.path.insert(0, os.getcwd())

from cyanide.vfs.engine import FakeFilesystem


def trace_list_dir(path):
    print(f"--- TRACING list_dir({path}) ---")
    fs = FakeFilesystem(os_profile="centos", root_dir="configs/profiles")

    prefix = path.rstrip("/") + "/"
    print(f"Prefix: '{prefix}'")

    all_paths = (
        list(fs.dynamic_files.keys())
        + list(fs.static_manifest.keys())
        + list(fs.memory_overlay.keys())
    )

    print(f"Total paths in all_paths: {len(all_paths)}")

    hits = [p for p in all_paths if p.startswith(prefix)]
    print(f"Found {len(hits)} hits starting with prefix.")

    contents = set()
    for p in hits:
        if p == path:
            continue  # Skip itself if matches prefix?
        # No, p.startswith(prefix) won't match /etc if prefix is /etc/

        rel = p[len(prefix) :].split("/")[0]
        if rel:
            print(f"  Path: {p} -> Rel: {rel}")
            contents.add(rel)
        else:
            print(f"  Path: {p} -> Rel EMPTY!")

    print(f"Final sorted contents: {sorted(list(contents))}")


if __name__ == "__main__":
    trace_list_dir("/")
    print("\n")
    trace_list_dir("/etc")
