from __future__ import annotations

import os
from pathlib import Path
from urllib import request


ROOT = Path(__file__).resolve().parents[2]
CREATE_SQL = (ROOT / "analytics" / "sql" / "create_processed_logs.sql").read_text(
    encoding="utf-8"
)
SEED_SQL = (ROOT / "analytics" / "sql" / "seed_processed_logs.sql").read_text(
    encoding="utf-8"
)
CLICKHOUSE_URL = os.getenv("CLICKHOUSE_URL", "http://localhost:8123")


def split_statements(sql: str) -> list[str]:
    return [statement.strip() for statement in sql.split(";") if statement.strip()]


def execute(sql: str) -> str:
    response = request.urlopen(
        request.Request(CLICKHOUSE_URL, data=sql.encode("utf-8"), method="POST"),
        timeout=5,
    )
    with response:
        return response.read().decode("utf-8").strip()


def main() -> int:
    for statement in split_statements(CREATE_SQL):
        execute(statement)
    count = int(execute("SELECT count() FROM processed_logs") or "0")
    if count == 0:
        for statement in split_statements(SEED_SQL):
            execute(statement)
        count = int(execute("SELECT count() FROM processed_logs") or "0")
        print(f"Seeded analytics tables. processed_logs={count}")
    else:
        print(f"processed_logs already has {count} rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
