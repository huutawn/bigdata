from __future__ import annotations

import asyncio
import json
import os
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


ENDPOINTS = [
    "/api/v1/login",
    "/api/v1/products",
    "/api/v1/cart",
    "/api/v1/orders",
]
HUMAN_IPS = [
    "192.168.1.10",
    "192.168.1.11",
    "10.10.0.5",
]
BOT_IPS = [
    "1.2.3.4",
    "1.1.1.1",
]
HUMAN_USER_AGENTS = [
    "Mozilla/5.0",
    "Mozilla/5.0 (Mobile)",
    "Mozilla/5.0 (X11; Linux x86_64)",
]
BOT_USER_AGENTS = [
    "Googlebot/2.1",
    "curl/8.6.0",
]
METHODS_BY_ROUTE = {
    "/api/v1/login": ["POST"],
    "/api/v1/products": ["GET", "HEAD"],
    "/api/v1/cart": ["GET", "POST"],
    "/api/v1/orders": ["POST", "GET"],
}


@dataclass(frozen=True)
class GeneratorSettings:
    nats_url: str = os.getenv("NATS_URL", "nats://localhost:4222")
    subject: str = os.getenv("NATS_SUBJECT", "logs.raw")
    batch_size: int = int(os.getenv("GENERATOR_BATCH_SIZE", "5"))
    publish_interval_seconds: int = int(
        os.getenv("GENERATOR_PUBLISH_INTERVAL_SECONDS", "3")
    )
    seed: int = int(os.getenv("GENERATOR_SEED", "7"))


def _isoformat(timestamp: datetime) -> str:
    return timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_log(
    index: int,
    rng: random.Random,
    base_time: datetime | None = None,
) -> dict[str, object]:
    timestamp = (base_time or datetime.now(timezone.utc)) + timedelta(seconds=index * 3)
    phase = index % 12

    if phase in {0, 1, 2, 3}:
        endpoint = "/api/v1/products"
        method = "GET" if phase != 3 else "HEAD"
        ip = BOT_IPS[index % len(BOT_IPS)]
        user_agent = BOT_USER_AGENTS[index % len(BOT_USER_AGENTS)]
        status = 404 if phase == 3 else 200
        latency_ms = 70 + phase * 10
        session_id = f"sess-bot-{index // 4:03d}"
    elif phase in {4, 5}:
        endpoint = "/api/v1/orders"
        method = "POST"
        ip = HUMAN_IPS[index % len(HUMAN_IPS)]
        user_agent = HUMAN_USER_AGENTS[index % len(HUMAN_USER_AGENTS)]
        status = 500 if phase == 4 else 504
        latency_ms = 3200 + phase * 100
        session_id = f"sess-incident-{index // 2:03d}"
    else:
        endpoint = ENDPOINTS[(index + rng.randint(0, len(ENDPOINTS) - 1)) % len(ENDPOINTS)]
        method_choices = METHODS_BY_ROUTE[endpoint]
        method = method_choices[(index + rng.randint(0, len(method_choices) - 1)) % len(method_choices)]
        ip = HUMAN_IPS[index % len(HUMAN_IPS)]
        user_agent = HUMAN_USER_AGENTS[index % len(HUMAN_USER_AGENTS)]
        status = [200, 200, 201, 302][index % 4]
        latency_ms = 90 + (index % 5) * 35 + rng.randint(0, 25)
        session_id = f"sess-user-{index % 9:03d}"

    return {
        "schema_version": "v2",
        "timestamp": _isoformat(timestamp),
        "request_id": f"req-{index:06d}",
        "session_id": session_id,
        "ip": ip,
        "user_agent": user_agent,
        "method": method,
        "endpoint": endpoint,
        "route_template": endpoint,
        "status": status,
        "latency_ms": latency_ms,
    }


async def connect_nats(nats_url: str):
    try:
        import nats
    except ModuleNotFoundError as exc:
        raise RuntimeError("Missing dependency nats-py. Install generator requirements.") from exc

    return await nats.connect(nats_url)


async def publish_loop(settings: GeneratorSettings) -> None:
    nc = await connect_nats(settings.nats_url)
    rng = random.Random(settings.seed)
    cursor = 0

    try:
        while True:
            logs = [build_log(cursor + offset, rng) for offset in range(settings.batch_size)]
            for log in logs:
                await nc.publish(settings.subject, json.dumps(log).encode("utf-8"))
            await nc.flush()
            print(f"Published {len(logs)} v2 raw logs to {settings.subject}")
            cursor += settings.batch_size
            await asyncio.sleep(settings.publish_interval_seconds)
    finally:
        await nc.close()


def main() -> None:
    settings = GeneratorSettings()
    asyncio.run(publish_loop(settings))


if __name__ == "__main__":
    main()
