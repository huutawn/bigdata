from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from stream_processor.mock_analyzer import analyze as analyze_mock


@dataclass(frozen=True)
class StreamSettings:
    nats_url: str = os.getenv("NATS_URL", "nats://localhost:4222")
    subject: str = os.getenv("NATS_SUBJECT", "logs.raw")
    batch_size: int = int(os.getenv("STREAM_BATCH_SIZE", "5"))
    poll_timeout_seconds: int = int(os.getenv("STREAM_POLL_TIMEOUT_SECONDS", "3"))
    poll_interval_seconds: int = int(os.getenv("STREAM_POLL_INTERVAL_SECONDS", "10"))
    ml_api_url: str = os.getenv("ML_API_URL", "http://localhost:8000")
    clickhouse_url: str = os.getenv("CLICKHOUSE_URL", "http://localhost:8123")
    clickhouse_table: str = os.getenv("CLICKHOUSE_TABLE", "processed_logs")
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
            str(
                Path(__file__).resolve().parents[2]
                / "output"
                / "processed_logs.mock.jsonl"
            ),
        )
    )
    ml_timeout_seconds: int = int(os.getenv("ML_API_TIMEOUT_SECONDS", "2"))


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
    nc = await nats.connect(settings.nats_url)

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
        await sub.unsubscribe()
        await nc.drain()

    return messages


def request_json(method: str, url: str, payload: dict[str, Any] | None = None, timeout: int = 2) -> dict[str, Any]:
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


def analyze_record(record: dict[str, Any], current_rps: int, base_url: str, timeout: int) -> dict[str, Any]:
    payload = {
        "ip": record["ip"],
        "latency_ms": record["request_time_ms"],
        "current_rps": current_rps,
    }

    if ml_api_ready(base_url, timeout):
        try:
            return request_json(
                "POST",
                f"{base_url.rstrip('/')}/analyze",
                payload=payload,
                timeout=timeout,
            )
        except (error.HTTPError, error.URLError, TimeoutError, json.JSONDecodeError):
            pass

    return analyze_mock(payload["ip"], payload["latency_ms"], payload["current_rps"])


def enrich_logs(raw_logs: list[dict[str, Any]], base_url: str, timeout: int) -> list[dict[str, Any]]:
    current_rps = len(raw_logs)
    rows: list[dict[str, Any]] = []

    for record in raw_logs:
        analysis = analyze_record(record, current_rps, base_url, timeout)
        rows.append(
            {
                "timestamp": record["timestamp"],
                "ip": record["ip"],
                "endpoint": record["endpoint"],
                "latency_ms": record["request_time_ms"],
                "is_bot": int(bool(analysis["is_bot"])),
                "predicted_load": int(analysis["predicted_load"]),
                "is_anomaly": int(bool(analysis["is_anomaly"])),
            }
        )

    return rows


def build_micro_batch(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        from pyspark.sql import SparkSession
    except ModuleNotFoundError:
        return rows

    spark = SparkSession.builder.master("local[1]").appName("aiops-stream-processor").getOrCreate()
    try:
        return [item.asDict() for item in spark.createDataFrame(rows).collect()]
    finally:
        spark.stop()


def write_to_clickhouse(rows: list[dict[str, Any]], base_url: str, table: str) -> None:
    body = "\n".join(json.dumps(row) for row in rows).encode("utf-8")
    query = parse.urlencode({"query": f"INSERT INTO {table} FORMAT JSONEachRow"})
    url = f"{base_url.rstrip('/')}/?{query}"
    response = request.urlopen(
        request.Request(url, data=body, method="POST"),
        timeout=5,
    )
    with response:
        response.read()


def write_fallback_file(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(row) for row in rows) + "\n"
    path.write_text(content, encoding="utf-8")


def process_once(settings: StreamSettings) -> dict[str, Any]:
    raw_logs = asyncio.run(fetch_nats_batch(settings))
    source = "nats"
    if not raw_logs:
        raw_logs = load_sample_logs(settings.raw_log_sample_path)
        source = "sample"

    rows = build_micro_batch(
        enrich_logs(raw_logs[: settings.batch_size], settings.ml_api_url, settings.ml_timeout_seconds)
    )

    try:
        write_to_clickhouse(rows, settings.clickhouse_url, settings.clickhouse_table)
        sink = "clickhouse"
    except (error.HTTPError, error.URLError, TimeoutError, OSError):
        write_fallback_file(rows, settings.fallback_output_path)
        sink = "file"

    return {"source": source, "sink": sink, "count": len(rows)}


def main() -> None:
    settings = StreamSettings()
    while True:
        status = process_once(settings)
        print(
            f"Processed {status['count']} logs from {status['source']} and wrote to {status['sink']}"
        )
        asyncio.run(asyncio.sleep(settings.poll_interval_seconds))


if __name__ == "__main__":
    main()
