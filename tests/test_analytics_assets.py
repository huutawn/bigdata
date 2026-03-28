from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AnalyticsAssetTests(unittest.TestCase):
    def test_create_table_sql_contains_expected_tables(self) -> None:
        ddl = (ROOT / "analytics" / "sql" / "create_processed_logs.sql").read_text(
            encoding="utf-8"
        )
        self.assertIn("CREATE TABLE IF NOT EXISTS processed_logs", ddl)
        self.assertIn("CREATE TABLE IF NOT EXISTS bot_feature_windows", ddl)
        self.assertIn("CREATE TABLE IF NOT EXISTS load_forecasts", ddl)
        self.assertIn("CREATE TABLE IF NOT EXISTS anomaly_alerts", ddl)

    def test_seed_sql_contains_v2_tables(self) -> None:
        seed = (ROOT / "analytics" / "sql" / "seed_processed_logs.sql").read_text(
            encoding="utf-8"
        )
        self.assertIn("INSERT INTO processed_logs", seed)
        self.assertIn("INSERT INTO bot_feature_windows", seed)
        self.assertIn("INSERT INTO load_forecasts", seed)
        self.assertIn("INSERT INTO anomaly_alerts", seed)

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
                "Latest Forecasted Load",
                "Top Bot Entities",
                "Endpoint Anomaly Alerts",
            },
        )


if __name__ == "__main__":
    unittest.main()
