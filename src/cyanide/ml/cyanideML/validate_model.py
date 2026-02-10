import json
import sys
import os
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
    print("Loading production dataset...")
    normal_logs = []
    dataset_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../var/log/cyanide/cyanide-log.json"))
    
    if not os.path.exists(dataset_path):
        print(f"[!] Log file not found at {dataset_path}")
        return

    with open(dataset_path, 'r') as f:
        for line in f:
            try:
                l = json.loads(line)
                # Assume prod logs are 'normal' for training, or we don't know label
                # In unsupervised, we assume majority is normal.
                l['label'] = 'unknown' 
                normal_logs.append(l)
            except: pass
            
    # Use 80/20 split for train/test from available logs
    split_idx = int(len(normal_logs) * 0.8)
    train_set = normal_logs[:split_idx]
    
    # Test set could include anomalies if we want to verify detection capability
    # or just validation on unseen prod logs.
    # User said "work on prod logs", likely meaning "train/validate using real data".
    test_normal = normal_logs[split_idx:]
    test_anomalies = generate_anomalies(n=50) # Keep anomalies to verify we still catch them?
    
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
    
    # Output log file
    output_log_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../var/log/cyanide/cyanideML-log.json"))
    print(f"Writing detailed results to {output_log_path}...")
    
    with open(output_log_path, 'w') as out_f:
        for log in test_set:
            is_anomaly, reason, dist = model.process_log(log)
            
            # Ground Truth
            is_bad = (log['label'] == 'anomaly')
            y_true.append(is_bad)
            y_pred.append(is_anomaly)
            
            # Log result
            result_entry = {
                "timestamp": log.get("timestamp", ""),
                "session_id": log.get("session_id", ""),
                "ml_verdict": "anomaly" if is_anomaly else "clean",
                "ml_distance": dist,
                "ml_reason": reason,
                "ground_truth": "anomaly" if is_bad else "clean",
                "original_event": log
            }
            out_f.write(json.dumps(result_entry) + "\n")
            
            if is_bad and not is_anomaly:
                false_negatives += 1
            
            if not is_bad and is_anomaly:
                false_positives += 1

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
    print(f"TP: {tp}, TN: {tn}, FP: {false_positives}, FN: {false_negatives}")
    
    # Auto-Rotation Policy
    # If accuracy > 90% and recall > 40%, update the production model
    if accuracy > 0.90 and recall > 0.40:
        print("\n[*] Model performance meets production criteria.")
        prod_model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "cyanideML.pkl"))
        print(f"[*] Updating production model at {prod_model_path}...")
        model.save(prod_model_path)
        print("[+] Production model updated successfully.")
    else:
        print("\n[!] Model performance below threshold. Keeping existing production model.")

if __name__ == "__main__":
    validate()
