-- Materialized Views cho AIOps Analytics
-- Tự động aggregate dữ liệu từ raw tables để Grafana query nhanh hơn

-- ============================================================
-- 1. Bot stats theo giờ
-- ============================================================
CREATE TABLE IF NOT EXISTS bot_stats_hourly
(
    hour DateTime,
    ip String,
    session_id String,
    user_agent String,
    total_requests UInt64,
    bot_detected UInt64,
    avg_bot_score Float64,
    max_barrage UInt64,
    avg_repeated_requests Float64,
    avg_4xx_ratio Float64,
    avg_5xx_ratio Float64
)
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(hour)
ORDER BY (hour, ip, session_id)
TTL hour + INTERVAL 30 DAY;

CREATE MATERIALIZED VIEW IF NOT EXISTS bot_stats_hourly_mv
TO bot_stats_hourly
AS SELECT
    toStartOfHour(window_end) AS hour,
    ip,
    session_id,
    user_agent,
    toUInt64(count()) AS total_requests,
    toUInt64(sum(is_bot)) AS bot_detected,
    avg(bot_score) AS avg_bot_score,
    toUInt64(max(max_barrage)) AS max_barrage,
    avg(repeated_requests) AS avg_repeated_requests,
    avg(http_response_4xx) AS avg_4xx_ratio,
    avg(http_response_5xx) AS avg_5xx_ratio
FROM bot_feature_windows
GROUP BY hour, ip, session_id, user_agent;

-- ============================================================
-- 2. Endpoint performance theo giờ
-- ============================================================
CREATE TABLE IF NOT EXISTS endpoint_perf_hourly
(
    hour DateTime,
    endpoint String,
    total_requests UInt64,
    avg_latency_ms Float64,
    p95_latency_ms Float64,
    p99_latency_ms Float64,
    max_5xx_ratio Float64,
    anomaly_detected UInt64,
    avg_anomaly_score Float64
)
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(hour)
ORDER BY (hour, endpoint)
TTL hour + INTERVAL 30 DAY;

CREATE MATERIALIZED VIEW IF NOT EXISTS endpoint_perf_hourly_mv
TO endpoint_perf_hourly
AS SELECT
    toStartOfHour(window_end) AS hour,
    endpoint,
    toUInt64(count()) AS total_requests,
    avg(avg_latency_ms) AS avg_latency_ms,
    max(p95_latency_ms) AS p95_latency_ms,
    max(p99_latency_ms) AS p99_latency_ms,
    max(status_5xx_ratio) AS max_5xx_ratio,
    toUInt64(sum(is_anomaly)) AS anomaly_detected,
    avg(anomaly_score) AS avg_anomaly_score
FROM anomaly_alerts
GROUP BY hour, endpoint;

-- ============================================================
-- 3. Load forecast accuracy theo giờ
-- ============================================================
CREATE TABLE IF NOT EXISTS forecast_accuracy_hourly
(
    hour DateTime,
    scope String,
    endpoint String,
    total_forecasts UInt64,
    avg_predicted_load Float64,
    max_predicted_load UInt64,
    min_predicted_load UInt64
)
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(hour)
ORDER BY (hour, scope, endpoint)
TTL hour + INTERVAL 30 DAY;

CREATE MATERIALIZED VIEW IF NOT EXISTS forecast_accuracy_hourly_mv
TO forecast_accuracy_hourly
AS SELECT
    toStartOfHour(predicted_bucket_end) AS hour,
    scope,
    endpoint,
    toUInt64(count()) AS total_forecasts,
    avg(predicted_request_count) AS avg_predicted_load,
    toUInt64(max(predicted_request_count)) AS max_predicted_load,
    toUInt64(min(predicted_request_count)) AS min_predicted_load
FROM load_forecasts
GROUP BY hour, scope, endpoint;

-- ============================================================
-- 4. Processed logs summary theo giờ
-- ============================================================
CREATE TABLE IF NOT EXISTS processed_logs_summary_hourly
(
    hour DateTime,
    endpoint String,
    total_requests UInt64,
    unique_ips UInt64,
    avg_latency_ms Float64,
    error_4xx_count UInt64,
    error_5xx_count UInt64,
    bot_count UInt64,
    anomaly_count UInt64,
    avg_bot_score Float64,
    avg_anomaly_score Float64,
    avg_predicted_load Float64
)
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(hour)
ORDER BY (hour, endpoint)
TTL hour + INTERVAL 30 DAY;

CREATE MATERIALIZED VIEW IF NOT EXISTS processed_logs_summary_hourly_mv
TO processed_logs_summary_hourly
AS SELECT
    toStartOfHour(timestamp) AS hour,
    endpoint,
    toUInt64(count()) AS total_requests,
    uniq(ip) AS unique_ips,
    avg(latency_ms) AS avg_latency_ms,
    countIf(status >= 400 AND status < 500) AS error_4xx_count,
    countIf(status >= 500) AS error_5xx_count,
    sum(is_bot) AS bot_count,
    sum(is_anomaly) AS anomaly_count,
    avg(bot_score) AS avg_bot_score,
    avg(anomaly_score) AS avg_anomaly_score,
    avg(predicted_load) AS avg_predicted_load
FROM processed_logs
GROUP BY hour, endpoint;

-- ============================================================
-- 5. System-wide traffic theo phút (cho real-time dashboard)
-- ============================================================
CREATE TABLE IF NOT EXISTS system_traffic_minutely
(
    minute DateTime,
    total_requests UInt64,
    unique_ips UInt64,
    avg_latency_ms Float64,
    error_rate Float64,
    bot_ratio Float64,
    anomaly_ratio Float64
)
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMMDD(minute)
ORDER BY (minute)
TTL minute + INTERVAL 7 DAY;

CREATE MATERIALIZED VIEW IF NOT EXISTS system_traffic_minutely_mv
TO system_traffic_minutely
AS SELECT
    toStartOfMinute(timestamp) AS minute,
    toUInt64(count()) AS total_requests,
    uniq(ip) AS unique_ips,
    avg(latency_ms) AS avg_latency_ms,
    countIf(status >= 400) / count() AS error_rate,
    sum(is_bot) / count() AS bot_ratio,
    sum(is_anomaly) / count() AS anomaly_ratio
FROM processed_logs
GROUP BY minute;
