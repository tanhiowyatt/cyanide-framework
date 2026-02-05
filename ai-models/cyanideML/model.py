import numpy as np
from sklearn.cluster import MiniBatchKMeans
import collections
import time
import pickle
from .feature_extractor import FeatureExtractor
from .metrics import LOGS_PROCESSED_TOTAL, PROCESSING_LATENCY, DISTANCE_SCORE

class HoneypotFilter:
    """
    ML-based filter for SSH/Telnet honeypot logs.
    Identifies anomalies (dist > threshold) vs known patterns.
    """
    
    def __init__(self, n_clusters=75, batch_size=100):
        self.feature_extractor = FeatureExtractor()
        
        self.kmeans = MiniBatchKMeans(
            n_clusters=n_clusters,
            batch_size=batch_size,
            random_state=42,
            n_init=3,
            reassignment_ratio=0.01
        )
        
        self.batch_size = batch_size
        self.buffer = [] # Holds vectors for partial_fit
        self.history_distances = collections.deque(maxlen=1000)
        self.threshold = 1.0 # Initial fallback (orthogonal)
        self.is_fitted = False
        self.logs_processed = 0
        
    def _update_threshold(self):
        """
        Recalculate dynamic threshold using IQR rule on history buffer.
        """
        if len(self.history_distances) < 100:
            return
            
        dists = np.array(self.history_distances)
        q1 = np.percentile(dists, 25)
        q3 = np.percentile(dists, 75)
        iqr = q3 - q1
        
        # Q3 + 1.5*IQR is standard outlier fence (was 3*IQR which is too loose)
        new_threshold = q3 + (1.5 * iqr)
        
        # Safety bounds for cosine/euclidean on unit vectors
        # Max distance is sqrt(2) ~= 1.414. Cap at 1.2 to ensure we catch orthogonal vectors.
        self.threshold = max(0.5, min(new_threshold, 1.2))

    def process_log(self, log_entry):
        """
        Main entry point.
        
        Args:
            log_entry (dict): The log to analyze.
            
        Returns:
            tuple: (is_anomaly (bool), reason (str), distance (float))
        """
        start_time = time.time()
        
        # 1. Feature Extraction
        # Handle dynamic port learning
        dst_port = log_entry.get("dst_port", 2222) # Default if missing
        self.feature_extractor.update_port_stats(dst_port)
        
        if self.logs_processed % 1000 == 0:
            self.feature_extractor.refresh_top_ports()
            
        vector = self.feature_extractor.extract(log_entry)
        
        # 2. Inference
        if not self.is_fitted:
            # Cold start: Treat first batch as learning phase, not anomalies
            self.buffer.append(vector)
            if len(self.buffer) >= self.batch_size:
                X = np.vstack(self.buffer)
                self.kmeans.partial_fit(X)
                self.is_fitted = True
                self.buffer = []
            return False, "WARMUP", 0.0
            
        # Get distance to nearest cluster
        # transform returns array of shape (1, n_clusters)
        all_dists = self.kmeans.transform(vector)
        min_dist = np.min(all_dists)
        
        # Update history for thresholding
        self.history_distances.append(min_dist)
        if self.logs_processed % 50 == 0:
            self._update_threshold()
            
        # 3. Anomaly Decision
        is_anomaly = False
        reason = "KNOWN_PATTERN"
        
        if min_dist > self.threshold:
            is_anomaly = True
            reason = f"DISTANCE_EXCEEDED_THRESHOLD ({min_dist:.2f} > {self.threshold:.2f})"
        elif min_dist < (0.3 * self.threshold):
            is_anomaly = False
            reason = "DEEP_CLUSTER_MATCH"

        # Debug occasionally
        if self.logs_processed % 500 == 0:
            print(f"[DEBUG] Log {self.logs_processed}: Dist={min_dist:.4f}, Thr={self.threshold:.4f}, Anomaly={is_anomaly}")

        # Record Metrics
        processing_time = time.time() - start_time
        PROCESSING_LATENCY.observe(processing_time)
        DISTANCE_SCORE.observe(min_dist)
        status = "anomaly" if is_anomaly else "clean"
        LOGS_PROCESSED_TOTAL.labels(status=status).inc()
            
        # 4. Online Learning (Buffer)
        self.buffer.append(vector)
        # Train every 1000 logs to reduce latency impact
        if len(self.buffer) >= 1000: 
            X = np.vstack(self.buffer)
            self.kmeans.partial_fit(X)
            self.buffer = []
            
        self.logs_processed += 1
        
        return is_anomaly, reason, float(min_dist)

    def save(self, path="model.pkl"):
        """Saves current state."""
        with open(path, "wb") as f:
            pickle.dump(self, f)
            
    @staticmethod
    def load(path="model.pkl"):
        with open(path, "rb") as f:
            return pickle.load(f)
