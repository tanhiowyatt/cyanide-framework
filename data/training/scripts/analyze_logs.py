#!/usr/bin/env python3
import json
import os

def analyze_logs(log_path):
    if not os.path.exists(log_path):
        print(f"Log file not found: {log_path}")
        return

    total = 0
    anomalies_old = 0
    anomalies_new = 0
    t1 = 0.0040
    t2 = 0.0125
    
    suspected_fp = []

    with open(log_path, 'r') as f:
        for line in f:
            try:
                data = json.loads(line)
                total += 1
                dist = data.get('distance', 0)
                cmd = data.get('command', '')
                
                if dist > t1:
                    anomalies_old += 1
                    # If it's between t1 and t2, it's a "recovered" false positive
                    if dist <= t2:
                        suspected_fp.append(cmd)
                
                if dist > t2:
                    anomalies_new += 1
            except:
                continue

    if total == 0:
        print("No logs found to analyze.")
        return

    print("="*40)
    print("      LOG ANOMALY ANALYSIS      ")
    print("="*40)
    print(f"Total Log Entries: {total}")
    print(f"Anomalies at Threshold 0.0040: {anomalies_old} ({anomalies_old/total*100:.2f}%)")
    print(f"Anomalies at Threshold 0.0125: {anomalies_new} ({anomalies_new/total*100:.2f}%)")
    print("-" * 40)
    print(f"Reduction in 'Anomalies' (False Positives): {anomalies_old - anomalies_new}")
    print(f"New Anomaly Rate: {anomalies_new/total*100:.2f}%")
    
    if suspected_fp:
        print("\nExamples of Resolved False Positives:")
        # Show unique examples
        unique_fps = list(set(suspected_fp))
        for item in unique_fps[:10]:
            print(f" - {item}")
    print("="*40)

if __name__ == "__main__":
    analyze_logs("var/log/cyanide/cyanideML-log.json")
