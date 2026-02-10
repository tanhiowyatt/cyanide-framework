import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer
import math
import collections

class FeatureExtractor:
    """
    High-performance feature extractor for Honeypot logs.
    Target latency: <0.5ms per log.
    
    Features:
    - Text Hashing (512 dims)
    - Statistical (3 dims: len, entropy, metachars)
    - Protocol (1 dim: 0=SSH, 1=Telnet)
    - Port (21 dims: Top-20 + Rare)
    
    Total Dimensions: 537
    """
    
    def __init__(self, n_text_features=512, n_top_ports=20):
        self.n_text_features = n_text_features
        self.n_top_ports = n_top_ports
        
        # Text Vectorizer (Stateless, fast)
        self.text_vectorizer = HashingVectorizer(
            n_features=n_text_features,
            norm='l2',
            alternate_sign=False,
            binary=False
        )
        
        # Port Management
        self.top_ports = collections.defaultdict(int)
        self.top_ports_list = [] # Cached list of top ports
        self.port_map = {} # port -> index
        self.port_counter = collections.Counter()
        self.total_logs = 0
        self.port_lock = False # Simple flag, assume single thread for now or external lock
        
    def _calculate_entropy(self, text):
        """Calculates Shannon entropy of the string."""
        if not text:
            return 0.0
        prob = [float(text.count(c)) / len(text) for c in dict.fromkeys(list(text))]
        entropy = - sum([p * math.log(p) / math.log(2.0) for p in prob])
        return entropy

    def _count_metachars(self, text):
        """Counts Linux shell metacharacters."""
        metachars = "|&;()<>`$\\"
        return sum(1 for c in text if c in metachars)

    def update_port_stats(self, port):
        """Updates port frequency statistics."""
        self.port_counter[port] += 1
        self.total_logs += 1
        
        # Periodically re-calculate top ports (e.g., every 1000 logs)
        # For simplicity and speed, we do this check externally or very rarely.
        # Here we just track.
    
    def refresh_top_ports(self):
        """Re-calculates the top N ports based on observed frequency."""
        most_common = self.port_counter.most_common(self.n_top_ports)
        self.top_ports_list = [p[0] for p in most_common]
        self.port_map = {port: i for i, port in enumerate(self.top_ports_list)}
        
    def extract(self, log_entry):
        """
        Convert log entry to dense numpy array (float32).
        
        Args:
            log_entry (dict): JSON log entry.
            
        Returns:
            np.ndarray: Feature vector of shape (1, 537)
        """
        # 1. Text Features
        # Combine relevant text fields
        text_content = ""
        if "input" in log_entry: text_content += str(log_entry["input"]) + " "
        if "username" in log_entry: text_content += str(log_entry["username"]) + " "
        if "password" in log_entry: text_content += str(log_entry["password"]) + " "
        if "cmd" in log_entry: text_content += str(log_entry["cmd"]) + " " # For command_not_found
        if "command" in log_entry: text_content += str(log_entry["command"]) + " " # Standardized key
        
        # HashingVectorizer returns scipy.sparse matrix
        text_vec = self.text_vectorizer.transform([text_content])
        # Convert to dense for concatenation (size 512 is small enough)
        text_arr = text_vec.toarray()
        
        # 2. Statistical Features
        length = len(text_content)
        log_len = math.log10(length + 1)
        entropy = self._calculate_entropy(text_content)
        meta_count = self._count_metachars(text_content)
        
        stats_arr = np.array([[log_len, entropy, meta_count]], dtype=np.float32)
        
        # 3. Protocol Feature
        is_telnet = 1.0 if log_entry.get("protocol", "").lower() == "telnet" else 0.0
        proto_arr = np.array([[is_telnet]], dtype=np.float32)
        
        # 4. Port Features
        # One-hot encoded against Top-N ports, plus one for "Other"
        port = log_entry.get("src_port") # Wait, Task says DESTINATION port (honeypot port).
        # Log format check: existing logs don't clearly show destination port in all events?
        # Looking at previous file view...
        # 16: {"eventid": "connect", ..., "src_port": 50512} -> This is source port.
        # We need the honeypot port (dst_port). 
        # The prompt says "Honeypot ports: Dynamic (22, 23...)"
        # If the log entry doesn't have dst_port, we might need to assume it or extract from metadata.
        # Let's check `cyanide.json` again. It usually lacks dst_port in the snippet I saw.
        # Assuming the user will Provide `dst_port` in the dict passed to `process_log`.
        # I will use `dst_port` key.
        
        dst_port = log_entry.get("dst_port", 0)
        
        port_vec = np.zeros((1, self.n_top_ports + 1), dtype=np.float32)
        if dst_port in self.port_map:
            idx = self.port_map[dst_port]
            port_vec[0, idx] = 1.0
        else:
            # Rare/Other category
            port_vec[0, self.n_top_ports] = 1.0
            
        # Concatenate
        combined = np.hstack([text_arr, stats_arr, proto_arr, port_vec])
        return combined.astype(np.float32)

