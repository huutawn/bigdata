# Team Workflow

## Ownership

- Tech Lead: `infra/`, `contracts/`, `.github/`, `docs/`, root docs.
- Member 1: `generator/`
- Member 2: `stream-processor/`
- Member 3: `ml-api/`
- Member 4: `analytics/`

## Branching

- `main`: only Tech Lead merge.
- `feat/generator`: generator owner.
- `feat/stream`: stream owner.
- `feat/ml`: ml owner.
- `feat/analytics`: analytics owner.

## Change Boundaries

- Khong sua module cua nguoi khac neu khong can thiet.
- Schema change phai sua dong thoi `CONTRACTS.md`, schema JSON va examples.
- Infrastructure change phai duoc test lai bang `docker compose -f infra/docker-compose.yml config`.

## Dependency Matrix

| Team | Input dependency | Cach mo khoa khi dependency chua san sang |
| --- | --- | --- |
| Generator | NATS | Fail som neu NATS down, khong block team khac |
| Stream | NATS raw logs | Doc `contracts/examples/raw-logs.sample.jsonl` |
| Stream | ML API | Dung local mock analyzer |
| Stream | ClickHouse | Dump sang `stream-processor/output/processed_logs.mock.jsonl` |
| Analytics | ClickHouse rows | `ensure_seed.py` tao bang va seed du lieu mau |
| ML | Model artifact | Chay mock mode cho toi khi co file trong `ml-api/models/` |

## PR Checklist

- Interface van dung voi contracts hien tai.
- Co fallback/mock neu code cua ban phu thuoc module khac.
- Co test cho logic moi hoac update bootstrap tests.
- Khong sua file ngoai ownership neu chang chang buoc.
