import os
import sys

# Add src to path
sys.path.insert(0, os.getcwd())

from cyanide.vfs.engine import FakeFilesystem
from cyanide.vfs.nodes import Directory


def test_nodes():
    fs = FakeFilesystem(os_profile="centos", root_dir="configs/profiles")
    for path in ["/", "/etc", "/bin", "/root", "/sys"]:
        node = fs.get_node(path)
        print(f"Path: {path}")
        print(f"  Node: {node}")
        print(f"  isinstance(Directory): {isinstance(node, Directory)}")
        if isinstance(node, Directory):
            print(f"  Children: {sorted(list(node.children.keys()))}")
        print("-" * 20)


if __name__ == "__main__":
    test_nodes()
