from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib import error


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "stream-processor" / "src"))

from stream_processor.main import StreamSettings, enrich_logs, process_once  # noqa: E402


class StreamProcessorTests(unittest.TestCase):
    def test_enrich_logs_uses_local_mock_when_ml_api_unavailable(self) -> None:
        raw_logs = [
            {
                "timestamp": "2026-03-24T10:00:00Z",
                "ip": "1.2.3.4",
                "endpoint": "/api/v1/products",
                "status": 200,
                "request_time_ms": 50,
                "user_agent": "Googlebot/2.1",
            }
        ]

        with patch("stream_processor.main.ml_api_ready", return_value=False):
            rows = enrich_logs(raw_logs, "http://127.0.0.1:1", 1)

        self.assertEqual(rows[0]["is_bot"], 1)
        self.assertEqual(rows[0]["predicted_load"], 21)
        self.assertEqual(rows[0]["is_anomaly"], 0)

    def test_process_once_falls_back_to_sample_and_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sample_path = temp_path / "raw-logs.sample.jsonl"
            fallback_path = temp_path / "processed_logs.mock.jsonl"
            sample_path.write_text(
                '{"timestamp":"2026-03-24T10:00:00Z","ip":"192.168.1.10","endpoint":"/api/v1/login","status":200,"request_time_ms":120,"user_agent":"Mozilla/5.0"}\n',
                encoding="utf-8",
            )

            settings = StreamSettings(
                batch_size=1,
                raw_log_sample_path=sample_path,
                fallback_output_path=fallback_path,
            )

            async def fake_fetch(_settings: StreamSettings):
                return []

            with patch("stream_processor.main.fetch_nats_batch", side_effect=fake_fetch), patch(
                "stream_processor.main.write_to_clickhouse",
                side_effect=error.URLError("clickhouse unavailable"),
            ), patch(
                "stream_processor.main.build_micro_batch",
                side_effect=lambda rows: rows,
            ), patch("stream_processor.main.ml_api_ready", return_value=False):
                status = process_once(settings)

            self.assertEqual(status["source"], "sample")
            self.assertEqual(status["sink"], "file")
            saved_rows = [json.loads(line) for line in fallback_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(saved_rows), 1)
            self.assertEqual(saved_rows[0]["predicted_load"], 21)


if __name__ == "__main__":
    unittest.main()
