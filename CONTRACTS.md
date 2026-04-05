# Hợp đồng dữ liệu (Contracts)

`CONTRACTS.md` là nguồn sự thật duy nhất (single source of truth) cho các giao diện trong toàn bộ kho lưu trữ.
Hợp đồng v2 này chuyển dự án từ việc giả lập suy luận theo từng sự kiện sang kỹ thuật đặc trưng dựa trên cửa sổ (window-based feature engineering) và các dự đoán ML cụ thể theo nhiệm vụ.

## Tóm tắt kiến trúc

Đường ống (pipeline) là:

`raw logs -> feature windows -> ML predictions -> ClickHouse -> Grafana`
(log thô -> cửa sổ đặc trưng -> dự đoán ML -> ClickHouse -> Grafana)

Ba nhiệm vụ ML được tách biệt:

1. Phát hiện Bot dựa trên IP hoặc các cửa sổ hành vi phiên.
2. Dự báo tải dựa trên các nhóm lịch sử lưu lượng.
3. Phát hiện bất thường về độ trễ và lỗi trên các cửa sổ endpoint.

Luồng dữ liệu: `generator -> Kafka -> stream-processor (Spark) -> ml-api -> ClickHouse -> Grafana`

## 1. Hợp đồng Log thô (Raw Log Contract)

- Chủ đề (Subject): `logs.raw`
- Nhà sản xuất (Producer): `generator`
- Người tiêu dùng (Consumer): `stream-processor`
- Sơ đồ (Schema): `contracts/raw-log.schema.json`
- Ví dụ:
  - `contracts/examples/raw-log.sample.json`
  - `contracts/examples/raw-logs.sample.jsonl`

### Gói dữ liệu (Payload)

```json
{
  "schema_version": "v2",
  "timestamp": "2026-03-24T10:00:00Z",
  "request_id": "req-000001",
  "session_id": "sess-001",
  "ip": "1.2.3.4",
  "user_agent": "Mozilla/5.0",
  "method": "GET",
  "endpoint": "/api/v1/products",
  "route_template": "/api/v1/products",
  "status": 200,
  "latency_ms": 150
}
```

## 2. Hợp đồng phát hiện Bot (Bot Detection Contract)

- Nhà cung cấp (Provider): `ml-api`
- Người gọi (Caller): `stream-processor`
- Endpoint: `POST /predict/bot`
- Sơ đồ (Schemas):
  - `contracts/bot-request.schema.json`
  - `contracts/bot-response.schema.json`

### Yêu cầu (Request)

```json
{
  "feature_version": "v2",
  "window_start": "2026-03-24T10:00:00Z",
  "window_end": "2026-03-24T10:01:00Z",
  "entity": {
    "ip": "1.2.3.4",
    "session_id": "sess-001",
    "user_agent": "Mozilla/5.0"
  },
  "features": {
    "number_of_requests": 42,
    "total_duration_s": 58,
    "average_time_ms": 120,
    "repeated_requests": 0.83,
    "http_response_2xx": 0.76,
    "http_response_3xx": 0.02,
    "http_response_4xx": 0.18,
    "http_response_5xx": 0.04,
    "get_method": 0.91,
    "post_method": 0.07,
    "head_method": 0.01,
    "other_method": 0.01,
    "night": 0,
    "max_barrage": 12
  }
}
```

### Phản hồi (Response)

```json
{
  "is_bot": true,
  "bot_score": 0.91,
  "model_version": "mock-bot-v2"
}
```

## 3. Hợp đồng dự báo tải (Load Forecast Contract)

- Nhà cung cấp (Provider): `ml-api`
- Người gọi (Caller): `stream-processor`
- Endpoint: `POST /predict/forecast`
- Sơ đồ (Schemas):
  - `contracts/forecast-request.schema.json`
  - `contracts/forecast-response.schema.json`

### Yêu cầu (Request)

```json
{
  "feature_version": "v2",
  "bucket_end": "2026-03-24T10:01:00Z",
  "target": {
    "scope": "system",
    "endpoint": ""
  },
  "history_rps": [55, 58, 61, 64, 62, 70],
  "features": {
    "rolling_mean_5": 63.0,
    "rolling_std_5": 4.2,
    "hour_of_day": 10,
    "day_of_week": 1
  }
}
```

### Phản hồi (Response)

```json
{
  "predicted_request_count": 74,
  "model_version": "mock-forecast-v2"
}
```

## 4. Hợp đồng phát hiện bất thường (Anomaly Detection Contract)

- Nhà cung cấp (Provider): `ml-api`
- Người gọi (Caller): `stream-processor`
- Endpoint: `POST /predict/anomaly`
- Sơ đồ (Schemas):
  - `contracts/anomaly-request.schema.json`
  - `contracts/anomaly-response.schema.json`

### Yêu cầu (Request)

```json
{
  "feature_version": "v2",
  "window_start": "2026-03-24T10:00:00Z",
  "window_end": "2026-03-24T10:01:00Z",
  "entity": {
    "endpoint": "/api/v1/orders"
  },
  "features": {
    "request_count": 120,
    "avg_latency_ms": 420,
    "p95_latency_ms": 1800,
    "p99_latency_ms": 3200,
    "status_5xx_ratio": 0.12,
    "baseline_avg_latency_ms": 180,
    "baseline_5xx_ratio": 0.01
  }
}
```

### Phản hồi (Response)

```json
{
  "is_anomaly": true,
  "anomaly_score": 0.87,
  "model_version": "mock-anomaly-v2"
}
```

## 5. Hợp đồng Log đã xử lý (Processed Log Contract)

- Lưu trữ (Storage): ClickHouse
- Bảng (Table): `processed_logs`
- Người viết (Writer): `stream-processor`
- Người đọc (Reader): `analytics`
- Sơ đồ (Schema): `contracts/processed-log.schema.json`

### Gói dữ liệu (Payload)

```json
{
  "schema_version": "v2",
  "timestamp": "2026-03-24T10:00:00Z",
  "request_id": "req-000001",
  "session_id": "sess-001",
  "ip": "1.2.3.4",
  "user_agent": "Mozilla/5.0",
  "method": "GET",
  "endpoint": "/api/v1/products",
  "route_template": "/api/v1/products",
  "status": 200,
  "latency_ms": 150,
  "bot_score": 0.91,
  "is_bot": 1,
  "predicted_load": 74,
  "anomaly_score": 0.04,
  "is_anomaly": 0
}
```

## 6. Quy tắc giả lập tất định (Deterministic Mock Rules)

Logic giả lập phải khớp giữa `ml-api` và dự phòng luồng cục bộ (local stream fallback):

- Điểm số Bot (Bot score) tăng khi có bùng nổ yêu cầu (request burst), lặp lại các route, tỷ lệ lỗi 4xx hoặc 5xx cao, user agent đáng ngờ và IP nằm trong danh sách bot đã biết.
- Dự báo (Forecast) sử dụng lịch sử lưu lượng truy cập gần đây cộng với xu hướng ngắn hạn.
- Điểm số bất thường (Anomaly score) tăng khi độ trễ bị lạm phát (latency inflation), các đỉnh p95 hoặc p99 vọt lên và tỷ lệ 5xx cao so với đường cơ sở (baseline) gần đây.

## 7. Quy tắc về cửa sổ (Windowing Rules)

- Cửa sổ phát hiện Bot:
  - Khóa (Key): `ip + session_id + user_agent`
  - Độ dài cửa sổ: 60 giây
  - Trượt (Slide): 10 giây
- Cửa sổ phát hiện bất thường:
  - Khóa (Key): `endpoint`
  - Độ dài cửa sổ: 60 giây
  - Trượt (Slide): 10 giây
  - Xem lại đường cơ sở (Baseline lookback): 5 phút
- Nhóm dự báo (Forecasting buckets):
  - Khóa (Key): `system` và `endpoint`
  - Độ dài nhóm: 60 giây
  - Độ dài lịch sử: 10 nhóm

## 8. Quy tắc dự phòng (Fallback Rules)

- `generator`: thất bại nhanh (fail fast) nếu NATS không khả dụng.
- `stream-processor`:
  - Nếu NATS không trả về dữ liệu, hãy tải `raw-logs.sample.jsonl`.
  - Nếu `ml-api` không hoạt động tốt, hãy sử dụng các hàm dự đoán tất định cục bộ.
  - Nếu việc ghi vào ClickHouse thất bại, hãy kết xuất (dump) tất cả các hàng của bảng vào tệp dự phòng.
- `analytics`:
  - Luôn sử dụng `CREATE TABLE IF NOT EXISTS`.
  - Nạp dữ liệu mồi (Seed) cho tất cả các bảng phân tích nếu `processed_logs` trống.

