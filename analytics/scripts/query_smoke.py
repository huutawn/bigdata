from __future__ import annotations

import os
from urllib import request


CLICKHOUSE_URL = os.getenv("CLICKHOUSE_URL", "http://localhost:8123")
QUERIES = {
    "processed_logs": "SELECT count() FROM processed_logs",
    "bot_feature_windows": "SELECT count() FROM bot_feature_windows",
    "load_forecasts": "SELECT count() FROM load_forecasts",
    "anomaly_alerts": "SELECT count() FROM anomaly_alerts",
}


def execute(sql: str) -> str:
    response = request.urlopen(
        request.Request(CLICKHOUSE_URL, data=sql.encode("utf-8"), method="POST"),
        timeout=5,
    )
    with response:
        return response.read().decode("utf-8").strip()


def main() -> int:
    for name, sql in QUERIES.items():
        result = execute(sql)
        print(f"{name}={result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
