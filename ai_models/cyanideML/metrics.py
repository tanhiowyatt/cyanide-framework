try:
    from prometheus_client import Counter, Histogram
except ImportError:
    # Fallback if library not present
    class MockMetric:
        def labels(self, **kwargs): return self
        def inc(self, amount=1): pass
        def observe(self, amount): pass
        def __init__(self, *args, **kwargs): pass
        
    Counter = MockMetric
    Histogram = MockMetric

# Metrics definition
LOGS_PROCESSED_TOTAL = Counter(
    'honeypot_logs_processed_total', 
    'Total number of logs processed by ML filter',
    ['status'] # 'anomaly' or 'clean'
)

PROCESSING_LATENCY = Histogram(
    'honeypot_processing_latency_seconds',
    'Time taken to process a single log',
    buckets=[0.0005, 0.001, 0.002, 0.005, 0.01, 0.05, 0.1]
)

DISTANCE_SCORE = Histogram(
    'honeypot_distance_score',
    'Distance score of logs from nearest cluster',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0]
)
