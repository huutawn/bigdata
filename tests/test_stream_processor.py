from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from urllib import error


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_TMP = ROOT / ".local-dev" / "tmp"
sys.path.insert(0, str(ROOT / "stream-processor" / "src"))

from stream_processor.main import (  # noqa: E402
    RuntimeState,
    StreamSettings,
    build_bot_feature_windows_python,
    build_load_forecast_rows,
    normalize_raw_log,
    process_once,
    update_runtime_state,
    build_forecast_requests,
)


def make_workspace_dir(prefix: str) -> Path:
    WORKSPACE_TMP.mkdir(parents=True, exist_ok=True)
    path = WORKSPACE_TMP / f"{prefix}-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


class StreamProcessorTests(unittest.TestCase):
    def test_stream_settings_default_to_python_windows(self) -> None:
        self.assertFalse(StreamSettings().use_spark_windows)

    def test_build_bot_feature_windows_aggregates_behavior_features(self) -> None:
        settings = StreamSettings(use_spark_windows=False)
        raw_logs = [
            normalize_raw_log(
                {
                    "schema_version": "v2",
                    "timestamp": "2026-03-24T10:00:00Z",
                    "request_id": "req-1",
                    "session_id": "sess-bot-1",
                    "ip": "1.2.3.4",
                    "user_agent": "Googlebot/2.1",
                    "method": "GET",
                    "endpoint": "/api/v1/products",
                    "route_template": "/api/v1/products",
                    "status": 200,
                    "latency_ms": 80,
                }
            ),
            normalize_raw_log(
                {
                    "schema_version": "v2",
                    "timestamp": "2026-03-24T10:00:05Z",
                    "request_id": "req-2",
                    "session_id": "sess-bot-1",
                    "ip": "1.2.3.4",
                    "user_agent": "Googlebot/2.1",
                    "method": "GET",
                    "endpoint": "/api/v1/products",
                    "route_template": "/api/v1/products",
                    "status": 404,
                    "latency_ms": 95,
                }
            ),
            normalize_raw_log(
                {
                    "schema_version": "v2",
                    "timestamp": "2026-03-24T10:00:08Z",
                    "request_id": "req-3",
                    "session_id": "sess-bot-1",
                    "ip": "1.2.3.4",
                    "user_agent": "Googlebot/2.1",
                    "method": "HEAD",
                    "endpoint": "/api/v1/products",
                    "route_template": "/api/v1/products",
                    "status": 200,
                    "latency_ms": 70,
                }
            ),
        ]

        payloads = build_bot_feature_windows_python(raw_logs, settings)

        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0]["features"]["number_of_requests"], 3)
        self.assertEqual(payloads[0]["features"]["repeated_requests"], 1.0)
        self.assertGreater(payloads[0]["features"]["http_response_4xx"], 0)
        self.assertGreaterEqual(payloads[0]["features"]["max_barrage"], 1)

    def test_build_forecast_requests_keeps_recent_history(self) -> None:
        settings = StreamSettings(use_spark_windows=False, forecast_history_size=4)
        state = RuntimeState()
        raw_logs = [
            normalize_raw_log(
                {
                    "schema_version": "v2",
                    "timestamp": "2026-03-24T10:00:00Z",
                    "request_id": "req-1",
                    "session_id": "sess-user-1",
                    "ip": "192.168.1.10",
                    "user_agent": "Mozilla/5.0",
                    "method": "GET",
                    "endpoint": "/api/v1/login",
                    "route_template": "/api/v1/login",
                    "status": 200,
                    "latency_ms": 120,
                }
            )
        ]

        update_runtime_state(state, raw_logs, settings)
        payloads = build_forecast_requests(state, raw_logs, settings)
        system_payload = next(payload for payload in payloads if payload["target"]["scope"] == "system")

        self.assertEqual(len(system_payload["history_rps"]), 4)
        self.assertEqual(system_payload["history_rps"][-1], 1)
        self.assertEqual(system_payload["bucket_end"], "2026-03-24T10:00:00Z")
        self.assertEqual(system_payload["predicted_bucket_end"], "2026-03-24T10:01:00Z")

        rows = build_load_forecast_rows(
            payloads,
            {
                ("system", ""): {
                    "predicted_request_count": 3,
                    "model_version": "mock-forecast-v2",
                },
                ("endpoint", "/api/v1/login"): {
                    "predicted_request_count": 2,
                    "model_version": "mock-forecast-v2",
                },
            },
        )
        system_row = next(row for row in rows if row["scope"] == "system")
        self.assertEqual(system_row["bucket_end"], "2026-03-24 10:00:00")
        self.assertEqual(system_row["predicted_bucket_end"], "2026-03-24 10:01:00")

    def test_process_once_falls_back_to_sample_and_file(self) -> None:
        temp_path = make_workspace_dir("stream-processor")
        self.addCleanup(shutil.rmtree, temp_path, ignore_errors=True)
        sample_path = temp_path / "raw-logs.sample.jsonl"
        fallback_path = temp_path / "processed_rows.mock.jsonl"
        sample_path.write_text(
            '{"schema_version":"v2","timestamp":"2026-03-24T10:00:00Z","request_id":"req-000001","session_id":"sess-bot-001","ip":"1.2.3.4","user_agent":"Googlebot/2.1","method":"GET","endpoint":"/api/v1/products","route_template":"/api/v1/products","status":404,"latency_ms":95}\n',
            encoding="utf-8",
        )

        settings = StreamSettings(
            batch_size=1,
            raw_log_sample_path=sample_path,
            fallback_output_path=fallback_path,
            use_spark_windows=False,
        )

        async def fake_fetch(_settings: StreamSettings):
            return []

        with patch("stream_processor.main.fetch_nats_batch", side_effect=fake_fetch), patch(
            "stream_processor.main.write_all_tables",
            side_effect=error.URLError("clickhouse unavailable"),
        ), patch("stream_processor.main.ml_api_ready", return_value=False):
            status = process_once(settings, RuntimeState())

        self.assertEqual(status["source"], "sample")
        self.assertEqual(status["sink"], "file")
        saved_rows = [json.loads(line) for line in fallback_path.read_text(encoding="utf-8").splitlines()]
        self.assertTrue(any(item["table"] == settings.processed_logs_table for item in saved_rows))
        processed_row = next(item["row"] for item in saved_rows if item["table"] == settings.processed_logs_table)
        self.assertIn("predicted_load", processed_row)
        self.assertEqual(processed_row["is_bot"], 1)

    def test_process_once_uses_ml_api_when_available_with_python_default(self) -> None:
        temp_path = make_workspace_dir("stream-processor")
        self.addCleanup(shutil.rmtree, temp_path, ignore_errors=True)
        sample_path = temp_path / "raw-logs.sample.jsonl"
        fallback_path = temp_path / "processed_rows.mock.jsonl"
        sample_path.write_text(
            "\n".join(
                [
                    '{"schema_version":"v2","timestamp":"2026-03-24T10:00:00Z","request_id":"req-000001","session_id":"sess-bot-001","ip":"1.2.3.4","user_agent":"Googlebot/2.1","method":"GET","endpoint":"/api/v1/products","route_template":"/api/v1/products","status":404,"latency_ms":95}',
                    '{"schema_version":"v2","timestamp":"2026-03-24T10:00:05Z","request_id":"req-000002","session_id":"sess-bot-001","ip":"1.2.3.4","user_agent":"Googlebot/2.1","method":"HEAD","endpoint":"/api/v1/products","route_template":"/api/v1/products","status":200,"latency_ms":80}',
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        settings = StreamSettings(
            batch_size=2,
            raw_log_sample_path=sample_path,
            fallback_output_path=fallback_path,
        )

        async def fake_fetch(_settings: StreamSettings):
            return []

        def fake_request_json(
            method: str,
            url: str,
            payload: dict[str, object] | None = None,
            timeout: int = 2,
        ) -> dict[str, object]:
            self.assertEqual(method, "POST")
            self.assertIsNotNone(payload)
            if url.endswith("/predict/bot"):
                return {"is_bot": True, "bot_score": 0.97, "model_version": "api-bot-v2"}
            if url.endswith("/predict/forecast"):
                target = payload["target"]
                if target["scope"] == "endpoint":
                    return {
                        "predicted_request_count": 31,
                        "model_version": "api-forecast-v2",
                    }
                return {"predicted_request_count": 74, "model_version": "api-forecast-v2"}
            if url.endswith("/predict/anomaly"):
                return {
                    "is_anomaly": True,
                    "anomaly_score": 0.81,
                    "model_version": "api-anomaly-v2",
                }
            self.fail(f"Unexpected URL: {url}")

        with patch("stream_processor.main.fetch_nats_batch", side_effect=fake_fetch), patch(
            "stream_processor.main.write_all_tables",
            side_effect=error.URLError("clickhouse unavailable"),
        ), patch("stream_processor.main.ml_api_ready", return_value=True), patch(
            "stream_processor.main.request_json",
            side_effect=fake_request_json,
        ):
            status = process_once(settings, RuntimeState())

        self.assertEqual(status["source"], "sample")
        self.assertEqual(status["sink"], "file")
        self.assertFalse(settings.use_spark_windows)
        saved_rows = [json.loads(line) for line in fallback_path.read_text(encoding="utf-8").splitlines()]
        bot_row = next(item["row"] for item in saved_rows if item["table"] == settings.bot_feature_table)
        forecast_rows = [
            item["row"] for item in saved_rows if item["table"] == settings.load_forecast_table
        ]
        processed_row = next(item["row"] for item in saved_rows if item["table"] == settings.processed_logs_table)
        anomaly_row = next(item["row"] for item in saved_rows if item["table"] == settings.anomaly_alert_table)

        self.assertEqual(bot_row["model_version"], "api-bot-v2")
        self.assertTrue(all(row["model_version"] == "api-forecast-v2" for row in forecast_rows))
        self.assertEqual(processed_row["predicted_load"], 31)
        self.assertEqual(anomaly_row["model_version"], "api-anomaly-v2")


if __name__ == "__main__":
    unittest.main()
