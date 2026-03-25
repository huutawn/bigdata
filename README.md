# AIOps Big Data Monorepo

Monorepo nay duoc bootstrap theo mo hinh `interface first` de 4 thanh vien co the lam song song ma khong chan nhau. Tech Lead quan ly `infra`, contracts, CI va review; moi thanh vien chi can tap trung vao module cua minh.

## Repo Layout

```text
.
|-- AI_CONTEXT.md
|-- CONTRACTS.md
|-- docs/
|-- infra/
|-- contracts/
|-- generator/
|-- stream-processor/
|-- ml-api/
|-- analytics/
|-- scripts/
`-- tests/
```

## Quick Start

1. Copy `.env.example` thanh `.env` va dieu chinh neu can.
2. Start ha tang:

   ```powershell
   docker compose -f infra/docker-compose.yml --env-file .env up -d clickhouse nats grafana
   ```

3. Start ML mock API:

   ```powershell
   docker compose -f infra/docker-compose.yml --env-file .env up -d ml-api
   ```

4. Seed ClickHouse neu bang rong:

   ```powershell
   python analytics/scripts/ensure_seed.py
   ```

5. Run bootstrap tests:

   ```powershell
   python scripts/validate_contracts.py
   python -m unittest discover -s tests -p "test_*.py" -v
   ```

## Zero-Conflict Rules

- `generator/`: chi push raw logs len NATS, khong dung den `stream-processor/`.
- `stream-processor/`: chi doc contracts, goi `ml-api`, ghi ClickHouse.
- `ml-api/`: cung cap HTTP interface on dinh, co mock fallback khi chua co model.
- `analytics/`: chi doc ClickHouse va dung seed SQL neu chua co du lieu that.
- `infra/`, `contracts/`, `.github/`, `docs/`: Tech Lead so huu.

## Fallback Strategy

- NATS khong co message trong cua so poll: `stream-processor` doc `contracts/examples/raw-logs.sample.jsonl`.
- `ml-api` chua co model hoac khong healthy: tra mock inference deterministic.
- ClickHouse bang rong: `analytics/scripts/ensure_seed.py` tu dong tao bang va seed du lieu mau.
- ClickHouse chua san sang khi stream ghi: luu batch vao `stream-processor/output/processed_logs.mock.jsonl`.

## Git Workflow

- Default branch: `main`
- Feature branches:
  - `feat/generator`
  - `feat/stream`
  - `feat/ml`
  - `feat/analytics`
- PR chi merge vao `main` sau khi pass contracts, tests, compose config va review Tech Lead.

## Notes

- `.github/CODEOWNERS` dang dung placeholder `@techlead-placeholder`; thay bang GitHub handle that truoc khi bat branch protection.
- `deploy.yml` da duoc scaffold o che do secret-gated. Deploy chi chay khi khai bao `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`.
