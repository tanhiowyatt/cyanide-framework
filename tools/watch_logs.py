import time
import json
import sys
import os
import configparser
import logging
from prometheus_client import start_http_server

# Add project root to path
sys.path.append(os.getcwd())

# Import the ML Filter
try:
    from ai_models.cyanideML import HoneypotFilter
except ImportError:
    sys.path.append(os.path.join(os.getcwd(), '..'))
    from ai_models.cyanideML import HoneypotFilter

LOG_FILE = "var/log/cyanide/cyanide.json"
CONFIG_FILE = "etc/cyanide.cfg"

def load_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return config

def setup_logger(log_path):
    logger = logging.getLogger("anomalies")
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_path)
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

def follow(file):
    """Generator that yields new lines from a file."""
    file.seek(0, os.SEEK_END)
    while True:
        line = file.readline()
        if not line:
            time.sleep(0.1)
            continue
        yield line

def main():
    config = load_config()
    
    # Check if ML is enabled
    if not config.has_section('ml') or not config.getboolean('ml', 'enabled', fallback=True):
        print("[*] ML Analysis is disabled in cyanide.cfg. Exiting.")
        return

    metrics_port = config.getint('ml', 'metrics_port', fallback=9091)
    anomalies_log_path = config.get('ml', 'anomalies_log', fallback='var/log/cyanide/anomalies.json')

    print(f"[*] Initializing ML Filter...")
    model = HoneypotFilter()
    
    # Setup Prometheus
    print(f"[*] Starting Prometheus Metrics Server on port {metrics_port}...")
    start_http_server(metrics_port)
    
    # Setup File Logging
    print(f"[*] Logging anomalies to {anomalies_log_path}...")
    anomaly_logger = setup_logger(anomalies_log_path)

    if not os.path.exists(LOG_FILE):
        print(f"[!] Log file not found at {LOG_FILE}")
        # Wait for file to appear? Or exit?
        # Let's wait a bit then exit if not found
        time.sleep(2)
        if not os.path.exists(LOG_FILE):
             print(f"[!] Still not found. Please ensure Cyanide is running.")
             return

    print(f"[*] Watching {LOG_FILE} for anomalies...")
    print(f"[*] Press Ctrl+C to stop.")

    try:
        with open(LOG_FILE, "r") as f:
            for line in follow(f):
                try:
                    log_entry = json.loads(line)
                    is_anomaly, reason, distance = model.process_log(log_entry)
                    
                    if is_anomaly:
                        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
                        details = {
                            "timestamp": timestamp,
                            "src_ip": log_entry.get('src_ip', 'unknown'),
                            "reason": reason,
                            "distance": float(distance),
                            "event": log_entry
                        }
                        
                        # Console Alert
                        print(f"\n[!] ANOMALY DETECTED! {reason} | IP: {details['src_ip']}")
                        
                        # File Alert
                        anomaly_logger.info(json.dumps(details))
                        
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"[!] Error processing log: {e}")
    except KeyboardInterrupt:
        print("\n[*] Stopping watcher.")

if __name__ == "__main__":
    main()
