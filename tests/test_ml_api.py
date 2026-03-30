from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_TMP = ROOT / ".local-dev" / "tmp"
sys.path.insert(0, str(ROOT / "ml-api" / "src"))

from ml_api.analyzer import predict_anomaly, predict_bot, predict_forecast, runtime_mode  # noqa: E402

try:
    from fastapi.testclient import TestClient
    from ml_api.main import Settings, create_app
except (ModuleNotFoundError, RuntimeError):
    TestClient = None
    Settings = None
    create_app = None


def make_workspace_dir(prefix: str) -> Path:
    WORKSPACE_TMP.mkdir(parents=True, exist_ok=True)
    path = WORKSPACE_TMP / f"{prefix}-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


class MlApiAnalyzerTests(unittest.TestCase):
    def test_predict_bot_is_deterministic(self) -> None:
        models_dir = make_workspace_dir("ml-api-models")
        self.addCleanup(shutil.rmtree, models_dir, ignore_errors=True)
        result = predict_bot(
            {
                "entity": {
                    "ip": "1.2.3.4",
                    "session_id": "sess-bot-1",
                    "user_agent": "Googlebot/2.1",
                },
                "features": {
                    "number_of_requests": 42,
                    "total_duration_s": 58,
                    "average_time_ms": 120,
                    "repeated_requests": 0.83,
                    "http_response_2xx": 0.76,
                    "http_response_3xx": 0.02,
                    "http_response_4xx": 0.18,
                    "http_response_5xx": 0.04,
                    "get_method": 0.91,
                    "post_method": 0.07,
                    "head_method": 0.01,
                    "other_method": 0.01,
                    "night": 0,
                    "max_barrage": 12,
                },
            },
            models_dir,
        )
        self.assertTrue(result["is_bot"])
        self.assertGreater(result["bot_score"], 0.5)

    def test_predict_forecast_and_anomaly_are_deterministic(self) -> None:
        models_dir = make_workspace_dir("ml-api-models")
        self.addCleanup(shutil.rmtree, models_dir, ignore_errors=True)
        forecast = predict_forecast(
            {
                "history_rps": [10, 12, 14, 16, 20],
                "features": {
                    "rolling_mean_5": 14.4,
                    "rolling_std_5": 3.4,
                    "hour_of_day": 10,
                    "day_of_week": 1,
                },
            },
            models_dir,
        )
        anomaly = predict_anomaly(
            {
                "features": {
                    "request_count": 30,
                    "avg_latency_ms": 480,
                    "p95_latency_ms": 1900,
                    "p99_latency_ms": 3200,
                    "status_5xx_ratio": 0.12,
                    "baseline_avg_latency_ms": 150,
                    "baseline_5xx_ratio": 0.01,
                }
            },
            models_dir,
        )
        self.assertGreaterEqual(forecast["predicted_request_count"], 20)
        self.assertTrue(anomaly["is_anomaly"])

    def test_runtime_mode_switches_when_artifact_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = Path(temp_dir)
            self.assertEqual(runtime_mode(models_dir), "mock")
            (models_dir / "model_config.json").write_text("{}", encoding="utf-8")
            self.assertEqual(runtime_mode(models_dir), "model")

    def test_predict_bot_uses_model_artifact_when_available(self) -> None:
        source_models_dir = ROOT / "ml-api" / "models"
        if not (source_models_dir / "bot_model.joblib").exists():
            self.skipTest("bot model artifact is not available")

        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = Path(temp_dir)
            (models_dir / "bot_model.joblib").write_bytes(
                (source_models_dir / "bot_model.joblib").read_bytes()
            )
            (models_dir / "model_config.json").write_text(
                (source_models_dir / "model_config.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            result = predict_bot(
                {
                    "entity": {
                        "ip": "1.2.3.4",
                        "session_id": "sess-bot-1",
                        "user_agent": "Googlebot/2.1",
                    },
                    "features": {
                        "number_of_requests": 42,
                        "total_duration_s": 58,
                        "average_time_ms": 120,
                        "repeated_requests": 0.83,
                        "http_response_2xx": 0.76,
                        "http_response_3xx": 0.02,
                        "http_response_4xx": 0.18,
                        "http_response_5xx": 0.04,
                        "get_method": 0.91,
                        "post_method": 0.07,
                        "head_method": 0.01,
                        "other_method": 0.01,
                        "night": 0,
                        "max_barrage": 12,
                    },
                },
                models_dir,
            )

        self.assertIn("bot_score", result)
        self.assertEqual(result["model_version"], "model-bot-v2")
        self.assertGreaterEqual(result["bot_score"], 0.0)
        self.assertLessEqual(result["bot_score"], 1.0)

    def test_predict_forecast_guards_small_demo_traffic_against_huge_model_output(self) -> None:
        source_models_dir = ROOT / "ml-api" / "models"
        if not (source_models_dir / "forecast_model.joblib").exists():
            self.skipTest("forecast model artifact is not available")

        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = Path(temp_dir)
            (models_dir / "forecast_model.joblib").write_bytes(
                (source_models_dir / "forecast_model.joblib").read_bytes()
            )
            (models_dir / "forecast_model_config.json").write_text(
                (source_models_dir / "forecast_model_config.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            result = predict_forecast(
                {
                    "history_rps": [0, 0, 1, 1, 2, 2, 3, 2, 4, 3],
                    "features": {
                        "rolling_mean_5": 2.8,
                        "rolling_std_5": 0.8,
                        "hour_of_day": 10,
                        "day_of_week": 1,
                    },
                },
                models_dir,
            )

        self.assertEqual(result["model_version"], "guarded-forecast-v2")
        self.assertGreaterEqual(result["predicted_request_count"], 3)
        self.assertLessEqual(result["predicted_request_count"], 50)


@unittest.skipIf(TestClient is None or create_app is None, "fastapi is not installed")
class MlApiEndpointTests(unittest.TestCase):
    def test_healthz_and_prediction_endpoints(self) -> None:
        models_dir = make_workspace_dir("ml-api-models")
        self.addCleanup(shutil.rmtree, models_dir, ignore_errors=True)
        client = TestClient(create_app(Settings(models_dir=models_dir)))
        health = client.get("/healthz")
        bot_response = client.post(
            "/predict/bot",
            json={
                "feature_version": "v2",
                "window_start": "2026-03-24T10:00:00Z",
                "window_end": "2026-03-24T10:01:00Z",
                "entity": {
                    "ip": "1.2.3.4",
                    "session_id": "sess-bot-1",
                    "user_agent": "Googlebot/2.1",
                },
                "features": {
                    "number_of_requests": 42,
                    "total_duration_s": 58,
                    "average_time_ms": 120,
                    "repeated_requests": 0.83,
                    "http_response_2xx": 0.76,
                    "http_response_3xx": 0.02,
                    "http_response_4xx": 0.18,
                    "http_response_5xx": 0.04,
                    "get_method": 0.91,
                    "post_method": 0.07,
                    "head_method": 0.01,
                    "other_method": 0.01,
                    "night": 0,
                    "max_barrage": 12,
                },
            },
        )
        forecast_response = client.post(
            "/predict/forecast",
            json={
                "feature_version": "v2",
                "bucket_end": "2026-03-24T10:01:00Z",
                "predicted_bucket_end": "2026-03-24T10:02:00Z",
                "target": {"scope": "system", "endpoint": ""},
                "history_rps": [10, 12, 14, 16, 20],
                "features": {
                    "rolling_mean_5": 14.4,
                    "rolling_std_5": 3.4,
                    "hour_of_day": 10,
                    "day_of_week": 1,
                },
            },
        )
        anomaly_response = client.post(
            "/predict/anomaly",
            json={
                "feature_version": "v2",
                "window_start": "2026-03-24T10:00:00Z",
                "window_end": "2026-03-24T10:01:00Z",
                "entity": {"endpoint": "/api/v1/orders"},
                "features": {
                    "request_count": 30,
                    "avg_latency_ms": 480,
                    "p95_latency_ms": 1900,
                    "p99_latency_ms": 3200,
                    "status_5xx_ratio": 0.12,
                    "baseline_avg_latency_ms": 150,
                    "baseline_5xx_ratio": 0.01,
                },
            },
        )

        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["mode"], "mock")
        self.assertEqual(bot_response.status_code, 200)
        self.assertEqual(forecast_response.status_code, 200)
        self.assertEqual(anomaly_response.status_code, 200)
        self.assertIn("bot_score", bot_response.json())
        self.assertIn("predicted_request_count", forecast_response.json())
        self.assertIn("anomaly_score", anomaly_response.json())

    def test_healthz_reports_model_mode_when_artifacts_exist(self) -> None:
        source_models_dir = ROOT / "ml-api" / "models"
        if not (source_models_dir / "bot_model.joblib").exists():
            self.skipTest("bot model artifact is not available")

        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = Path(temp_dir)
            (models_dir / "bot_model.joblib").write_bytes(
                (source_models_dir / "bot_model.joblib").read_bytes()
            )
            (models_dir / "model_config.json").write_text(
                (source_models_dir / "model_config.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            client = TestClient(create_app(Settings(models_dir=models_dir)))
            health = client.get("/healthz")
            body = health.json()

        self.assertEqual(health.status_code, 200)
        self.assertEqual(body["mode"], "model")
        self.assertIn("bot", body["tasks"])


if __name__ == "__main__":
    unittest.main()
