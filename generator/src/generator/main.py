from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

ENDPOINTS = [
    "/api/v1/search",
    "/api/v1/login",
    "/api/v1/profile",
    "/api/v1/products",
    "/api/v1/cart",
    "/api/v1/orders",
    "/api/v1/checkout",
    "/api/v1/admin/users",
]
HUMAN_IPS = [
    "192.168.1.10",
    "192.168.1.11",
    "10.10.0.5",
    "10.10.0.6",
    "172.16.2.44",
]
BOT_IPS = [
    "1.2.3.4",
    "1.1.1.1",
    "66.249.66.1",
    "203.0.113.42",
]
HUMAN_USER_AGENTS = [
    "Mozilla/5.0",
    "Mozilla/5.0 (Mobile)",
    "Mozilla/5.0 (X11; Linux x86_64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X)",
]
BOT_USER_AGENTS = [
    "Googlebot/2.1",
    "curl/8.6.0",
    "python-requests/2.32.3",
    "Bingbot/2.0",
    "sqlmap/1.8.3",
]
METHODS_BY_ROUTE = {
    "/api/v1/search": ["GET"],
    "/api/v1/login": ["POST"],
    "/api/v1/profile": ["GET", "PATCH"],
    "/api/v1/products": ["GET", "HEAD"],
    "/api/v1/cart": ["GET", "POST", "DELETE"],
    "/api/v1/orders": ["POST", "GET", "PATCH"],
    "/api/v1/checkout": ["POST"],
    "/api/v1/admin/users": ["GET", "PATCH", "DELETE"],
}
LOAD_PROFILE = [
    3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22,
    20, 18, 16, 13, 10, 8, 6, 5, 4, 3, 2, 2,
    3, 5, 8, 12, 17, 11, 7, 4,
]
LOAD_PROFILE_JITTER = [0, 1, 0, -1, 0, 1, -1, 0]


@dataclass(frozen=True)
class GeneratorSettings:
    bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094")
    topic: str = os.getenv("KAFKA_TOPIC", "logs.raw")
    batch_size: int = int(os.getenv("GENERATOR_BATCH_SIZE", "50"))
    publish_interval_seconds: int = int(
        os.getenv("GENERATOR_PUBLISH_INTERVAL_SECONDS", "3")
    )
    seed: int = int(os.getenv("GENERATOR_SEED", "7"))
    connect_timeout_seconds: int = int(os.getenv("GENERATOR_KAFKA_TIMEOUT_SECONDS", "10"))


def _isoformat(timestamp: datetime) -> str:
    return timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _pick(values: list[str], rng: random.Random, index: int) -> str:
    return values[(index + rng.randint(0, len(values) - 1)) % len(values)]


def _build_timestamp(
    index: int,
    base_time: datetime | None = None,
    event_time: datetime | None = None,
) -> str:
    if event_time is None:
        event_time = (base_time or datetime.now(timezone.utc)) + timedelta(seconds=index * 3)
    return _isoformat(event_time)


def build_log(
    index: int,
    rng: random.Random,
    base_time: datetime | None = None,
    event_time: datetime | None = None,
) -> dict[str, object]:
    phase = index % 24

    if phase in {0, 1, 2, 3, 4}:
        endpoint = _pick(["/api/v1/products", "/api/v1/search"], rng, index)
        method = "HEAD" if phase == 4 else "GET"
        ip = BOT_IPS[index % len(BOT_IPS)]
        user_agent = _pick(BOT_USER_AGENTS, rng, index)
        status = [200, 200, 200, 404, 429][phase]
        latency_ms = 55 + phase * 18 + rng.randint(0, 45)
        session_id = f"sess-bot-{index // 5:03d}"
    elif phase in {5, 6, 7}:
        endpoint = "/api/v1/login"
        method = "POST"
        ip = BOT_IPS[(index + 1) % len(BOT_IPS)]
        user_agent = _pick(BOT_USER_AGENTS, rng, index + 7)
        status = [401, 403, 429][phase - 5]
        latency_ms = 110 + (phase - 5) * 90 + rng.randint(0, 120)
        session_id = f"sess-probe-{index // 3:03d}"
    elif phase in {8, 9, 10}:
        endpoint = "/api/v1/orders" if phase != 9 else "/api/v1/checkout"
        method = ["POST", "POST", "PATCH"][phase - 8]
        ip = HUMAN_IPS[index % len(HUMAN_IPS)]
        user_agent = _pick(HUMAN_USER_AGENTS, rng, index)
        status = [500, 503, 504][phase - 8]
        latency_ms = 1900 + (phase - 8) * 850 + rng.randint(200, 900)
        session_id = f"sess-incident-{index // 3:03d}"
    elif phase in {11, 12, 13, 14, 15}:
        endpoint = _pick(
            ["/api/v1/products", "/api/v1/search", "/api/v1/cart", "/api/v1/profile"],
            rng,
            index,
        )
        method = _pick(METHODS_BY_ROUTE[endpoint], rng, index + 3)
        ip = HUMAN_IPS[index % len(HUMAN_IPS)]
        user_agent = _pick(HUMAN_USER_AGENTS, rng, index + 11)
        status = [200, 200, 201, 204, 302][phase - 11]
        latency_ms = 70 + (phase - 11) * 45 + rng.randint(0, 150)
        session_id = f"sess-user-{index % 17:03d}"
    elif phase in {16, 17, 18}:
        endpoint = _pick(["/api/v1/products", "/api/v1/cart", "/api/v1/profile"], rng, index)
        method = _pick(METHODS_BY_ROUTE[endpoint], rng, index + 5)
        ip = HUMAN_IPS[(index + 2) % len(HUMAN_IPS)]
        user_agent = _pick(HUMAN_USER_AGENTS[1:], rng, index)
        status = [200, 302, 408][phase - 16]
        latency_ms = 150 + (phase - 16) * 210 + rng.randint(20, 260)
        session_id = f"sess-mobile-{index % 11:03d}"
    elif phase in {19, 20, 21}:
        endpoint = "/api/v1/admin/users"
        method = ["GET", "PATCH", "DELETE"][phase - 19]
        ip = _pick(HUMAN_IPS + BOT_IPS, rng, index)
        user_agent = _pick(BOT_USER_AGENTS if phase == 21 else HUMAN_USER_AGENTS, rng, index)
        status = [200, 409, 403][phase - 19]
        latency_ms = 180 + (phase - 19) * 120 + rng.randint(0, 240)
        session_id = f"sess-admin-{index // 3:03d}"
    else:
        endpoint = _pick(ENDPOINTS, rng, index)
        method = _pick(METHODS_BY_ROUTE[endpoint], rng, index + 9)
        ip = _pick(HUMAN_IPS + BOT_IPS, rng, index)
        user_agent = _pick(HUMAN_USER_AGENTS + BOT_USER_AGENTS, rng, index)
        status = _pick(["200", "201", "302", "400", "404"], rng, index)
        latency_ms = 90 + rng.randint(0, 520)
        session_id = f"sess-mixed-{index % 13:03d}"

    return {
        "schema_version": "v2",
        "timestamp": _build_timestamp(index, base_time=base_time, event_time=event_time),
        "request_id": f"req-{index:06d}",
        "session_id": session_id,
        "ip": ip,
        "user_agent": user_agent,
        "method": method,
        "endpoint": endpoint,
        "route_template": endpoint,
        "status": int(status),
        "latency_ms": latency_ms,
    }


def _resolve_batch_size(settings: GeneratorSettings, publish_index: int) -> int:
    base = max(settings.batch_size, 1)
    scale = base / 50.0
    profile_value = LOAD_PROFILE[publish_index % len(LOAD_PROFILE)]
    jitter = LOAD_PROFILE_JITTER[publish_index % len(LOAD_PROFILE_JITTER)]
    return max(1, int(round(profile_value * scale)) + jitter)


def _build_batch(
    publish_index: int,
    cursor: int,
    batch_size: int,
    rng: random.Random,
    publish_time: datetime,
) -> list[dict[str, object]]:
    mode = publish_index % 4
    current_time = publish_time - timedelta(seconds=max(batch_size * 2, 6))
    logs: list[dict[str, object]] = []

    for offset in range(batch_size):
        if mode == 0:
            step_seconds = [0, 0, 1, 1, 2][(offset + rng.randint(0, 4)) % 5]
        elif mode == 1:
            step_seconds = [1, 2, 2, 3, 5][(offset + rng.randint(0, 4)) % 5]
        elif mode == 2:
            step_seconds = [0, 1, 4, 0, 6][(offset + rng.randint(0, 4)) % 5]
        else:
            step_seconds = [2, 3, 1, 4, 2][(offset + rng.randint(0, 4)) % 5]
        current_time += timedelta(seconds=step_seconds)
        logs.append(build_log(cursor + offset, rng, event_time=current_time))

    return logs


def connect_kafka(bootstrap_servers: str, timeout_seconds: int) -> KafkaProducer:
    try:
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers.split(","),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
            retries=3,
            request_timeout_ms=timeout_seconds * 1000,
            max_block_ms=timeout_seconds * 1000,
        )
        return producer
    except NoBrokersAvailable as exc:
        raise RuntimeError(
            f"Kafka is not available at {bootstrap_servers}. Generator fail-fast."
        ) from exc


def publish_loop(settings: GeneratorSettings) -> None:
    producer = connect_kafka(settings.bootstrap_servers, settings.connect_timeout_seconds)
    rng = random.Random(settings.seed)
    cursor = 0
    publish_index = 0

    try:
        while True:
            batch_size = _resolve_batch_size(settings, publish_index)
            logs = _build_batch(publish_index, cursor, batch_size, rng, datetime.now(timezone.utc))
            for log in logs:
                producer.send(settings.topic, value=log)
            producer.flush()
            print(f"Published {len(logs)} v2 raw logs to topic '{settings.topic}'")
            cursor += batch_size
            publish_index += 1
            time.sleep(settings.publish_interval_seconds)
    except KeyboardInterrupt:
        print("Generator interrupted.")
    finally:
        producer.close()


def main() -> None:
    settings = GeneratorSettings()
    publish_loop(settings)


if __name__ == "__main__":
    main()
