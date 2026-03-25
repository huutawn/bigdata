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
STATUSES = [200, 200, 201, 400, 429, 500, 504]
USER_AGENTS = [
    "Mozilla/5.0",
    "Mozilla/5.0 (Mobile)",
    "Googlebot/2.1",
    "curl/8.6.0",
]
IPS = [
    "192.168.1.10",
    "192.168.1.11",
    "10.10.0.5",
    "1.2.3.4",
    "1.1.1.1",
]


@dataclass(frozen=True)
class GeneratorSettings:
    nats_url: str = os.getenv("NATS_URL", "nats://localhost:4222")
    subject: str = os.getenv("NATS_SUBJECT", "logs.raw")
    batch_size: int = int(os.getenv("GENERATOR_BATCH_SIZE", "5"))
    publish_interval_seconds: int = int(
        os.getenv("GENERATOR_PUBLISH_INTERVAL_SECONDS", "3")
    )
    seed: int = int(os.getenv("GENERATOR_SEED", "7"))


def build_log(index: int, rng: random.Random, base_time: datetime | None = None) -> dict[str, object]:
    timestamp = (base_time or datetime.now(timezone.utc)) + timedelta(seconds=index)
    endpoint = ENDPOINTS[index % len(ENDPOINTS)]
    status = STATUSES[(index + rng.randint(0, len(STATUSES) - 1)) % len(STATUSES)]
    latency = 50 + (index % 5) * 70
    if status >= 500:
        latency += 3000

    return {
        "timestamp": timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "ip": IPS[index % len(IPS)],
        "endpoint": endpoint,
        "status": status,
        "request_time_ms": latency,
        "user_agent": USER_AGENTS[index % len(USER_AGENTS)],
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
            logs = [
                build_log(cursor + offset, rng)
                for offset in range(settings.batch_size)
            ]
            for log in logs:
                await nc.publish(settings.subject, json.dumps(log).encode("utf-8"))
            await nc.flush()
            print(f"Published {len(logs)} logs to {settings.subject}")
            cursor += settings.batch_size
            await asyncio.sleep(settings.publish_interval_seconds)
    finally:
        await nc.close()


def main() -> None:
    settings = GeneratorSettings()
    asyncio.run(publish_loop(settings))


if __name__ == "__main__":
    main()
