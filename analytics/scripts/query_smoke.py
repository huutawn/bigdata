from __future__ import annotations

import os
from urllib import request


CLICKHOUSE_URL = os.getenv("CLICKHOUSE_URL", "http://localhost:8123")
QUERIES = {
    "request_count": "SELECT count() FROM processed_logs",
    "bot_ratio": "SELECT sum(is_bot) FROM processed_logs",
    "anomaly_ratio": "SELECT sum(is_anomaly) FROM processed_logs",
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
