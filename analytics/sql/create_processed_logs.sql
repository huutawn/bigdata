CREATE TABLE IF NOT EXISTS processed_logs (
    schema_version String,
    timestamp DateTime,
    replay_timestamp Nullable(DateTime),
    request_id String,
    session_id String,
    ip String,
    user_agent String,
    method String,
    endpoint String,
    route_template String,
    status Int32,
    latency_ms Int32,
    bot_score Float64,
    is_bot UInt8,
    predicted_load Int32,
    anomaly_score Float64,
    is_anomaly UInt8
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, ip, request_id)
TTL timestamp + INTERVAL 30 DAY;

CREATE TABLE IF NOT EXISTS bot_feature_windows (
    window_start DateTime,
    window_end DateTime,
    ip String,
    session_id String,
    user_agent String,
    number_of_requests Int32,
    repeated_requests Float64,
    max_barrage Int32,
    http_response_4xx Float64,
    http_response_5xx Float64,
    bot_score Float64,
    is_bot UInt8,
    model_version String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(window_end)
ORDER BY (window_end, ip, session_id)
TTL window_end + INTERVAL 30 DAY;

CREATE TABLE IF NOT EXISTS load_forecasts (
    bucket_end DateTime,
    predicted_bucket_end DateTime,
    scope String,
    endpoint String,
    history_size Int32,
    current_rps Int32,
    predicted_request_count Int32,
    model_version String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(predicted_bucket_end)
ORDER BY (predicted_bucket_end, scope, endpoint)
TTL predicted_bucket_end + INTERVAL 30 DAY;

CREATE TABLE IF NOT EXISTS anomaly_alerts (
    window_start DateTime,
    window_end DateTime,
    endpoint String,
    request_count Int32,
    avg_latency_ms Float64,
    p95_latency_ms Float64,
    p99_latency_ms Float64,
    status_5xx_ratio Float64,
    baseline_avg_latency_ms Float64,
    anomaly_score Float64,
    is_anomaly UInt8,
    model_version String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(window_end)
ORDER BY (window_end, endpoint)
TTL window_end + INTERVAL 30 DAY;
