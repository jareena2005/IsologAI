from prometheus_client import Counter, Gauge, Histogram

logs_ingested_total = Counter(
    'logs_ingested_total',
    'Total number of logs ingested successfully.',
    labelnames=('service_name',),
)

anomalies_detected_total = Counter(
    'anomalies_detected_total',
    'Total number of logs scored as anomalies.',
)

logs_scored_total = Counter(
    'logs_scored_total',
    'Total number of logs scored by the detection pipeline.',
)

scoring_latency_seconds = Histogram(
    'scoring_latency_seconds',
    'Wall-clock time taken to score a single log entry.',
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, +float('inf')),
)

consumer_lag = Gauge(
    'consumer_lag',
    'Pending messages in the Redis stream consumer group.',
)
