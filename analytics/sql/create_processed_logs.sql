CREATE TABLE IF NOT EXISTS processed_logs (
    timestamp DateTime,
    ip String,
    endpoint String,
    latency_ms Int32,
    is_bot UInt8,
    predicted_load Int32,
    is_anomaly UInt8
) ENGINE = MergeTree()
ORDER BY timestamp;
