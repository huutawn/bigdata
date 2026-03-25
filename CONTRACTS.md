# Contracts

`CONTRACTS.md` là nguồn chân lý cho interface giữa 4 module. Mọi thay đổi schema phải được Tech Lead review.

## 1. Raw Log Contract

- Subject: `logs.raw`
- Producer: `generator`
- Consumer: `stream-processor`
- Schema file: `contracts/raw-log.schema.json`
- Examples:
  - `contracts/examples/raw-log.sample.json`
  - `contracts/examples/raw-logs.sample.jsonl`

### Payload

```json
{
  "timestamp": "2026-03-24T10:00:00Z",
  "ip": "1.2.3.4",
  "endpoint": "/api/v1/products",
  "status": 200,
  "request_time_ms": 150,
  "user_agent": "Mozilla/5.0..."
}
```

## 2. Analyze API Contract

- Provider: `ml-api`
- Caller: `stream-processor`
- Endpoint: `POST /analyze`
- Health: `GET /healthz`
- Schema files:
  - `contracts/analyze-request.schema.json`
  - `contracts/analyze-response.schema.json`

### Request

```json
{
  "ip": "string",
  "latency_ms": 123,
  "current_rps": 100
}
```

### Response

```json
{
  "is_bot": false,
  "predicted_load": 120,
  "is_anomaly": false
}
```

## 3. Processed Log Contract

- Storage: ClickHouse
- Table: `processed_logs`
- Writer: `stream-processor`
- Reader: `analytics`
- Schema file: `contracts/processed-log.schema.json`

### DDL

```sql
CREATE TABLE processed_logs (
    timestamp DateTime,
    ip String,
    endpoint String,
    latency_ms Int32,
    is_bot UInt8,
    predicted_load Int32,
    is_anomaly UInt8
) ENGINE = MergeTree()
ORDER BY timestamp;
```

## 4. Deterministic Mock Rules

Mock rule phải giống nhau giữa `ml-api` và local fallback của `stream-processor`.

- `is_bot = true` nếu `ip` nằm trong `{"1.1.1.1", "1.2.3.4"}`.
- `is_anomaly = true` nếu `latency_ms >= 3000`.
- `predicted_load = current_rps + 20`, cộng thêm `30` nếu `is_anomaly = true`.

## 5. Readiness and Fallback

- `generator`: startup fail sớm nếu không kết nối được NATS.
- `stream-processor`:
  - nếu NATS không trả message trong timeout, đọc sample JSONL.
  - nếu `ml-api` timeout hoặc `/healthz` không healthy, dùng local mock analyzer.
  - nếu ClickHouse ghi thất bại, dump batch vào file fallback.
- `analytics`:
  - luôn `CREATE TABLE IF NOT EXISTS`.
  - nếu `processed_logs` bảng rỗng, auto seed từ `analytics/sql/seed_processed_logs.sql`.
