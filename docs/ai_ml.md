# AI and Machine Learning Documentation

Cyanide uses a dedicated ML module (`cyanideML`) to filter traffic, detect anomalies, and benchmark performance.

## ai-models/cyanideML

### `model.py`
**Class:** `HoneypotFilter`
The main ML model wrapper.
*   **Parameters:** `n_clusters`, `batch_size`.
*   **Logic:** Uses online K-Means clustering (MiniBatchKMeans) to learn "normal" traffic patterns.
*   **Functions:**
    *   `process_log(log_entry)`: Returns `(is_anomaly, reason, distance)`.
    *   `_update_threshold()`: Dynamically adjusts the anomaly threshold using statistical analysis (IQR) of recent distances.

### `feature_extractor.py`
**Class:** `FeatureExtractor`
Converts raw log entries into numerical feature vectors.
*   **Features:**
    *   Text Hashing (HashingVectorizer on command/username/input).
    *   Port usage (One-hot encoding of top ports).
    *   Entropy analysis (Shannon entropy of strings).
    *   Shell metacharacter counts.

### `validate_model.py`
Basic validation script.
*   **Function:** `validate()`
*   Runs a test against `var/log/cyanide/cyanide_synthetic.json` (if available) to calculate Accuracy, Precision, Recall, and F1 Score by mixing normal logs with generated random anomalies.

### `validate_advanced.py`
Advanced validation scenarios.
*   Generates complex attack patterns (SQLi, obfuscated shell commands, reverse shells).
*   Tests the model's ability to distinguish subtle attacks from normal administrative behavior.

### `benchmark.py`
Performance testing script.
*   Measures latency per log (Target < 1ms).
*   Tracks memory usage and throughput.
