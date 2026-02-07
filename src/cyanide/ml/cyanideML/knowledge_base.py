import json
import logging
import re
from pathlib import Path
import random
import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

class KnowledgeBase:
    """
    Indexed Knowledge Base for MITRE ATT&CK and CVE data using TF-IDF.
    """
    def __init__(self, data_path: Path = None):
        self.data_path = data_path
        self.entries = [] # List of message lists
        self.vectorizer = None
        self.tfidf_matrix = None
        
    def build(self):
        """Indexes the data from the provided path using TF-IDF."""
        if not self.data_path:
            print("[!] No data path provided for building KB.")
            return

        print(f"[*] Building Knowledge Base from {self.data_path.resolve()}")
        jsonl_files = list(self.data_path.glob("**/*.jsonl"))
        print(f"[*] Found {len(jsonl_files)} .jsonl files.")
        
        corpus = []
        self.entries = []
        
        for jf in jsonl_files:
            print(f"[*] Processing {jf}...")
            try:
                with open(jf, 'r') as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            if "question" in entry and "answer" in entry:
                                # MITRE dataset format
                                content = f"Question: {entry['question']}\nAnswer: {entry['answer']}"
                                corpus.append(content)
                                self.entries.append({
                                    "source": "MITRE",
                                    "content": content,
                                    "raw": entry,
                                    "id": entry.get("id", ""),
                                    "name": entry.get("name", ""),
                                    "description": entry.get("answer", "")
                                })
                            elif "messages" in entry:
                                # ShareGPT/OpenAI format
                                content = " ".join([m.get("content", "") for m in entry["messages"]])
                                corpus.append(content)
                                self.entries.append({
                                    "source": "General",
                                    "content": content,
                                    "raw": entry["messages"]
                                })
                            elif "instruction" in entry and "output" in entry:
                                # Alpaca format
                                content = f"{entry['instruction']} {entry.get('input', '')} {entry['output']}"
                                corpus.append(content)
                                
                                # Heuristic source tagging
                                source = "General"
                                if "ATT&CK" in content or "tactic" in content.lower() or "mitre" in content.lower():
                                    source = "MITRE"
                                elif "CVE-" in content:
                                    source = "CVE"
                                    
                                # Extract structured fields for MITRE
                                mitre_id = ""
                                mitre_name = ""
                                mitre_desc = ""
                                if source == "MITRE":
                                    id_match = re.search(r'([T][A]?\d{4}(?:\.\d{3})?)', content)
                                    name_match = re.search(r'«([^»]+)»', content)
                                    mitre_id = id_match.group(1) if id_match else ""
                                    mitre_name = name_match.group(1) if name_match else ""
                                    mitre_desc = entry.get('output', '')
                                    
                                self.entries.append({
                                    "source": source,
                                    "content": content,
                                    "raw": entry,
                                    "id": mitre_id,
                                    "name": mitre_name,
                                    "description": mitre_desc
                                })
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                print(f"[!] Error reading KB file {jf}: {e}")
                
        print(f"[*] Indexed {len(self.entries)} entries. Calculating TF-IDF...")
        
        # Limit features to manageable size for memory efficiency
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=50000)
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
        
        print(f"[*] TF-IDF Matrix shape: {self.tfidf_matrix.shape}")
        
    def search(self, query, top_k=50):
        """
        Search for relevant entries based on query using Cosine Similarity.
        Returns a list of messages (or list of lists if top_k > 1).
        """
        if self.vectorizer is None or self.tfidf_matrix is None:
            return None
            
        # Transform query
        query_vec = self.vectorizer.transform([query])
        
        # Calculate cosine similarity (linear_kernel is faster for sparse matrices)
        cosine_similarities = linear_kernel(query_vec, self.tfidf_matrix).flatten()
        
        # Get top_k indices
        related_docs_indices = cosine_similarities.argsort()[:-top_k-1:-1]
        
        mitre_tactic = None
        mitre_technique = None
        cve_match = None
        
        for i in related_docs_indices:
            if cosine_similarities[i] > 0.03:
                entry = self.entries[i].copy()
                entry["score"] = float(cosine_similarities[i])
                
                source = entry.get("source", "General")
                if source == "MITRE":
                    mid = entry.get("id", "")
                    if mid.startswith("TA") and not mitre_tactic:
                        mitre_tactic = entry
                    elif mid.startswith("T") and not mid.startswith("TA") and not mitre_technique:
                        mitre_technique = entry
                elif (source == "General" or "CVE" in entry.get("content", "")) and not cve_match:
                    cve_match = entry
                        
                if mitre_tactic and mitre_technique and cve_match:
                    break
                    
        results = []
        if cve_match: results.append(cve_match)
        if mitre_tactic: results.append(mitre_tactic)
        if mitre_technique: results.append(mitre_technique)
            
        if not results:
            return None
            
        return results # Return list of matches

    def correlate(self, anomaly_description):
        """
        Finds a MITRE technique related to the anomaly.
        """
        return self.search(anomaly_description)
        
    def save(self, path):
        with open(path, 'wb') as f:
            pickle.dump({
                'entries': self.entries,
                'vectorizer': self.vectorizer,
                'tfidf_matrix': self.tfidf_matrix
            }, f)
            
    def load(self, path):
        with open(path, 'rb') as f:
            data = pickle.load(f)
            self.entries = data['entries']
            self.vectorizer = data['vectorizer']
            self.tfidf_matrix = data['tfidf_matrix']
