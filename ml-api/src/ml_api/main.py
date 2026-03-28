from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, Field

from ml_api.analyzer import predict_anomaly, predict_bot, predict_forecast, runtime_mode


@dataclass(frozen=True)
class Settings:
    models_dir: Path = Path(
        os.getenv("ML_MODELS_DIR", str(Path(__file__).resolve().parents[2] / "models"))
    )


class BotEntity(BaseModel):
    ip: str = Field(min_length=7)
    session_id: str = Field(min_length=1)
    user_agent: str = Field(min_length=1)


class BotFeatures(BaseModel):
    number_of_requests: int = Field(ge=0)
    total_duration_s: float = Field(ge=0)
    average_time_ms: float = Field(ge=0)
    repeated_requests: float = Field(ge=0, le=1)
    http_response_2xx: float = Field(ge=0, le=1)
    http_response_3xx: float = Field(ge=0, le=1)
    http_response_4xx: float = Field(ge=0, le=1)
    http_response_5xx: float = Field(ge=0, le=1)
    get_method: float = Field(ge=0, le=1)
    post_method: float = Field(ge=0, le=1)
    head_method: float = Field(ge=0, le=1)
    other_method: float = Field(ge=0, le=1)
    night: int = Field(ge=0, le=1)
    max_barrage: int = Field(ge=0)


class BotRequest(BaseModel):
    feature_version: str = Field(min_length=1)
    window_start: str = Field(min_length=1)
    window_end: str = Field(min_length=1)
    entity: BotEntity
    features: BotFeatures


class BotResponse(BaseModel):
    is_bot: bool
    bot_score: float = Field(ge=0, le=1)
    model_version: str = Field(min_length=1)


class ForecastTarget(BaseModel):
    scope: str = Field(pattern="^(system|endpoint)$")
    endpoint: str


class ForecastFeatures(BaseModel):
    rolling_mean_5: float = Field(ge=0)
    rolling_std_5: float = Field(ge=0)
    hour_of_day: int = Field(ge=0, le=23)
    day_of_week: int = Field(ge=0, le=6)


class ForecastRequest(BaseModel):
    feature_version: str = Field(min_length=1)
    bucket_end: str = Field(min_length=1)
    target: ForecastTarget
    history_rps: list[int] = Field(min_length=1)
    features: ForecastFeatures


class ForecastResponse(BaseModel):
    predicted_request_count: int = Field(ge=0)
    model_version: str = Field(min_length=1)


class AnomalyEntity(BaseModel):
    endpoint: str = Field(min_length=1)


class AnomalyFeatures(BaseModel):
    request_count: int = Field(ge=0)
    avg_latency_ms: float = Field(ge=0)
    p95_latency_ms: float = Field(ge=0)
    p99_latency_ms: float = Field(ge=0)
    status_5xx_ratio: float = Field(ge=0, le=1)
    baseline_avg_latency_ms: float = Field(ge=0)
    baseline_5xx_ratio: float = Field(ge=0, le=1)


class AnomalyRequest(BaseModel):
    feature_version: str = Field(min_length=1)
    window_start: str = Field(min_length=1)
    window_end: str = Field(min_length=1)
    entity: AnomalyEntity
    features: AnomalyFeatures


class AnomalyResponse(BaseModel):
    is_anomaly: bool
    anomaly_score: float = Field(ge=0, le=1)
    model_version: str = Field(min_length=1)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings()
    app = FastAPI(title="AIOps ML API", version="0.2.0")

    @app.get("/healthz")
    def healthz() -> dict[str, object]:
        return {
            "status": "ok",
            "mode": runtime_mode(resolved_settings.models_dir),
            "tasks": ["bot", "forecast", "anomaly"],
        }

    @app.post("/predict/bot", response_model=BotResponse)
    def predict_bot_endpoint(payload: BotRequest) -> BotResponse:
        result = predict_bot(payload.model_dump(), resolved_settings.models_dir)
        return BotResponse(**result)

    @app.post("/predict/forecast", response_model=ForecastResponse)
    def predict_forecast_endpoint(payload: ForecastRequest) -> ForecastResponse:
        result = predict_forecast(payload.model_dump(), resolved_settings.models_dir)
        return ForecastResponse(**result)

    @app.post("/predict/anomaly", response_model=AnomalyResponse)
    def predict_anomaly_endpoint(payload: AnomalyRequest) -> AnomalyResponse:
        result = predict_anomaly(payload.model_dump(), resolved_settings.models_dir)
        return AnomalyResponse(**result)

    return app


app = create_app()
