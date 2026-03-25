from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, Field

from ml_api.analyzer import analyze, runtime_mode


@dataclass(frozen=True)
class Settings:
    models_dir: Path = Path(os.getenv("ML_MODELS_DIR", str(Path(__file__).resolve().parents[2] / "models")))


class AnalyzeRequest(BaseModel):
    ip: str = Field(min_length=7)
    latency_ms: int = Field(ge=0)
    current_rps: int = Field(ge=0)


class AnalyzeResponse(BaseModel):
    is_bot: bool
    predicted_load: int = Field(ge=0)
    is_anomaly: bool


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings()
    app = FastAPI(title="AIOps ML API", version="0.1.0")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "mode": runtime_mode(resolved_settings.models_dir)}

    @app.post("/analyze", response_model=AnalyzeResponse)
    def analyze_endpoint(payload: AnalyzeRequest) -> AnalyzeResponse:
        result = analyze(
            ip=payload.ip,
            latency_ms=payload.latency_ms,
            current_rps=payload.current_rps,
            models_dir=resolved_settings.models_dir,
        )
        return AnalyzeResponse(**result)

    return app


app = create_app()
