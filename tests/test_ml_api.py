from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml-api" / "src"))

from ml_api.analyzer import analyze, runtime_mode  # noqa: E402

try:
    from fastapi.testclient import TestClient
    from ml_api.main import Settings, create_app
except ModuleNotFoundError:
    TestClient = None
    Settings = None
    create_app = None


class MlApiAnalyzerTests(unittest.TestCase):
    def test_mock_mode_analysis_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = Path(temp_dir)
            result = analyze("192.168.1.10", 123, 100, models_dir)
            self.assertEqual(result["is_bot"], False)
            self.assertEqual(result["predicted_load"], 120)
            self.assertEqual(result["is_anomaly"], False)

    def test_runtime_mode_switches_when_artifact_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = Path(temp_dir)
            self.assertEqual(runtime_mode(models_dir), "mock")
            (models_dir / "model_config.json").write_text("{}", encoding="utf-8")
            self.assertEqual(runtime_mode(models_dir), "model")


@unittest.skipIf(TestClient is None or create_app is None, "fastapi is not installed")
class MlApiEndpointTests(unittest.TestCase):
    def test_healthz_and_analyze_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            client = TestClient(create_app(Settings(models_dir=Path(temp_dir))))
            health = client.get("/healthz")
            analyze_response = client.post(
                "/analyze",
                json={"ip": "192.168.1.10", "latency_ms": 123, "current_rps": 100},
            )

        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["mode"], "mock")
        self.assertEqual(analyze_response.status_code, 200)
        self.assertEqual(analyze_response.json()["predicted_load"], 120)


if __name__ == "__main__":
    unittest.main()
