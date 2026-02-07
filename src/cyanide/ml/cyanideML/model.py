import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_squared_error
import collections
import time
import pickle
from .feature_extractor import FeatureExtractor
from .metrics import LOGS_PROCESSED_TOTAL, PROCESSING_LATENCY, DISTANCE_SCORE

class HoneypotFilter:
    """
    ML-based filter for SSH/Telnet honeypot logs using an Autoencoder.
    Identifies anomalies (Reconstruction Error > threshold) vs known patterns.
    """
    
    def __init__(self, batch_size=200, online_learning=True):
        self.feature_extractor = FeatureExtractor()
        
        # Autoencoder Architecture
        # Input (537) -> 256 -> 64 (Bottleneck) -> 256 -> Output (537)
        self.model = MLPRegressor(
            hidden_layer_sizes=(256, 64, 256),
            activation='relu',
            solver='adam',
            alpha=0.0001,
            batch_size=batch_size,
            learning_rate='adaptive',
            learning_rate_init=0.001,
            max_iter=1, # For partial_fit
            warm_start=True, # Keep learning
            random_state=42
        )
        
        self.batch_size = batch_size
        self.buffer = [] # Holds vectors for partial_fit
        self.history_errors = collections.deque(maxlen=2000)
        self.threshold = 0.5 # Initial threshold (will adapt)
        self.is_fitted = False
        self.logs_processed = 0
        self.online_learning = online_learning
        
    def _update_threshold(self):
        """
        Recalculate dynamic threshold using Mean + 3*StdDev of history errors.
        """
        if len(self.history_errors) < 100:
            return
            
        errors = np.array(self.history_errors)
        mean_err = np.mean(errors)
        std_err = np.std(errors)
        
        # 3-sigma rule for simpler/robust outlier detection in error distribution
        new_threshold = mean_err + (3 * std_err)
        
        # Safety bounds
        self.threshold = max(0.0125, min(new_threshold, 5.0))

    def process_log(self, log_entry):
        """
        Main entry point.
        """
        start_time = time.time()
        
        # 1. Feature Extraction
        dst_port = log_entry.get("dst_port", 2222)
        self.feature_extractor.update_port_stats(dst_port)
        
        if self.logs_processed % 1000 == 0:
            self.feature_extractor.refresh_top_ports()
            
        vector = self.feature_extractor.extract(log_entry)
        
        # 2. Inference (Reconstruction)
        if not self.is_fitted:
            # Cold start
            if self.online_learning:
                self.buffer.append(vector)
                if len(self.buffer) >= self.batch_size:
                    X = np.vstack(self.buffer)
                    # Autoencoder targets itself (X -> X)
                    self.model.partial_fit(X, X)
                    self.buffer = []
                    self.is_fitted = True
            return False, "Cold Start", 0.0
            
        # Predict reconstruction
        reconstructed = self.model.predict(vector)
        # Calculate MSE/Reconstruction Error
        reconstruction_error = mean_squared_error(vector, reconstructed)
        
        # Update metrics
        self.history_errors.append(reconstruction_error)
        if self.logs_processed % 50 == 0:
            self._update_threshold()
            
        is_anomaly = reconstruction_error > self.threshold
        reason = f"Error {reconstruction_error:.4f} > Threshold {self.threshold:.4f}" if is_anomaly else "Known Pattern"

        # Record Metrics
        processing_time = time.time() - start_time
        PROCESSING_LATENCY.observe(processing_time)
        DISTANCE_SCORE.observe(reconstruction_error) # Using DISTANCE_SCORE for error
        status = "anomaly" if is_anomaly else "clean"
        LOGS_PROCESSED_TOTAL.labels(status=status).inc()
            
        # 3. Online Learning (Buffer)
        if self.online_learning:
            self.buffer.append(vector)
            if len(self.buffer) >= self.batch_size: 
                X = np.vstack(self.buffer)
                self.model.partial_fit(X, X)
                self.buffer = []
            
        self.logs_processed += 1
        
        return is_anomaly, reason, float(reconstruction_error)

    def fit_offline(self, log_iterator):
        """
        Train the model offline using a generator of log entries.
        """
        print(f"[*] Starting offline Autoencoder training (batch={self.batch_size})...")
        batch = []
        count = 0
        epoch_errors = []
        
        for log in log_iterator:
            dst_port = log.get("dst_port", 2222)
            self.feature_extractor.update_port_stats(dst_port)
            
            if count % 1000 == 0:
                self.feature_extractor.refresh_top_ports()
                
            vector = self.feature_extractor.extract(log)
            batch.append(vector)
            count += 1
            
            if len(batch) >= self.batch_size:
                X = np.vstack(batch)
                self.model.partial_fit(X, X)
                
                # Monitor error occasionally
                if count % (self.batch_size * 10) == 0:
                    pred = self.model.predict(X)
                    err = mean_squared_error(X, pred)
                    epoch_errors.append(err)
                    
                batch = []
                self.is_fitted = True
                
        # Process remaining
        if batch:
            X = np.vstack(batch)
            self.model.partial_fit(X, X)
            self.is_fitted = True
            
        avg_err = np.mean(epoch_errors) if epoch_errors else 0.0
        print(f"[*] Offline training complete. Logs: {count}. Final Avg Error: {avg_err:.6f}")
        
        # Initialize threshold based on last batch
        self.history_errors.clear()
        self.threshold = max(0.1, avg_err * 3) 

    def save(self, path="cyanideML.pkl"):
        """Saves current state."""
        with open(path, "wb") as f:
            pickle.dump({
                'model': self.model,
                'feature_extractor': self.feature_extractor,
                'threshold': self.threshold,
                'history': self.history_errors,
                'is_fitted': self.is_fitted,
                'logs_processed': self.logs_processed
            }, f)
        print(f"[*] Model saved to {path}")
            
    @staticmethod
    def load(path="cyanideML.pkl"):
        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
            
            instance = HoneypotFilter()
            instance.model = data['model']
            instance.feature_extractor = data['feature_extractor']
            instance.threshold = data.get('threshold', 0.5)
            instance.history_errors = data.get('history', instance.history_errors)
            instance.is_fitted = data.get('is_fitted', False)
            instance.logs_processed = data.get('logs_processed', 0)
            print(f"[*] Autoencoder Model loaded from {path}")
            return instance
        except Exception as e:
            print(f"[!] Failed to load model: {e}")
            # Return fresh instance if fail, or None? 
            # Better to return fresh for resilience but log error
            return HoneypotFilter()
