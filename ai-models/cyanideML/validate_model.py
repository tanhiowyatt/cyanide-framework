import json
import numpy as np
import sys
import os
import collections
from sklearn.metrics import confusion_matrix
import random

# Add project root to path
# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Mock prometheus if missing (for validate script)
try:
    import prometheus_client
except ImportError:
    pass # Managed in metrics.py

# Add ai-models to path for importing cyanideML
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cyanideML.model import HoneypotFilter

def generate_anomalies(n=50):
    """Generates random weird commands that should be anomalous."""
    anomalies = []
    for _ in range(n):
        cmd = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=random.randint(50, 200)))
        anomalies.append({
            "command": cmd,
            "username": "root", 
            "password": "123",
            "dst_port": 9999, # Weird port
            "protocol": "ssh",
            "label": "anomaly"
        })
    return anomalies

def validate():
    print("Loading valid dataset...")
    normal_logs = []
    dataset_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../var/log/cyanide/cyanide_synthetic.json"))
    
    with open(dataset_path, 'r') as f:
        for line in f:
            try:
                l = json.loads(line)
                l['label'] = 'normal'
                normal_logs.append(l)
            except: pass
            
    # Simulate: Train on first 2000 'normal' logs
    train_set = normal_logs[:2000]
    
    # Test on next 500 'normal' logs + 50 'anomalies'
    test_normal = normal_logs[2000:2500]
    test_anomalies = generate_anomalies(n=50)
    
    test_set = test_normal + test_anomalies
    random.shuffle(test_set)
    
    print(f"Training on {len(train_set)} logs...")
    model = HoneypotFilter(n_clusters=20, batch_size=100) # Reduced clusters for demo sensitivity
    
    # Train
    for log in train_set:
        model.process_log(log)
        
    print(f"Testing on {len(test_set)} logs ({len(test_normal)} normal, {len(test_anomalies)} anomalies)...")
    
    y_true = []
    y_pred = []
    
    false_positives = 0 # Normal flagged as anomaly
    false_negatives = 0 # Anomaly flagged as normal
    
    for log in test_set:
        is_anomaly, reason, dist = model.process_log(log)
        
        # Ground Truth
        is_bad = (log['label'] == 'anomaly')
        y_true.append(is_bad)
        y_pred.append(is_anomaly)
        
        if is_bad and not is_anomaly:
            false_negatives += 1
            # print(f"Missed Anomaly: {log['command'][:30]}... Dist: {dist:.4f}")
        
        if not is_bad and is_anomaly:
            false_positives += 1
            # print(f"False Alarm: {log.get('command') or log.get('input')}... Dist: {dist:.4f}")

    # Metrics
    tp = sum(1 for t, p in zip(y_true, y_pred) if t and p)
    tn = sum(1 for t, p in zip(y_true, y_pred) if not t and not p)
    fp = false_positives
    fn = false_negatives
    
    accuracy = (tp + tn) / len(test_set)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    
    print("\n--- Validation Results ---")
    print(f"Accuracy: {accuracy*100:.2f}%")
    print(f"Precision: {precision*100:.2f}%")
    print(f"Recall (Sensitivity): {recall*100:.2f}%")
    print(f"False Positive Rate: {fp/len(test_normal)*100:.2f}%")
    print(f"False Negative Rate: {fn/len(test_anomalies)*100:.2f}%")
    print("-" * 30)
    print(f"TP: {tp}, TN: {tn}, FP: {fp}, FN: {fn}")

if __name__ == "__main__":
    validate()
