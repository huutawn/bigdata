from __future__ import annotations

from typing import Any


BOT_IPS = {"1.1.1.1", "1.2.3.4"}
BOT_THRESHOLD = 0.55
ANOMALY_THRESHOLD = 0.6
FORECAST_SMOOTHING = 0.2


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def predict_bot(payload: dict[str, Any]) -> dict[str, Any]:
    entity = payload["entity"]
    features = payload["features"]
    user_agent = entity["user_agent"].lower()
    suspicious_agent = any(token in user_agent for token in ("bot", "crawler", "spider", "curl"))

    score = 0.0
    score += min(features["number_of_requests"] / 50.0, 0.25)
    score += clamp(features["repeated_requests"]) * 0.25
    score += clamp(features["http_response_4xx"]) * 0.15
    score += clamp(features["http_response_5xx"]) * 0.10
    score += min(features["max_barrage"] / 20.0, 0.10)
    score += 0.10 if features["night"] else 0.0
    score += 0.15 if suspicious_agent else 0.0
    score += 0.15 if entity["ip"] in BOT_IPS else 0.0

    bot_score = round(clamp(score), 4)
    return {
        "is_bot": bot_score >= BOT_THRESHOLD,
        "bot_score": bot_score,
        "model_version": "mock-bot-v2",
    }


def predict_forecast(payload: dict[str, Any]) -> dict[str, Any]:
    history = payload["history_rps"]
    features = payload["features"]
    current = history[-1]
    previous = history[-2] if len(history) > 1 else current
    rolling_mean = float(features["rolling_mean_5"])
    rolling_std = float(features["rolling_std_5"])
    trend = max(current - previous, 0)
    predicted = current + trend + int(round(rolling_mean * FORECAST_SMOOTHING + rolling_std * 0.1))
    predicted = max(predicted, current)
    return {
        "predicted_request_count": int(predicted),
        "model_version": "mock-forecast-v2",
    }


def predict_anomaly(payload: dict[str, Any]) -> dict[str, Any]:
    features = payload["features"]
    baseline_latency = max(float(features["baseline_avg_latency_ms"]), 1.0)
    baseline_5xx = float(features["baseline_5xx_ratio"])
    latency_ratio = float(features["avg_latency_ms"]) / baseline_latency
    p95_ratio = float(features["p95_latency_ms"]) / baseline_latency
    p99_ratio = float(features["p99_latency_ms"]) / baseline_latency
    error_delta = max(float(features["status_5xx_ratio"]) - baseline_5xx, 0.0)

    score = 0.0
    score += clamp((latency_ratio - 1.0) / 2.0) * 0.35
    score += clamp((p95_ratio - 1.0) / 4.0) * 0.25
    score += clamp((p99_ratio - 1.0) / 6.0) * 0.20
    score += clamp(error_delta * 4.0) * 0.20

    anomaly_score = round(clamp(score), 4)
    return {
        "is_anomaly": anomaly_score >= ANOMALY_THRESHOLD or p99_ratio >= 8.0,
        "anomaly_score": anomaly_score,
        "model_version": "mock-anomaly-v2",
    }
