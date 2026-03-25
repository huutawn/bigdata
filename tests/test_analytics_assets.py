from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AnalyticsAssetTests(unittest.TestCase):
    def test_create_table_sql_contains_expected_columns(self) -> None:
        ddl = (ROOT / "analytics" / "sql" / "create_processed_logs.sql").read_text(
            encoding="utf-8"
        )
        self.assertIn("timestamp DateTime", ddl)
        self.assertIn("predicted_load Int32", ddl)
        self.assertIn("is_anomaly UInt8", ddl)

    def test_seed_sql_contains_three_bootstrap_scenarios(self) -> None:
        seed = (ROOT / "analytics" / "sql" / "seed_processed_logs.sql").read_text(
            encoding="utf-8"
        )
        self.assertIn("/api/v1/login", seed)
        self.assertIn("/api/v1/products", seed)
        self.assertIn("/api/v1/cart", seed)

    def test_dashboard_starter_has_core_panels(self) -> None:
        dashboard = json.loads(
            (ROOT / "analytics" / "grafana" / "dashboards" / "aiops-overview.json").read_text(
                encoding="utf-8"
            )
        )
        titles = {panel["title"] for panel in dashboard["panels"]}
        self.assertEqual(
            titles,
            {
                "Requests per Minute",
                "Bot Ratio",
                "Avg Anomaly Latency",
                "Endpoint Breakdown",
            },
        )


if __name__ == "__main__":
    unittest.main()
