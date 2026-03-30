
from __future__ import annotations

import asyncio
import json
import math
import os
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from stream_processor.mock_analyzer import (
    predict_anomaly as predict_anomaly_mock,
)
from stream_processor.mock_analyzer import predict_bot as predict_bot_mock
from stream_processor.mock_analyzer import predict_forecast as predict_forecast_mock


@dataclass(frozen=True)
class StreamSettings:
    nats_url: str = os.getenv("NATS_URL", "nats://localhost:4222")
    subject: str = os.getenv("NATS_SUBJECT", "logs.raw")
    batch_size: int = int(os.getenv("STREAM_BATCH_SIZE", "5"))
    poll_timeout_seconds: int = int(os.getenv("STREAM_POLL_TIMEOUT_SECONDS", "3"))
    poll_interval_seconds: int = int(os.getenv("STREAM_POLL_INTERVAL_SECONDS", "10"))
    ml_api_url: str = os.getenv("ML_API_URL", "http://localhost:8000")
    clickhouse_url: str = os.getenv("CLICKHOUSE_URL", "http://localhost:8123")
    processed_logs_table: str = os.getenv("CLICKHOUSE_PROCESSED_LOGS_TABLE", "processed_logs")
    bot_feature_table: str = os.getenv("CLICKHOUSE_BOT_FEATURE_TABLE", "bot_feature_windows")
    load_forecast_table: str = os.getenv("CLICKHOUSE_LOAD_FORECAST_TABLE", "load_forecasts")
    anomaly_alert_table: str = os.getenv("CLICKHOUSE_ANOMALY_ALERT_TABLE", "anomaly_alerts")
    raw_log_sample_path: Path = Path(
        os.getenv(
            "RAW_LOG_SAMPLE_PATH",
            str(
                Path(__file__).resolve().parents[3]
                / "contracts"
                / "examples"
                / "raw-logs.sample.jsonl"
            ),
        )
    )
    fallback_output_path: Path = Path(
        os.getenv(
            "STREAM_FALLBACK_OUTPUT_PATH",
            str(Path(__file__).resolve().parents[2] / "output" / "processed_rows.mock.jsonl"),
        )
    )
    ml_timeout_seconds: int = int(os.getenv("ML_API_TIMEOUT_SECONDS", "2"))
    bot_window_seconds: int = int(os.getenv("BOT_WINDOW_SECONDS", "60"))
    bot_window_slide_seconds: int = int(os.getenv("BOT_WINDOW_SLIDE_SECONDS", "10"))
    anomaly_window_seconds: int = int(os.getenv("ANOMALY_WINDOW_SECONDS", "60"))
    anomaly_window_slide_seconds: int = int(os.getenv("ANOMALY_WINDOW_SLIDE_SECONDS", "10"))
    anomaly_baseline_lookback_seconds: int = int(
        os.getenv("ANOMALY_BASELINE_LOOKBACK_SECONDS", "300")
    )
    forecast_bucket_seconds: int = int(os.getenv("FORECAST_BUCKET_SECONDS", "60"))
    forecast_history_size: int = int(os.getenv("FORECAST_HISTORY_SIZE", "10"))
    use_spark_windows: bool = os.getenv("STREAM_USE_SPARK_WINDOWS", "0") == "1"


@dataclass
class RuntimeState:
    recent_events: list[dict[str, Any]] = field(default_factory=list)
    traffic_buckets: dict[tuple[str, str], dict[datetime, int]] = field(default_factory=dict)


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def format_clickhouse_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")


def iso_to_clickhouse_datetime(value: str) -> str:
    return format_clickhouse_datetime(parse_timestamp(value))


def shift_logs_to_now(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not records:
        return []
    parsed_times: list[datetime] = []
    for record in records:
        timestamp = record.get("timestamp")
        if isinstance(timestamp, str) and timestamp:
            parsed_times.append(parse_timestamp(timestamp))
    if not parsed_times:
        return records
    now = datetime.now(timezone.utc)
    delta = now - max(parsed_times)
    shifted: list[dict[str, Any]] = []
    for record in records:
        timestamp = record.get("timestamp")
        if isinstance(timestamp, str) and timestamp:
            shifted_time = parse_timestamp(timestamp) + delta
            updated = dict(record)
            updated["timestamp"] = format_timestamp(shifted_time)
            shifted.append(updated)
        else:
            shifted.append(record)
    return shifted


def align_window_end(value: datetime, slide_seconds: int) -> datetime:
    epoch_seconds = int(value.astimezone(timezone.utc).timestamp())
    aligned_seconds = ((epoch_seconds + slide_seconds - 1) // slide_seconds) * slide_seconds
    return datetime.fromtimestamp(aligned_seconds, tz=timezone.utc)


def percentile(values: list[int | float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def normalize_raw_log(record: dict[str, Any]) -> dict[str, Any]:
    latency_ms = int(record.get("latency_ms", record.get("request_time_ms", 0)))
    timestamp = record.get("timestamp")
    ip = record.get("ip", "0.0.0.0")
    user_agent = record.get("user_agent", "unknown")
    endpoint = record.get("endpoint", "/unknown")
    normalized = {
        "schema_version": record.get("schema_version", "v2"),
        "timestamp": timestamp,
        "request_id": record.get("request_id", f"req-{ip.replace('.', '-')}-{timestamp}"),
        "session_id": record.get("session_id", f"{ip}::{user_agent}"),
        "ip": ip,
        "user_agent": user_agent,
        "method": str(record.get("method", "GET")).upper(),
        "endpoint": endpoint,
        "route_template": record.get("route_template", endpoint),
        "status": int(record.get("status", 200)),
        "latency_ms": latency_ms,
    }
    normalized["event_time"] = parse_timestamp(normalized["timestamp"])
    return normalized


def load_sample_logs(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


async def fetch_nats_batch(settings: StreamSettings) -> list[dict[str, Any]]:
    try:
        import nats
    except ModuleNotFoundError:
        return []

    messages: list[dict[str, Any]] = []
    event = asyncio.Event()

    async def ignore_error(_exc) -> None:
        return None

    try:
        connect_timeout = max(0.1, float(settings.poll_timeout_seconds))
        nc = await asyncio.wait_for(
            nats.connect(
                settings.nats_url,
                allow_reconnect=False,
                connect_timeout=connect_timeout,
                reconnect_time_wait=0,
                max_reconnect_attempts=0,
                error_cb=ignore_error,
            ),
            timeout=connect_timeout,
        )
    except Exception:
        return []

    async def handle_message(msg) -> None:
        messages.append(json.loads(msg.data.decode("utf-8")))
        if len(messages) >= settings.batch_size:
            event.set()

    sub = await nc.subscribe(settings.subject, cb=handle_message)

    try:
        await asyncio.wait_for(event.wait(), timeout=settings.poll_timeout_seconds)
    except asyncio.TimeoutError:
        pass
    finally:
        try:
            await sub.unsubscribe()
        finally:
            await nc.drain()

    return messages


def request_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    timeout: int = 2,
) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    response = request.urlopen(
        request.Request(url, data=data, method=method, headers=headers),
        timeout=timeout,
    )
    with response:
        return json.loads(response.read().decode("utf-8"))


def ml_api_ready(base_url: str, timeout: int) -> bool:
    try:
        payload = request_json("GET", f"{base_url.rstrip('/')}/healthz", timeout=timeout)
    except (error.HTTPError, error.URLError, TimeoutError, json.JSONDecodeError):
        return False
    return payload.get("status") == "ok"


def _is_night(event_time: datetime) -> int:
    hour = event_time.hour
    return 1 if hour < 6 or hour >= 22 else 0


def _window_records(
    records: list[dict[str, Any]],
    window_seconds: int,
    slide_seconds: int,
) -> tuple[datetime, datetime, list[dict[str, Any]]]:
    latest = max(record["event_time"] for record in records)
    window_end = align_window_end(latest, slide_seconds)
    window_start = window_end - timedelta(seconds=window_seconds)
    scoped = [record for record in records if window_start < record["event_time"] <= window_end]
    return window_start, window_end, scoped


def _group_by_entity(records: list[dict[str, Any]]) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for record in records:
        key = (record["ip"], record["session_id"], record["user_agent"])
        groups.setdefault(key, []).append(record)
    return groups


def _group_by_endpoint(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        groups.setdefault(record["endpoint"], []).append(record)
    return groups


def build_bot_feature_windows_python(
    records: list[dict[str, Any]],
    settings: StreamSettings,
) -> list[dict[str, Any]]:
    if not records:
        return []
    window_start, window_end, scoped = _window_records(
        records,
        settings.bot_window_seconds,
        settings.bot_window_slide_seconds,
    )
    payloads: list[dict[str, Any]] = []
    for (ip, session_id, user_agent), events in _group_by_entity(scoped).items():
        total = len(events)
        route_counts = Counter(event["route_template"] for event in events)
        second_counts = Counter(event["event_time"].replace(microsecond=0) for event in events)
        first_seen = min(event["event_time"] for event in events)
        last_seen = max(event["event_time"] for event in events)
        payloads.append(
            {
                "feature_version": "v2",
                "window_start": format_timestamp(window_start),
                "window_end": format_timestamp(window_end),
                "entity": {
                    "ip": ip,
                    "session_id": session_id,
                    "user_agent": user_agent,
                },
                "features": {
                    "number_of_requests": total,
                    "total_duration_s": round((last_seen - first_seen).total_seconds(), 3),
                    "average_time_ms": round(sum(event["latency_ms"] for event in events) / total, 3),
                    "repeated_requests": round(max(route_counts.values()) / total, 4),
                    "http_response_2xx": round(sum(1 for event in events if 200 <= event["status"] < 300) / total, 4),
                    "http_response_3xx": round(sum(1 for event in events if 300 <= event["status"] < 400) / total, 4),
                    "http_response_4xx": round(sum(1 for event in events if 400 <= event["status"] < 500) / total, 4),
                    "http_response_5xx": round(sum(1 for event in events if 500 <= event["status"] < 600) / total, 4),
                    "get_method": round(sum(1 for event in events if event["method"] == "GET") / total, 4),
                    "post_method": round(sum(1 for event in events if event["method"] == "POST") / total, 4),
                    "head_method": round(sum(1 for event in events if event["method"] == "HEAD") / total, 4),
                    "other_method": round(sum(1 for event in events if event["method"] not in {"GET", "POST", "HEAD"}) / total, 4),
                    "night": 1 if sum(_is_night(event["event_time"]) for event in events) >= math.ceil(total / 2) else 0,
                    "max_barrage": max(second_counts.values()),
                },
            }
        )
    return sorted(payloads, key=lambda item: (item["entity"]["ip"], item["entity"]["session_id"]))

def build_bot_feature_windows_spark(
    records: list[dict[str, Any]],
    settings: StreamSettings,
) -> list[dict[str, Any]]:
    try:
        from pyspark.sql import SparkSession
        from pyspark.sql.functions import avg, count, hour, lit, max as spark_max, min as spark_min, when, window
    except ModuleNotFoundError:
        return build_bot_feature_windows_python(records, settings)

    if not records:
        return []

    latest = max(record["event_time"] for record in records)
    active_end = align_window_end(latest, settings.bot_window_slide_seconds)
    spark = SparkSession.builder.master("local[1]").appName("aiops-bot-window").getOrCreate()
    try:
        df = spark.createDataFrame(records)
        aggregated = (
            df.groupBy(
                window(
                    "event_time",
                    f"{settings.bot_window_seconds} seconds",
                    f"{settings.bot_window_slide_seconds} seconds",
                ).alias("window"),
                "ip",
                "session_id",
                "user_agent",
            )
            .agg(
                count("*").alias("number_of_requests"),
                avg("latency_ms").alias("average_time_ms"),
                spark_min("event_time").alias("first_seen"),
                spark_max("event_time").alias("last_seen"),
                avg(when((df.status >= 200) & (df.status < 300), lit(1.0)).otherwise(lit(0.0))).alias("http_response_2xx"),
                avg(when((df.status >= 300) & (df.status < 400), lit(1.0)).otherwise(lit(0.0))).alias("http_response_3xx"),
                avg(when((df.status >= 400) & (df.status < 500), lit(1.0)).otherwise(lit(0.0))).alias("http_response_4xx"),
                avg(when((df.status >= 500) & (df.status < 600), lit(1.0)).otherwise(lit(0.0))).alias("http_response_5xx"),
                avg(when(df.method == "GET", lit(1.0)).otherwise(lit(0.0))).alias("get_method"),
                avg(when(df.method == "POST", lit(1.0)).otherwise(lit(0.0))).alias("post_method"),
                avg(when(df.method == "HEAD", lit(1.0)).otherwise(lit(0.0))).alias("head_method"),
                avg(when(~df.method.isin("GET", "POST", "HEAD"), lit(1.0)).otherwise(lit(0.0))).alias("other_method"),
                spark_max(when((hour("event_time") < 6) | (hour("event_time") >= 22), lit(1)).otherwise(lit(0))).alias("night"),
            )
            .collect()
        )
    finally:
        spark.stop()

    scoped_start = active_end - timedelta(seconds=settings.bot_window_seconds)
    scoped_records = [record for record in records if scoped_start < record["event_time"] <= active_end]
    grouped_records = _group_by_entity(scoped_records)
    payloads: list[dict[str, Any]] = []
    for row in aggregated:
        row_data = row.asDict(recursive=True)
        row_end = row_data["window"]["end"]
        if row_end.tzinfo is None:
            row_end = row_end.replace(tzinfo=timezone.utc)
        else:
            row_end = row_end.astimezone(timezone.utc)
        if row_end != active_end:
            continue
        key = (row_data["ip"], row_data["session_id"], row_data["user_agent"])
        events = grouped_records.get(key, [])
        if not events:
            continue
        route_counts = Counter(event["route_template"] for event in events)
        second_counts = Counter(event["event_time"].replace(microsecond=0) for event in events)
        payloads.append(
            {
                "feature_version": "v2",
                "window_start": format_timestamp(scoped_start),
                "window_end": format_timestamp(active_end),
                "entity": {
                    "ip": row_data["ip"],
                    "session_id": row_data["session_id"],
                    "user_agent": row_data["user_agent"],
                },
                "features": {
                    "number_of_requests": int(row_data["number_of_requests"]),
                    "total_duration_s": round((row_data["last_seen"] - row_data["first_seen"]).total_seconds(), 3),
                    "average_time_ms": round(float(row_data["average_time_ms"]), 3),
                    "repeated_requests": round(max(route_counts.values()) / max(int(row_data["number_of_requests"]), 1), 4),
                    "http_response_2xx": round(float(row_data["http_response_2xx"]), 4),
                    "http_response_3xx": round(float(row_data["http_response_3xx"]), 4),
                    "http_response_4xx": round(float(row_data["http_response_4xx"]), 4),
                    "http_response_5xx": round(float(row_data["http_response_5xx"]), 4),
                    "get_method": round(float(row_data["get_method"]), 4),
                    "post_method": round(float(row_data["post_method"]), 4),
                    "head_method": round(float(row_data["head_method"]), 4),
                    "other_method": round(float(row_data["other_method"]), 4),
                    "night": int(row_data["night"]),
                    "max_barrage": max(second_counts.values()),
                },
            }
        )
    return sorted(payloads, key=lambda item: (item["entity"]["ip"], item["entity"]["session_id"]))


def build_bot_feature_windows(records: list[dict[str, Any]], settings: StreamSettings) -> list[dict[str, Any]]:
    if settings.use_spark_windows:
        return build_bot_feature_windows_spark(records, settings)
    return build_bot_feature_windows_python(records, settings)


def build_anomaly_feature_windows_python(
    records: list[dict[str, Any]],
    settings: StreamSettings,
) -> list[dict[str, Any]]:
    if not records:
        return []
    window_start, window_end, scoped = _window_records(
        records,
        settings.anomaly_window_seconds,
        settings.anomaly_window_slide_seconds,
    )
    baseline_start = window_start - timedelta(seconds=settings.anomaly_baseline_lookback_seconds)
    payloads: list[dict[str, Any]] = []
    all_by_endpoint = _group_by_endpoint(records)
    for endpoint, events in _group_by_endpoint(scoped).items():
        total = len(events)
        baseline_events = [
            event
            for event in all_by_endpoint.get(endpoint, [])
            if baseline_start < event["event_time"] <= window_start
        ]
        latencies = [event["latency_ms"] for event in events]
        baseline_latencies = [event["latency_ms"] for event in baseline_events] or latencies
        baseline_5xx = [1 for event in baseline_events if 500 <= event["status"] < 600]
        payloads.append(
            {
                "feature_version": "v2",
                "window_start": format_timestamp(window_start),
                "window_end": format_timestamp(window_end),
                "entity": {"endpoint": endpoint},
                "features": {
                    "request_count": total,
                    "avg_latency_ms": round(sum(latencies) / total, 3),
                    "p95_latency_ms": round(percentile(latencies, 0.95), 3),
                    "p99_latency_ms": round(percentile(latencies, 0.99), 3),
                    "status_5xx_ratio": round(sum(1 for event in events if 500 <= event["status"] < 600) / total, 4),
                    "baseline_avg_latency_ms": round(sum(baseline_latencies) / len(baseline_latencies), 3),
                    "baseline_5xx_ratio": round(len(baseline_5xx) / max(len(baseline_events), 1), 4),
                },
            }
        )
    return sorted(payloads, key=lambda item: item["entity"]["endpoint"])


def build_anomaly_feature_windows_spark(
    records: list[dict[str, Any]],
    settings: StreamSettings,
) -> list[dict[str, Any]]:
    try:
        from pyspark.sql import SparkSession
        from pyspark.sql.functions import avg, count, lit, percentile_approx, when, window
    except ModuleNotFoundError:
        return build_anomaly_feature_windows_python(records, settings)

    if not records:
        return []

    latest = max(record["event_time"] for record in records)
    active_end = align_window_end(latest, settings.anomaly_window_slide_seconds)
    active_start = active_end - timedelta(seconds=settings.anomaly_window_seconds)
    baseline_start = active_start - timedelta(seconds=settings.anomaly_baseline_lookback_seconds)

    spark = SparkSession.builder.master("local[1]").appName("aiops-anomaly-window").getOrCreate()
    try:
        df = spark.createDataFrame(records)
        aggregated = (
            df.groupBy(
                window(
                    "event_time",
                    f"{settings.anomaly_window_seconds} seconds",
                    f"{settings.anomaly_window_slide_seconds} seconds",
                ).alias("window"),
                "endpoint",
            )
            .agg(
                count("*").alias("request_count"),
                avg("latency_ms").alias("avg_latency_ms"),
                percentile_approx("latency_ms", 0.95).alias("p95_latency_ms"),
                percentile_approx("latency_ms", 0.99).alias("p99_latency_ms"),
                avg(when((df.status >= 500) & (df.status < 600), lit(1.0)).otherwise(lit(0.0))).alias("status_5xx_ratio"),
            )
            .collect()
        )
    finally:
        spark.stop()

    by_endpoint = _group_by_endpoint(records)
    payloads: list[dict[str, Any]] = []
    for row in aggregated:
        row_data = row.asDict(recursive=True)
        row_end = row_data["window"]["end"]
        if row_end.tzinfo is None:
            row_end = row_end.replace(tzinfo=timezone.utc)
        else:
            row_end = row_end.astimezone(timezone.utc)
        if row_end != active_end:
            continue
        endpoint = row_data["endpoint"]
        baseline_events = [
            event
            for event in by_endpoint.get(endpoint, [])
            if baseline_start < event["event_time"] <= active_start
        ]
        baseline_latencies = [event["latency_ms"] for event in baseline_events] or [float(row_data["avg_latency_ms"])]
        baseline_5xx_ratio = (
            sum(1 for event in baseline_events if 500 <= event["status"] < 600) / max(len(baseline_events), 1)
        )
        payloads.append(
            {
                "feature_version": "v2",
                "window_start": format_timestamp(active_start),
                "window_end": format_timestamp(active_end),
                "entity": {"endpoint": endpoint},
                "features": {
                    "request_count": int(row_data["request_count"]),
                    "avg_latency_ms": round(float(row_data["avg_latency_ms"]), 3),
                    "p95_latency_ms": round(float(row_data["p95_latency_ms"]), 3),
                    "p99_latency_ms": round(float(row_data["p99_latency_ms"]), 3),
                    "status_5xx_ratio": round(float(row_data["status_5xx_ratio"]), 4),
                    "baseline_avg_latency_ms": round(sum(baseline_latencies) / len(baseline_latencies), 3),
                    "baseline_5xx_ratio": round(float(baseline_5xx_ratio), 4),
                },
            }
        )
    return sorted(payloads, key=lambda item: item["entity"]["endpoint"])


def build_anomaly_feature_windows(records: list[dict[str, Any]], settings: StreamSettings) -> list[dict[str, Any]]:
    if settings.use_spark_windows:
        return build_anomaly_feature_windows_spark(records, settings)
    return build_anomaly_feature_windows_python(records, settings)


def update_runtime_state(
    state: RuntimeState,
    raw_logs: list[dict[str, Any]],
    settings: StreamSettings,
) -> None:
    if not raw_logs:
        return
    state.recent_events.extend(raw_logs)
    latest = max(record["event_time"] for record in state.recent_events)
    keep_seconds = max(
        settings.bot_window_seconds,
        settings.anomaly_window_seconds + settings.anomaly_baseline_lookback_seconds,
    )
    cutoff = latest - timedelta(seconds=keep_seconds)
    state.recent_events = [record for record in state.recent_events if record["event_time"] >= cutoff]

    for record in raw_logs:
        bucket_end = align_window_end(record["event_time"], settings.forecast_bucket_seconds)
        for key in (("system", ""), ("endpoint", record["endpoint"])):
            bucket_map = state.traffic_buckets.setdefault(key, {})
            bucket_map[bucket_end] = bucket_map.get(bucket_end, 0) + 1

    latest_bucket_end = align_window_end(latest, settings.forecast_bucket_seconds)
    bucket_cutoff = latest_bucket_end - timedelta(
        seconds=settings.forecast_bucket_seconds * (settings.forecast_history_size + 2)
    )
    for key in list(state.traffic_buckets):
        filtered = {
            bucket_end: count
            for bucket_end, count in state.traffic_buckets[key].items()
            if bucket_end >= bucket_cutoff
        }
        if filtered:
            state.traffic_buckets[key] = filtered
        else:
            del state.traffic_buckets[key]


def build_forecast_requests(
    state: RuntimeState,
    raw_logs: list[dict[str, Any]],
    settings: StreamSettings,
) -> list[dict[str, Any]]:
    if not raw_logs:
        return []
    latest = max(record["event_time"] for record in raw_logs)
    latest_bucket_end = align_window_end(latest, settings.forecast_bucket_seconds)
    predicted_bucket_end = latest_bucket_end + timedelta(seconds=settings.forecast_bucket_seconds)
    targets = {("system", "")}
    targets.update(("endpoint", record["endpoint"]) for record in raw_logs)
    payloads: list[dict[str, Any]] = []
    for scope, endpoint in sorted(targets):
        bucket_map = state.traffic_buckets.get((scope, endpoint), {})
        history: list[int] = []
        for offset in range(settings.forecast_history_size - 1, -1, -1):
            bucket_end = latest_bucket_end - timedelta(seconds=settings.forecast_bucket_seconds * offset)
            history.append(bucket_map.get(bucket_end, 0))
        if not any(history):
            continue
        recent = history[-5:] if len(history) >= 5 else history
        mean = sum(recent) / len(recent)
        variance = sum((value - mean) ** 2 for value in recent) / len(recent)
        payloads.append(
            {
                "feature_version": "v2",
                "bucket_end": format_timestamp(latest_bucket_end),
                "predicted_bucket_end": format_timestamp(predicted_bucket_end),
                "target": {"scope": scope, "endpoint": endpoint},
                "history_rps": history,
                "features": {
                    "rolling_mean_5": round(mean, 3),
                    "rolling_std_5": round(math.sqrt(variance), 3),
                    "hour_of_day": predicted_bucket_end.hour,
                    "day_of_week": predicted_bucket_end.weekday(),
                },
            }
        )
    return payloads

def _safe_post_prediction(
    api_ready: bool,
    base_url: str,
    path: str,
    payload: dict[str, Any],
    timeout: int,
    fallback,
) -> dict[str, Any]:
    if api_ready:
        try:
            return request_json("POST", f"{base_url.rstrip('/')}{path}", payload=payload, timeout=timeout)
        except (error.HTTPError, error.URLError, TimeoutError, json.JSONDecodeError):
            pass
    return fallback(payload)


def predict_bot_windows(
    payloads: list[dict[str, Any]],
    base_url: str,
    timeout: int,
    api_ready: bool,
) -> dict[tuple[str, str, str], dict[str, Any]]:
    predictions: dict[tuple[str, str, str], dict[str, Any]] = {}
    for payload in payloads:
        key = (
            payload["entity"]["ip"],
            payload["entity"]["session_id"],
            payload["entity"]["user_agent"],
        )
        predictions[key] = _safe_post_prediction(
            api_ready,
            base_url,
            "/predict/bot",
            payload,
            timeout,
            predict_bot_mock,
        )
    return predictions


def predict_forecasts(
    payloads: list[dict[str, Any]],
    base_url: str,
    timeout: int,
    api_ready: bool,
) -> dict[tuple[str, str], dict[str, Any]]:
    predictions: dict[tuple[str, str], dict[str, Any]] = {}
    for payload in payloads:
        key = (payload["target"]["scope"], payload["target"]["endpoint"])
        predictions[key] = _safe_post_prediction(
            api_ready,
            base_url,
            "/predict/forecast",
            payload,
            timeout,
            predict_forecast_mock,
        )
    return predictions


def predict_anomaly_windows(
    payloads: list[dict[str, Any]],
    base_url: str,
    timeout: int,
    api_ready: bool,
) -> dict[str, dict[str, Any]]:
    predictions: dict[str, dict[str, Any]] = {}
    for payload in payloads:
        key = payload["entity"]["endpoint"]
        predictions[key] = _safe_post_prediction(
            api_ready,
            base_url,
            "/predict/anomaly",
            payload,
            timeout,
            predict_anomaly_mock,
        )
    return predictions


def build_bot_feature_rows(
    payloads: list[dict[str, Any]],
    predictions: dict[tuple[str, str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for payload in payloads:
        entity = payload["entity"]
        features = payload["features"]
        prediction = predictions[(entity["ip"], entity["session_id"], entity["user_agent"])]
        rows.append(
            {
                "window_start": iso_to_clickhouse_datetime(payload["window_start"]),
                "window_end": iso_to_clickhouse_datetime(payload["window_end"]),
                "ip": entity["ip"],
                "session_id": entity["session_id"],
                "user_agent": entity["user_agent"],
                "number_of_requests": int(features["number_of_requests"]),
                "repeated_requests": float(features["repeated_requests"]),
                "max_barrage": int(features["max_barrage"]),
                "http_response_4xx": float(features["http_response_4xx"]),
                "http_response_5xx": float(features["http_response_5xx"]),
                "bot_score": float(prediction["bot_score"]),
                "is_bot": int(bool(prediction["is_bot"])),
                "model_version": prediction["model_version"],
            }
        )
    return rows


def build_load_forecast_rows(
    payloads: list[dict[str, Any]],
    predictions: dict[tuple[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for payload in payloads:
        target = payload["target"]
        prediction = predictions[(target["scope"], target["endpoint"])]
        rows.append(
            {
                "bucket_end": iso_to_clickhouse_datetime(payload["bucket_end"]),
                "predicted_bucket_end": iso_to_clickhouse_datetime(payload["predicted_bucket_end"]),
                "scope": target["scope"],
                "endpoint": target["endpoint"],
                "history_size": len(payload["history_rps"]),
                "current_rps": int(payload["history_rps"][-1]),
                "predicted_request_count": int(prediction["predicted_request_count"]),
                "model_version": prediction["model_version"],
            }
        )
    return rows


def build_anomaly_alert_rows(
    payloads: list[dict[str, Any]],
    predictions: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for payload in payloads:
        endpoint = payload["entity"]["endpoint"]
        features = payload["features"]
        prediction = predictions[endpoint]
        rows.append(
            {
                "window_start": iso_to_clickhouse_datetime(payload["window_start"]),
                "window_end": iso_to_clickhouse_datetime(payload["window_end"]),
                "endpoint": endpoint,
                "request_count": int(features["request_count"]),
                "avg_latency_ms": float(features["avg_latency_ms"]),
                "p95_latency_ms": float(features["p95_latency_ms"]),
                "p99_latency_ms": float(features["p99_latency_ms"]),
                "status_5xx_ratio": float(features["status_5xx_ratio"]),
                "baseline_avg_latency_ms": float(features["baseline_avg_latency_ms"]),
                "anomaly_score": float(prediction["anomaly_score"]),
                "is_anomaly": int(bool(prediction["is_anomaly"])),
                "model_version": prediction["model_version"],
            }
        )
    return rows

def build_processed_logs(
    raw_logs: list[dict[str, Any]],
    bot_predictions: dict[tuple[str, str, str], dict[str, Any]],
    forecast_predictions: dict[tuple[str, str], dict[str, Any]],
    anomaly_predictions: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    processed: list[dict[str, Any]] = []
    default_forecast = forecast_predictions.get(("system", ""), {"predicted_request_count": 0})
    for record in raw_logs:
        bot_prediction = bot_predictions.get(
            (record["ip"], record["session_id"], record["user_agent"]),
            {"bot_score": 0.0, "is_bot": False},
        )
        anomaly_prediction = anomaly_predictions.get(
            record["endpoint"],
            {"anomaly_score": 0.0, "is_anomaly": False},
        )
        endpoint_forecast = forecast_predictions.get(
            ("endpoint", record["endpoint"]),
            default_forecast,
        )
        processed.append(
            {
                "schema_version": record["schema_version"],
                "timestamp": iso_to_clickhouse_datetime(record["timestamp"]),
                "request_id": record["request_id"],
                "session_id": record["session_id"],
                "ip": record["ip"],
                "user_agent": record["user_agent"],
                "method": record["method"],
                "endpoint": record["endpoint"],
                "route_template": record["route_template"],
                "status": int(record["status"]),
                "latency_ms": int(record["latency_ms"]),
                "bot_score": float(bot_prediction["bot_score"]),
                "is_bot": int(bool(bot_prediction["is_bot"])),
                "predicted_load": int(endpoint_forecast["predicted_request_count"]),
                "anomaly_score": float(anomaly_prediction["anomaly_score"]),
                "is_anomaly": int(bool(anomaly_prediction["is_anomaly"])),
            }
        )
    return processed


def write_rows_to_clickhouse(rows: list[dict[str, Any]], base_url: str, table: str) -> None:
    if not rows:
        return
    body = "\n".join(json.dumps(row) for row in rows).encode("utf-8")
    query = parse.urlencode({"query": f"INSERT INTO {table} FORMAT JSONEachRow"})
    url = f"{base_url.rstrip('/')}/?{query}"
    response = request.urlopen(request.Request(url, data=body, method="POST"), timeout=5)
    with response:
        response.read()


def write_all_tables(table_rows: dict[str, list[dict[str, Any]]], settings: StreamSettings) -> None:
    write_rows_to_clickhouse(table_rows[settings.processed_logs_table], settings.clickhouse_url, settings.processed_logs_table)
    write_rows_to_clickhouse(table_rows[settings.bot_feature_table], settings.clickhouse_url, settings.bot_feature_table)
    write_rows_to_clickhouse(table_rows[settings.load_forecast_table], settings.clickhouse_url, settings.load_forecast_table)
    write_rows_to_clickhouse(table_rows[settings.anomaly_alert_table], settings.clickhouse_url, settings.anomaly_alert_table)


def write_fallback_file(table_rows: dict[str, list[dict[str, Any]]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for table, rows in table_rows.items():
        for row in rows:
            lines.append(json.dumps({"table": table, "row": row}))
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def process_once(
    settings: StreamSettings,
    state: RuntimeState | None = None,
) -> dict[str, Any]:
    runtime_state = state or RuntimeState()
    raw_logs = asyncio.run(fetch_nats_batch(settings))
    source = "nats"
    if not raw_logs:
        raw_logs = shift_logs_to_now(load_sample_logs(settings.raw_log_sample_path))
        source = "sample"

    normalized = [normalize_raw_log(record) for record in raw_logs[: settings.batch_size]]
    update_runtime_state(runtime_state, normalized, settings)

    bot_requests = build_bot_feature_windows(runtime_state.recent_events, settings)
    anomaly_requests = build_anomaly_feature_windows(runtime_state.recent_events, settings)
    forecast_requests = build_forecast_requests(runtime_state, normalized, settings)
    api_ready = ml_api_ready(settings.ml_api_url, settings.ml_timeout_seconds)
    bot_predictions = predict_bot_windows(bot_requests, settings.ml_api_url, settings.ml_timeout_seconds, api_ready)
    forecast_predictions = predict_forecasts(
        forecast_requests,
        settings.ml_api_url,
        settings.ml_timeout_seconds,
        api_ready,
    )
    anomaly_predictions = predict_anomaly_windows(
        anomaly_requests,
        settings.ml_api_url,
        settings.ml_timeout_seconds,
        api_ready,
    )

    table_rows = {
        settings.processed_logs_table: build_processed_logs(
            normalized,
            bot_predictions,
            forecast_predictions,
            anomaly_predictions,
        ),
        settings.bot_feature_table: build_bot_feature_rows(bot_requests, bot_predictions),
        settings.load_forecast_table: build_load_forecast_rows(forecast_requests, forecast_predictions),
        settings.anomaly_alert_table: build_anomaly_alert_rows(anomaly_requests, anomaly_predictions),
    }

    try:
        write_all_tables(table_rows, settings)
        sink = "clickhouse"
    except (error.HTTPError, error.URLError, TimeoutError, OSError):
        write_fallback_file(table_rows, settings.fallback_output_path)
        sink = "file"

    return {
        "source": source,
        "sink": sink,
        "count": len(table_rows[settings.processed_logs_table]),
        "bot_windows": len(table_rows[settings.bot_feature_table]),
        "forecasts": len(table_rows[settings.load_forecast_table]),
        "anomalies": len(table_rows[settings.anomaly_alert_table]),
    }


def main() -> None:
    settings = StreamSettings()
    runtime_state = RuntimeState()
    while True:
        status = process_once(settings, runtime_state)
        print(
            "Processed "
            f"{status['count']} raw logs from {status['source']} and wrote to {status['sink']} "
            f"(bot_windows={status['bot_windows']}, forecasts={status['forecasts']}, anomalies={status['anomalies']})"
        )
        asyncio.run(asyncio.sleep(settings.poll_interval_seconds))


if __name__ == "__main__":
    main()
