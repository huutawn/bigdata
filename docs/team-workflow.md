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

- Không sửa module của người khác nếu không cần thiết.
- Schema change phải sửa đồng thời `CONTRACTS.md`, schema JSON và examples.
- Infrastructure change phải được test lại bằng `docker compose -f infra/docker-compose.yml config`.

## Dependency Matrix

| Team | Input dependency | Cách mở khoá khi dependency chưa sẵn sàng |
| --- | --- | --- |
| Generator | NATS | Fail sớm nếu NATS down, không block team khác |
| Stream | NATS raw logs | Đọc `contracts/examples/raw-logs.sample.jsonl` |
| Stream | ML API | Dùng local mock analyzer |
| Stream | ClickHouse | Dump sang `stream-processor/output/processed_logs.mock.jsonl` |
| Analytics | ClickHouse rows | `ensure_seed.py` tạo bảng và seed dữ liệu mẫu |
| ML | Model artifact | Chạy mock mode cho tới khi có file trong `ml-api/models/` |

## PR Checklist

- Interface vẫn đúng với contracts hiện tại.
- Có fallback/mock nếu code của bạn phụ thuộc module khác.
- Có test cho logic mới hoặc update bootstrap tests.
- Không sửa file ngoài ownership nếu chẳng đặng đừng.
