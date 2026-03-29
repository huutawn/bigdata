from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_BOT_IPS = {"1.1.1.1", "1.2.3.4"}
DEFAULT_BOT_THRESHOLD = 0.55
DEFAULT_ANOMALY_THRESHOLD = 0.6
DEFAULT_FORECAST_SMOOTHING = 0.2
BOT_MODEL_FILENAME = "bot_model.joblib"
FORECAST_MODEL_FILENAME = "forecast_model.joblib"
BOT_MODEL_FEATURE_MAP = {
    "NUMBER_OF_REQUESTS": "number_of_requests",
    "TOTAL_DURATION": "total_duration_s",
    "AVERAGE_TIME": "average_time_ms",
    "REPEATED_REQUESTS": "repeated_requests",
    "HTTP_RESPONSE_2XX": "http_response_2xx",
    "HTTP_RESPONSE_3XX": "http_response_3xx",
    "HTTP_RESPONSE_4XX": "http_response_4xx",
    "HTTP_RESPONSE_5XX": "http_response_5xx",
    "GET_METHOD": "get_method",
    "POST_METHOD": "post_method",
    "HEAD_METHOD": "head_method",
    "OTHER_METHOD": "other_method",
    "NIGHT": "night",
    "MAX_BARRAGE": "max_barrage",
}
FORECAST_MODEL_CONFIG_FILENAME = "forecast_model_config.json"


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


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


def _config(models_dir: Path) -> dict[str, Any]:
    return load_model_config(models_dir) if runtime_mode(models_dir) == "model" else {}


def _model_version(task: str, models_dir: Path) -> str:
    prefix = "model" if runtime_mode(models_dir) == "model" else "mock"
    return f"{prefix}-{task}-v2"


def _predict_bot_mock(payload: dict[str, Any], models_dir: Path) -> dict[str, Any]:
    config = _config(models_dir)
    bot_ips = set(config.get("bot_ips", DEFAULT_BOT_IPS))
    threshold = float(config.get("bot_threshold", DEFAULT_BOT_THRESHOLD))
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
    score += 0.15 if entity["ip"] in bot_ips else 0.0

    bot_score = round(clamp(score), 4)
    return {
        "is_bot": bot_score >= threshold,
        "bot_score": bot_score,
        "model_version": _model_version("bot", models_dir),
    }


def _load_joblib(path: Path) -> Any:
    import joblib

    return joblib.load(path)


def _build_bot_model_vector(payload: dict[str, Any], feature_columns: list[str]) -> list[float]:
    features = payload["features"]
    vector: list[float] = []
    for column in feature_columns:
        mapped_name = BOT_MODEL_FEATURE_MAP[column]
        vector.append(float(features[mapped_name]))
    return vector


def _load_json_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def predict_bot(payload: dict[str, Any], models_dir: Path) -> dict[str, Any]:
    if runtime_mode(models_dir) != "model":
        return _predict_bot_mock(payload, models_dir)

    config = _config(models_dir)
    feature_columns = config.get("feature_columns", [])
    threshold = float(config.get("threshold", DEFAULT_BOT_THRESHOLD))
    model_path = models_dir / BOT_MODEL_FILENAME

    if not feature_columns or not model_path.exists():
        return _predict_bot_mock(payload, models_dir)

    try:
        model = _load_joblib(model_path)
        vector = _build_bot_model_vector(payload, feature_columns)
        probability = float(model.predict_proba([vector])[0][1])
        bot_score = round(clamp(probability), 4)
        return {
            "is_bot": bot_score >= threshold,
            "bot_score": bot_score,
            "model_version": _model_version("bot", models_dir),
        }
    except (ImportError, KeyError, ValueError, AttributeError):
        return _predict_bot_mock(payload, models_dir)


def predict_forecast(payload: dict[str, Any], models_dir: Path) -> dict[str, Any]:
    forecast_config = _load_json_config(models_dir / FORECAST_MODEL_CONFIG_FILENAME)
    forecast_model_path = models_dir / FORECAST_MODEL_FILENAME
    feature_columns = forecast_config.get("feature_columns", [])

    if feature_columns and forecast_model_path.exists():
        try:
            model = _load_joblib(forecast_model_path)
            history = payload["history_rps"]
            features = payload["features"]
            feature_map = {
                **{f"history_rps_{index}": float(value) for index, value in enumerate(history)},
                "rolling_mean_5": float(features["rolling_mean_5"]),
                "rolling_std_5": float(features["rolling_std_5"]),
                "hour_of_day": float(features["hour_of_day"]),
                "day_of_week": float(features["day_of_week"]),
            }
            vector = [feature_map[column] for column in feature_columns]
            predicted = float(model.predict([vector])[0])
            predicted = max(predicted, 0.0)
            return {
                "predicted_request_count": int(round(predicted)),
                "model_version": _model_version("forecast", models_dir),
            }
        except (ImportError, KeyError, ValueError, AttributeError):
            pass

    config = _config(models_dir)
    smoothing = float(config.get("forecast_smoothing", DEFAULT_FORECAST_SMOOTHING))
    history = payload["history_rps"]
    features = payload["features"]
    current = history[-1]
    previous = history[-2] if len(history) > 1 else current
    rolling_mean = float(features["rolling_mean_5"])
    rolling_std = float(features["rolling_std_5"])
    trend = max(current - previous, 0)
    predicted = current + trend + int(round(rolling_mean * smoothing + rolling_std * 0.1))
    predicted = max(predicted, current)

    return {
        "predicted_request_count": int(predicted),
        "model_version": _model_version("forecast", models_dir),
    }


def predict_anomaly(payload: dict[str, Any], models_dir: Path) -> dict[str, Any]:
    config = _config(models_dir)
    threshold = float(config.get("anomaly_threshold", DEFAULT_ANOMALY_THRESHOLD))
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
    is_anomaly = anomaly_score >= threshold or p99_ratio >= 8.0
    return {
        "is_anomaly": is_anomaly,
        "anomaly_score": anomaly_score,
        "model_version": _model_version("anomaly", models_dir),
    }
