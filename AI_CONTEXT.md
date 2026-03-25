# AIOps Big Data Pipeline: Master Project Context

> Dành cho AI và thành viên nhóm. Đây là tài liệu quy định cấu trúc, kỹ thuật và quy trình làm việc.  
> Mọi thay đổi liên quan đến schema phải được Tech Lead thông qua.

## 1. Tổng quan và mục tiêu dự án

Hệ thống phân tích log thời gian thực từ API Gateway để phục vụ 3 nhiệm vụ AIOps:

- **Bot Detection**: Nhận diện IP là bot hay người dùng thật.
- **Load Forecasting**: Dự báo lưu lượng (`requests/s`) trong tương lai.
- **Performance Anomaly**: Phát hiện API bị chậm bất thường (`latency` cao).

### Nguyên tắc làm việc

**Interface First**: thiết kế giao diện trước, code logic sau. Không ai đợi ai.

## 2. Cấu trúc thư mục chuẩn (Zero-Conflict)

Mỗi thành viên chỉ làm việc trong thư mục của mình. Mọi kết nối giữa các phần được thực hiện qua Network/API.

```text
/aiops-bigdata-root
|-- /infra                # Tech Lead: Docker Compose (NATS, ClickHouse, Grafana)
|-- /generator            # Người 2: Python script sinh log (Producer)
|-- /stream-processor     # Người 3: Spark Streaming (Consumer & Transformer)
|-- /ml-api               # Người 4: FastAPI (Model Serving)
|-- /analytics            # Người 5: SQL Setup & Grafana Dashboard
|-- CONTRACTS.md          # Hợp đồng Schema (Single Source of Truth)
`-- README.md             # Hướng dẫn chạy nhanh
```

## 3. Hợp đồng interface và mock data

Đây là **Single Source of Truth** cho toàn bộ hệ thống.

### A. Dữ liệu thô

- **NATS Topic**: `logs.raw`
- **Bên gửi**: Người 2
- **Bên nhận**: Người 3

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

### B. AI Inference API

- **Framework**: FastAPI
- **Endpoint**: `POST /analyze`
- **Bên gọi**: Người 3
- **Bên cung cấp**: Người 4

**Request**

```json
{
  "ip": "string",
  "latency_ms": 123,
  "current_rps": 100
}
```

**Mock response** (Tech Lead setup sẵn)

```json
{
  "is_bot": false,
  "predicted_load": 120,
  "is_anomaly": false
}
```

### C. Analytical Storage

- **Hệ quản trị**: ClickHouse
- **Table**: `processed_logs`
- **Bên ghi**: Người 3
- **Bên truy vấn**: Người 5

```sql
CREATE TABLE processed_logs (
    timestamp DateTime,
    ip String,
    endpoint String,
    latency_ms Int32,
    is_bot UInt8,         -- 0: Human, 1: Bot
    predicted_load Int32, -- Requests/s dự báo
    is_anomaly UInt8      -- 0: Bình thường, 1: Bất thường
) ENGINE = MergeTree()
ORDER BY timestamp;
```

## 4. Nhiệm vụ chi tiết của Tech Lead

Tech Lead phải hoàn thành phần "khung xương" sau đây trong 2 giờ đầu tiên.

### 4.1. Thiết lập hạ tầng (Docker)

- Cung cấp file `docker-compose.yml` chạy `NATS`, `ClickHouse` và `Grafana`.
- Giới hạn RAM cho từng container để tránh làm treo máy server.

### 4.2. Thiết lập FastAPI skeleton (ML Interface)

- Viết file `ml-api/main.py` bọc trong Docker.
- Đây là bước quan trọng để Người 3 có thể gọi API ngay cả khi Người 4 chưa hoàn thiện model AI.
- Mock logic có thể:
  - trả kết quả ngẫu nhiên, hoặc
  - dùng luật đơn giản, ví dụ IP `1.1.1.1` luôn là bot.

### 4.3. Thiết lập GitHub workflow

- Khởi tạo repository và thêm 4 thành viên.
- Tạo 4 nhánh:
  - `feat/generator`
  - `feat/stream`
  - `feat/ml`
  - `feat/analytics`
- Thiết lập CI/CD bằng GitHub Actions để tự động deploy lên Docker khi Tech Lead merge vào `main`.

## 5. Workflow phối hợp bất đồng bộ

### Vai trò và điểm bắt đầu

| Vai trò | Điểm bắt đầu dựa trên mock/interface |
| --- | --- |
| Người 2 (Generator) | Dựa vào schema ở mục 3A để viết Python script đẩy dữ liệu vào NATS. |
| Người 3 (Stream) | Dùng Spark đọc NATS, gọi API `http://ml-api:8000/analyze` và ghi vào ClickHouse. |
| Người 4 (ML) | Làm việc trên Colab/Jupyter. Khi xong chỉ cần đưa model vào `ml-api` và cập nhật hàm xử lý. |
| Người 5 (Analytics) | Dùng dữ liệu mẫu để vẽ dashboard trên Grafana, không cần chờ luồng dữ liệu thật. |

### Mock data cho từng task

#### Cho Người 3 (Spark) và Người 5 (Grafana)

Tech Lead cung cấp script SQL mẫu để test dashboard và luồng xử lý:

```sql
-- Dữ liệu giả lập 3 kịch bản: bình thường, bot và API chậm
INSERT INTO processed_logs VALUES
(now(), '192.168.1.1', '/api/v1/login', 120, 0, 100, 0),
(now(), '1.2.3.4', '/api/v1/products', 50, 1, 100, 0),    -- BOT
(now(), '192.168.1.5', '/api/v1/cart', 4500, 0, 100, 1); -- ANOMALY
```

#### Cho Người 4 (ML)

- Dataset mẫu để train do Tech Lead gửi.
- Có thể dùng **Kaggle: Web Log Dataset** hoặc tự tạo file CSV dựa trên schema mục 3A.

## 6. Quy tắc merge và deploy

Quy trình chuẩn:

`Code xong -> Push lên nhánh feature -> Tạo Pull Request -> Tech Lead review -> Merge vào main -> Hệ thống tự cập nhật trên server`

### Checklist review của Tech Lead

- Code có đúng schema không?
- Có chạy Docker local được không?
- Có làm vỡ interface với thành viên khác không?

