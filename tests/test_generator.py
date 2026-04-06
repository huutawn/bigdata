from __future__ import annotations

import random
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator" / "src"))

from generator.main import GeneratorSettings, _resolve_batch_size, build_log  # noqa: E402
from generator.replay_access_logs import (  # noqa: E402
    Sessionizer,
    infer_latency_ms,
    parse_access_log_line,
)


class GeneratorTests(unittest.TestCase):
    def test_build_log_is_deterministic_for_same_index_and_seed(self) -> None:
        base_time = datetime(2026, 3, 24, 10, 0, 0, tzinfo=timezone.utc)
        first = build_log(1, random.Random(7), base_time)
        second = build_log(1, random.Random(7), base_time)

        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], "v2")
        self.assertEqual(first["request_id"], "req-000001")
        self.assertIn(first["method"], {"GET", "POST", "HEAD", "PUT", "DELETE", "PATCH"})
        self.assertIn("session_id", first)
        self.assertIn("route_template", first)
        self.assertIn("latency_ms", first)

    def test_batch_size_profile_has_repeatable_trend(self) -> None:
        settings = GeneratorSettings(batch_size=50)
        series = [_resolve_batch_size(settings, index) for index in range(16)]

        self.assertEqual(series[0], _resolve_batch_size(settings, 0))
        self.assertGreater(max(series), min(series))
        self.assertGreater(series[10], series[0])
        self.assertLess(series[-1], series[10])

    def test_parse_access_log_line_normalizes_combined_log(self) -> None:
        line = (
            '31.56.96.51 - - [22/Jan/2019:03:56:16 +0330] '
            '"GET /image/60844/productModel/200x200 HTTP/1.1" 200 5667 '
            '"https://www.zanbil.ir/m/filter/b113" '
            '"Mozilla/5.0 (Linux; Android 6.0; ALE-L21 Build/HuaweiALE-L21)" "-"'
        )

        parsed = parse_access_log_line(line, Sessionizer())

        self.assertIsNotNone(parsed)
        original_timestamp, record = parsed
        self.assertEqual(original_timestamp.tzinfo, timezone.utc)
        self.assertEqual(record["method"], "GET")
        self.assertEqual(record["endpoint"], "/image/60844/productModel/200x200")
        self.assertEqual(record["route_template"], "/image/{id}/productModel/{size}")
        self.assertEqual(record["original_timestamp"], "2019-01-22T00:26:16Z")
        self.assertEqual(record["status"], 200)
        self.assertTrue(str(record["session_id"]).startswith("sess-"))
        self.assertGreaterEqual(int(record["latency_ms"]), 35)

    def test_sessionizer_rotates_after_idle_gap(self) -> None:
        sessionizer = Sessionizer(gap=timedelta(minutes=15))
        first = sessionizer.assign(
            "1.2.3.4",
            "Googlebot/2.1",
            datetime(2026, 3, 24, 10, 0, 0, tzinfo=timezone.utc),
        )
        second = sessionizer.assign(
            "1.2.3.4",
            "Googlebot/2.1",
            datetime(2026, 3, 24, 10, 10, 0, tzinfo=timezone.utc),
        )
        third = sessionizer.assign(
            "1.2.3.4",
            "Googlebot/2.1",
            datetime(2026, 3, 24, 10, 31, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(first, second)
        self.assertNotEqual(second, third)

    def test_latency_heuristic_penalizes_slow_error_paths(self) -> None:
        image_latency = infer_latency_ms(
            "/image/60844/productModel/200x200",
            200,
            "Mozilla/5.0",
        )
        checkout_latency = infer_latency_ms(
            "/api/v1/checkout",
            503,
            "Mozilla/5.0",
        )

        self.assertGreater(checkout_latency, image_latency)


if __name__ == "__main__":
    unittest.main()
