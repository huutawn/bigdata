from __future__ import annotations


BOT_IPS = {"1.1.1.1", "1.2.3.4"}
ANOMALY_THRESHOLD_MS = 3000
BASE_LOAD_DELTA = 20
ANOMALY_LOAD_DELTA = 30


def analyze(ip: str, latency_ms: int, current_rps: int) -> dict[str, int | bool]:
    is_bot = ip in BOT_IPS
    is_anomaly = latency_ms >= ANOMALY_THRESHOLD_MS
    predicted_load = max(current_rps, 0) + BASE_LOAD_DELTA + (
        ANOMALY_LOAD_DELTA if is_anomaly else 0
    )
    return {
        "is_bot": is_bot,
        "predicted_load": predicted_load,
        "is_anomaly": is_anomaly,
    }
