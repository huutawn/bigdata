from __future__ import annotations

import random
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator" / "src"))

from generator.main import build_log  # noqa: E402


class GeneratorTests(unittest.TestCase):
    def test_build_log_is_deterministic_for_same_index_and_seed(self) -> None:
        base_time = datetime(2026, 3, 24, 10, 0, 0, tzinfo=timezone.utc)
        first = build_log(1, random.Random(7), base_time)
        second = build_log(1, random.Random(7), base_time)

        self.assertEqual(first, second)
        self.assertEqual(first["endpoint"], "/api/v1/products")
        self.assertIn("timestamp", first)
        self.assertIn("request_time_ms", first)


if __name__ == "__main__":
    unittest.main()
