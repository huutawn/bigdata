from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TextIO
from urllib.parse import unquote, urlsplit

from generator.main import _isoformat
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

ALLOWED_METHODS = {"GET", "POST", "HEAD", "PUT", "DELETE", "PATCH"}
LOG_PATTERN = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<timestamp>[^\]]+)\] "(?P<request>[^"]*)" '
    r'(?P<status>\d{3}) (?P<body_bytes>\S+) "(?P<referer>[^"]*)" "(?P<user_agent>[^"]*)"'
    r'(?: "(?P<forwarded>[^"]*)")?$'
)
ID_SEGMENT_PATTERN = re.compile(r"^\d+$")
SIZE_SEGMENT_PATTERN = re.compile(r"^\d+x\d+$", re.IGNORECASE)
HEXISH_SEGMENT_PATTERN = re.compile(r"^[0-9a-fA-F-]{8,}$")
BOT_SIGNATURES = (
    "bot",
    "crawler",
    "spider",
    "ahrefs",
    "bingbot",
    "googlebot",
    "python-requests",
    "curl/",
    "wget",
    "sqlmap",
)


@dataclass(frozen=True)
class ReplaySettings:
    input_dir: Path
    bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094")
    topic: str = os.getenv("KAFKA_TOPIC", "logs.raw")
    time_scale: float = float(os.getenv("GENERATOR_REPLAY_TIME_SCALE", "30"))
    session_gap_minutes: int = int(os.getenv("GENERATOR_SESSION_GAP_MINUTES", "15"))
    flush_every: int = int(os.getenv("GENERATOR_REPLAY_FLUSH_EVERY", "1000"))
    flush_timeout_seconds: int = int(os.getenv("GENERATOR_REPLAY_FLUSH_TIMEOUT_SECONDS", "30"))
    progress_every: int = int(os.getenv("GENERATOR_REPLAY_PROGRESS_EVERY", "1000"))
    max_records: int = int(os.getenv("GENERATOR_REPLAY_MAX_RECORDS", "0"))
    output_jsonl: Path | None = None
    publish: bool = True
    repeat: bool = False


@dataclass
class Sessionizer:
    gap: timedelta = timedelta(minutes=15)
    last_seen: dict[tuple[str, str], datetime] = field(default_factory=dict)
    counters: dict[tuple[str, str], int] = field(default_factory=dict)

    def assign(self, ip: str, user_agent: str, timestamp: datetime) -> str:
        key = (ip, user_agent)
        current = self.counters.get(key, 0)
        previous = self.last_seen.get(key)

        if previous is None or timestamp < previous or (timestamp - previous) > self.gap:
            current += 1
            self.counters[key] = current

        self.last_seen[key] = timestamp
        prefix = hashlib.sha1(f"{ip}|{user_agent}".encode("utf-8")).hexdigest()[:8]
        return f"sess-{prefix}-{current:04d}"


@dataclass
class ReplayStats:
    files_scanned: int = 0
    lines_seen: int = 0
    parsed_lines: int = 0
    skipped_lines: int = 0


def discover_log_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]

    candidates = sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and (
            path.suffix.lower() in {".log", ".txt", ".gz"}
            or "access" in path.name.lower()
            or "log" in path.name.lower()
        )
    )

    if candidates:
        return candidates

    fallback = sorted(path for path in root.rglob("*") if path.is_file())
    if fallback:
        return fallback
    raise FileNotFoundError(f"No log files found under {root}")


def infer_route_template(endpoint: str) -> str:
    if endpoint == "/":
        return endpoint

    parts = []
    for segment in endpoint.strip("/").split("/"):
        if SIZE_SEGMENT_PATTERN.fullmatch(segment):
            parts.append("{size}")
        elif ID_SEGMENT_PATTERN.fullmatch(segment) or HEXISH_SEGMENT_PATTERN.fullmatch(segment):
            parts.append("{id}")
        else:
            parts.append(segment)
    return "/" + "/".join(parts)


def infer_latency_ms(endpoint: str, status: int, user_agent: str) -> int:
    tokens = {segment.lower() for segment in endpoint.split("/") if segment}
    base = 120

    if tokens & {"image", "images", "img", "media", "static", "productmodel", "article"}:
        base = 55
    elif tokens & {"search", "filter", "category", "products", "product"}:
        base = 140
    elif tokens & {"login", "auth", "signin", "register"}:
        base = 260
    elif tokens & {"cart", "basket", "profile", "account"}:
        base = 190
    elif tokens & {"orders", "order", "checkout", "payment"}:
        base = 900
    elif tokens & {"admin", "users", "user"}:
        base = 320

    if status >= 500:
        base += 1700
    elif status == 429:
        base += 350
    elif status >= 400:
        base += 140

    user_agent_lc = user_agent.lower()
    if any(signature in user_agent_lc for signature in BOT_SIGNATURES) and status < 500:
        base = max(35, base - 25)

    depth_penalty = max(0, len(tokens) - 2) * 12
    jitter_seed = hashlib.sha1(f"{endpoint}|{status}|{user_agent}".encode("utf-8")).hexdigest()
    jitter = int(jitter_seed[:6], 16) % 180
    return base + depth_penalty + jitter


def normalize_endpoint(request_target: str) -> str:
    split_target = urlsplit(request_target)
    endpoint = unquote(split_target.path or request_target)

    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint.lstrip("/")

    return endpoint or "/"


def parse_access_log_line(
    line: str,
    sessionizer: Sessionizer,
    cycle: int = 0,
) -> tuple[datetime, dict[str, object]] | None:
    match = LOG_PATTERN.match(line.strip())
    if not match:
        return None

    request = match.group("request")
    request_parts = request.split()
    if len(request_parts) < 2:
        return None

    method = request_parts[0].upper()
    if method not in ALLOWED_METHODS:
        return None

    request_target = request_parts[1]
    timestamp = datetime.strptime(match.group("timestamp"), "%d/%b/%Y:%H:%M:%S %z").astimezone(
        timezone.utc
    )
    ip = match.group("ip")
    user_agent = (match.group("user_agent") or "unknown").strip() or "unknown"
    endpoint = normalize_endpoint(request_target)
    route_template = infer_route_template(endpoint)
    status = int(match.group("status"))
    session_id = sessionizer.assign(ip, user_agent, timestamp)
    request_key = "|".join(
        [
            str(cycle),
            timestamp.isoformat(),
            ip,
            method,
            request_target,
            str(status),
            user_agent,
        ]
    )
    request_id = f"req-{hashlib.sha1(request_key.encode('utf-8')).hexdigest()[:16]}"

    return timestamp, {
        "schema_version": "v2",
        "timestamp": "",
        "request_id": request_id,
        "session_id": session_id,
        "ip": ip,
        "user_agent": user_agent,
        "method": method,
        "endpoint": endpoint,
        "route_template": route_template,
        "status": status,
        "latency_ms": infer_latency_ms(endpoint, status, user_agent),
    }


def _read_lines(path: Path):
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        yield from handle


def iter_normalized_records(
    log_paths: list[Path],
    sessionizer: Sessionizer,
    cycle: int,
    stats: ReplayStats,
):
    for path in log_paths:
        stats.files_scanned += 1
        for line in _read_lines(path):
            stats.lines_seen += 1
            parsed = parse_access_log_line(line, sessionizer, cycle=cycle)
            if parsed is None:
                stats.skipped_lines += 1
                continue
            stats.parsed_lines += 1
            yield parsed


def connect_kafka(bootstrap_servers: str) -> KafkaProducer:
    try:
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers.split(","),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
            retries=3,
        )
        return producer
    except NoBrokersAvailable as exc:
        raise RuntimeError(
            f"Kafka is not available at {bootstrap_servers}. Replay fail-fast."
        ) from exc


def flush_kafka_with_backoff(
    producer: KafkaProducer,
    settings: ReplaySettings,
    stage: str,
) -> None:
    attempts = max(3, 1)
    backoff_seconds = 2.0

    for attempt in range(1, attempts + 1):
        try:
            producer.flush(timeout=settings.flush_timeout_seconds)
            return
        except Exception as exc:
            if attempt >= attempts:
                raise RuntimeError(
                    "Kafka flush timed out while replaying access logs. "
                    "Reduce replay speed with a lower --time-scale, increase "
                    "--flush-every, or speed up the stream processor."
                ) from exc

            print(
                "Replay flush timed out "
                f"(stage={stage}, attempt={attempt}/{attempts}). "
                f"Backing off for {backoff_seconds:.1f}s before retry."
            )
            time.sleep(backoff_seconds)


def replay_access_logs(settings: ReplaySettings) -> None:
    log_paths = discover_log_files(settings.input_dir)
    output_handle: TextIO | None = None
    producer: KafkaProducer | None = None
    cycle = 0
    total_published = 0
    total_written = 0
    stats = ReplayStats()

    if not settings.publish and settings.output_jsonl is None:
        raise ValueError("Choose at least one output: publish to Kafka or write --output-jsonl.")
    if settings.time_scale <= 0:
        raise ValueError("--time-scale must be greater than zero.")
    if settings.flush_every <= 0:
        raise ValueError("--flush-every must be greater than zero.")
    if settings.progress_every <= 0:
        raise ValueError("--progress-every must be greater than zero.")

    try:
        if settings.output_jsonl is not None:
            settings.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
            output_handle = settings.output_jsonl.open("w", encoding="utf-8")

        if settings.publish:
            producer = connect_kafka(settings.bootstrap_servers)

        print(
            "Starting access-log replay from "
            f"{settings.input_dir} "
            f"(files={len(log_paths)}, publish={settings.publish}, "
            f"output_jsonl={bool(settings.output_jsonl)}, time_scale={settings.time_scale})."
        )

        while True:
            cycle_anchor = datetime.now(timezone.utc)
            first_original: datetime | None = None
            sessionizer = Sessionizer(gap=timedelta(minutes=settings.session_gap_minutes))
            cycle_count = 0

            for original_timestamp, record in iter_normalized_records(log_paths, sessionizer, cycle, stats):
                if first_original is None:
                    first_original = original_timestamp

                delta_seconds = (
                    original_timestamp - first_original
                ).total_seconds() / settings.time_scale
                scheduled_timestamp = cycle_anchor + timedelta(seconds=max(delta_seconds, 0.0))
                sleep_seconds = (scheduled_timestamp - datetime.now(timezone.utc)).total_seconds()
                if sleep_seconds > 0:
                    time.sleep(sleep_seconds)

                record["timestamp"] = _isoformat(scheduled_timestamp)
                payload = json.dumps(record, ensure_ascii=False)

                if output_handle is not None:
                    output_handle.write(payload + "\n")
                    total_written += 1

                if producer is not None:
                    producer.send(settings.topic, value=record)
                    total_published += 1
                    if total_published % settings.flush_every == 0:
                        flush_kafka_with_backoff(
                            producer,
                            settings,
                            stage=f"periodic-{total_published}",
                        )

                cycle_count += 1
                if cycle_count % settings.progress_every == 0:
                    if producer is not None:
                        flush_kafka_with_backoff(
                            producer,
                            settings,
                            stage=f"progress-{cycle + 1}-{cycle_count}",
                        )
                    if output_handle is not None:
                        output_handle.flush()
                    print(
                        "Replay progress: "
                        f"cycle={cycle + 1} records={cycle_count} "
                        f"published={total_published} written={total_written} "
                        f"last_timestamp={record['timestamp']}"
                    )
                if settings.max_records and max(total_published, total_written) >= settings.max_records:
                    break

            if producer is not None:
                flush_kafka_with_backoff(
                    producer,
                    settings,
                    stage=f"cycle-end-{cycle + 1}",
                )
            if output_handle is not None:
                output_handle.flush()

            if cycle_count == 0:
                raise RuntimeError(f"No supported access-log lines were parsed from {settings.input_dir}")

            print(
                "Replayed "
                f"{cycle_count} normalized access logs from {len(log_paths)} files "
                f"(skipped={stats.skipped_lines}, parsed={stats.parsed_lines})."
            )

            if settings.max_records and max(total_published, total_written) >= settings.max_records:
                break
            if not settings.repeat:
                break
            cycle += 1
    finally:
        if output_handle is not None:
            output_handle.close()
        if producer is not None:
            producer.close()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Replay Kaggle-style combined access logs as v2 raw logs."
    )
    parser.add_argument(
        "--input-dir",
        default=os.getenv("GENERATOR_SOURCE_DIR"),
        help="Directory or single file returned by kagglehub.dataset_download(...).",
    )
    parser.add_argument(
        "--time-scale",
        type=float,
        default=float(os.getenv("GENERATOR_REPLAY_TIME_SCALE", "30")),
        help="Compress original time gaps by this factor. Larger means faster replay.",
    )
    parser.add_argument(
        "--session-gap-minutes",
        type=int,
        default=int(os.getenv("GENERATOR_SESSION_GAP_MINUTES", "15")),
        help="Start a new synthetic session if the same IP+UA is idle longer than this gap.",
    )
    parser.add_argument(
        "--flush-every",
        type=int,
        default=int(os.getenv("GENERATOR_REPLAY_FLUSH_EVERY", "1000")),
        help="Flush to Kafka after this many published records.",
    )
    parser.add_argument(
        "--flush-timeout-seconds",
        type=int,
        default=int(os.getenv("GENERATOR_REPLAY_FLUSH_TIMEOUT_SECONDS", "30")),
        help="Timeout for each Kafka flush attempt.",
    )
    parser.add_argument(
        "--flush-retry-attempts",
        type=int,
        default=int(os.getenv("GENERATOR_REPLAY_FLUSH_RETRY_ATTEMPTS", "3")),
        help="Retry count when a Kafka flush times out.",
    )
    parser.add_argument(
        "--flush-retry-backoff-seconds",
        type=float,
        default=float(os.getenv("GENERATOR_REPLAY_FLUSH_RETRY_BACKOFF_SECONDS", "2")),
        help="Sleep this many seconds before retrying a timed out Kafka flush.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=int(os.getenv("GENERATOR_REPLAY_PROGRESS_EVERY", "1000")),
        help="Print replay progress after this many normalized records.",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=int(os.getenv("GENERATOR_REPLAY_MAX_RECORDS", "0")),
        help="Optional cap for dry-runs or demos. Zero means no cap.",
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        help="Optional path to write normalized v2 raw logs as JSONL.",
    )
    parser.add_argument(
        "--skip-publish",
        action="store_true",
        help="Only write JSONL output instead of publishing to Kafka.",
    )
    parser.add_argument(
        "--repeat",
        action="store_true",
        help="Loop over the dataset forever, useful when replacing the demo generator.",
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    if not args.input_dir:
        raise SystemExit("--input-dir is required.")

    settings = ReplaySettings(
        input_dir=Path(args.input_dir).expanduser().resolve(),
        time_scale=args.time_scale,
        session_gap_minutes=args.session_gap_minutes,
        flush_every=args.flush_every,
        progress_every=args.progress_every,
        max_records=args.max_records,
        output_jsonl=args.output_jsonl,
        publish=not args.skip_publish,
        repeat=args.repeat,
    )
    replay_access_logs(settings)


if __name__ == "__main__":
    main()
