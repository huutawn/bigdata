from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_BOT_IPS = {"1.1.1.1", "1.2.3.4"}
DEFAULT_ANOMALY_THRESHOLD_MS = 3000
DEFAULT_BASE_LOAD_DELTA = 20
DEFAULT_ANOMALY_LOAD_DELTA = 30


def has_model_artifact(models_dir: Path) -> bool:
    if not models_dir.exists():
        return False
    return any(path.is_file() and path.name != ".gitkeep" for path in models_dir.iterdir())


def load_model_config(models_dir: Path) -> dict[str, Any]:
    config_path = models_dir / "model_config.json"
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def runtime_mode(models_dir: Path) -> str:
    return "model" if has_model_artifact(models_dir) else "mock"


def analyze(ip: str, latency_ms: int, current_rps: int, models_dir: Path) -> dict[str, int | bool]:
    config = load_model_config(models_dir) if runtime_mode(models_dir) == "model" else {}
    bot_ips = set(config.get("bot_ips", DEFAULT_BOT_IPS))
    anomaly_threshold_ms = int(
        config.get("anomaly_threshold_ms", DEFAULT_ANOMALY_THRESHOLD_MS)
    )
    base_load_delta = int(config.get("base_load_delta", DEFAULT_BASE_LOAD_DELTA))
    anomaly_load_delta = int(
        config.get("anomaly_load_delta", DEFAULT_ANOMALY_LOAD_DELTA)
    )

    is_bot = ip in bot_ips
    is_anomaly = latency_ms >= anomaly_threshold_ms
    predicted_load = max(current_rps, 0) + base_load_delta + (
        anomaly_load_delta if is_anomaly else 0
    )

    return {
        "is_bot": is_bot,
        "predicted_load": predicted_load,
        "is_anomaly": is_anomaly,
    }
