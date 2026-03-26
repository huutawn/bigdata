# AIOps Big Data Pipeline

Dự án này xây dựng một hệ thống phân tích log thời gian thực từ API Gateway nhằm phục vụ 3 nhiệm vụ AIOps chính:
1. **Bot Detection**: Nhận diện IP là bot hay người dùng thật.
2. **Load Forecasting**: Dự báo lưu lượng (requests/s) trong tương lai.
3. **Performance Anomaly**: Phát hiện API bị chậm bất thường (latency cao).

Monorepo này áp dụng triết lý **Interface First** và **Zero-Conflict**: Mỗi thành viên được giao một phần việc độc lập trong một thư mục riêng biệt. Chúng ta thống nhất giao tiếp qua các hợp đồng dữ liệu (Data Contracts - xem `CONTRACTS.md`) để có thể làm việc song song mà không ai phải chờ ai.

## Repo Layout và Phân công nhiệm vụ

Cấu trúc dự án được chia mảnh rõ ràng cho từng vai trò:

```text
.
|-- AI_CONTEXT.md         # Master Project Context (dành cho kiến trúc)
|-- CONTRACTS.md          # Hợp đồng Schema (Single Source of Truth)
|-- docs/
|-- infra/                # [Tech Lead] Docker Compose (NATS, ClickHouse, Grafana)
|-- contracts/            # [Tech Lead] Các schema JSON và dữ liệu mẫu
|-- generator/            # [Người 2] Python script sinh log (Producer đẩy lên NATS)
|-- stream-processor/     # [Người 3] Spark Streaming (Consumer, gọi API, ghi ClickHouse)
|-- ml-api/               # [Người 4/Tech Lead] FastAPI (Model Serving & Mock API)
|-- analytics/            # [Người 5] SQL Setup & Grafana Dashboard
|-- scripts/
`-- tests/
```

### Chi tiết nhiệm vụ từng thành viên:

#### 1. Tân (Tech Lead / DevOps)
- **Mục đích**: Xây dựng nền móng kiến trúc, hạ tầng và tiêu chuẩn để 4 người còn lại có thể code song song mà không phải chờ đợi nhau.
- **Công việc cụ thể cần làm**:
  - Tạo file `docker-compose.yml` phân bổ NATS, ClickHouse, Grafana trong thư mục `infra/`.
  - Định nghĩa các Schema JSON và cấu hình DDL mẫu trong `contracts/` và chốt file `CONTRACTS.md`.
  - Code bộ khung (skeleton) FastAPI trong `ml-api/` để luôn trả về mock data, giúp Lên không bị đứng chờ Luân.
  - Review và Merge code của mọi người từ các nhánh feature bằng CI/CD Github.

#### 2. Trâm (Data Generator / Producer)
- **Mục đích**: Chạy một bộ giả lập API Gateway thực thụ, liên tục tạo ra nguồn dữ liệu log (raw logs) để nhồi vào hệ thống.
- **Công việc cụ thể cần làm**:
  - Viết code Python (thư mục `generator/`) chạy vòng lặp để tạo JSON dựa theo hợp đồng `contracts/raw-log.schema.json`.
  - Kết nối và đẩy toàn bộ log JSON đó vào hệ thống thông điệp NATS (topic `logs.raw`).
  - Lập trình **giả lập các kịch bản thực tế**: 
    - *Bình thường*: Đều đặn 10-20 req/s, Status 200, Latency thấp.
    - *Spam (Bot)*: Một vài IP gửi cả trăm req/s, dồn dập vào 1-2 endpoint.
    - *Sự cố (Anomaly)*: Bỗng nhiên latency toàn hệ thống tăng lên 3-5s, xuất hiện nhiều lỗi 5xx.
    - *Biến động tải (Forecasting)*: Lưu lượng tăng giảm theo đồ thị để hệ thống AI dự báo.
  - Cài đặt cơ chế Fail-fast: Tự động tắt script ngay nếu không kết nối được NATS.

#### 3. Lên (Stream Processor / Data Engineer)
- **Mục đích**: Làm trạm luân chuyển dữ liệu trung tâm: Hứng log thô, lọc, gửi lên AI phân tích, nhận kết quả và lưu về kho.
- **Công việc cụ thể cần làm**:
  - Viết Spark Streaming (trong `stream-processor/`) kết nối vào NATS để hút dữ liệu log thô liên tục.
  - Với mỗi JSON log thô, gọi HTTP `POST http://ml-api:8000/analyze` sang API (của Tân/Luân) để xin AI nhận định rủi ro.
  - Trộn kết quả AI vào JSON gốc và Insert trực tiếp vào bảng `processed_logs` trên ClickHouse.
  - Xử lý các kịch bản Fallback (Phòng hờ lỗi): Đọc file mẫu nếu NATS sập, dùng hàm giả lập nội bộ nếu ML API bị sập, ghi tạm dữ liệu ra ổ cứng nếu ClickHouse chưa khởi động xong.

#### 4. Luân (AI/ML Engineer)
- **Mục đích**: Xây dựng "Bộ não" của hệ thống - làm mô hình Machine Learning để trả lời 3 câu hỏi AIOps dựa trên số liệu log.
- **Công việc cụ thể cần làm**:
  - Thu thập dữ liệu log mẫu từ Kaggle hoặc lấy log do Trâm sinh ra để huấn luyện mô hình (trên Python Notebook / Colab).
  - Khảo sát và train 3 model: Phân loại tính chất Bot, Dự báo Requests/s tương lai, và Phát hiện độ trễ bất thường.
  - Mang mô hình (`.pkl`, `.onnx`...) lắp vào thư mục mã nguồn `ml-api/`, viết đoạn code xử lý đè lên logic Fake do Tân tạo ra từ trước.

#### 5. Hòa (Data Analytics / BI)
- **Mục đích**: Trực quan hóa dữ liệu ở bước cuối cùng, giúp người dùng cuối nhìn thấy báo cáo trên đồ thị thời gian thực.
- **Công việc cụ thể cần làm**:
  - Không cần đợi ai cả, chạy file giả lập SQL (`ensure_seed.py`) tạo bảng trên ClickHouse và tự băm dữ liệu mẫu vào.
  - Đăng nhập vào giao diện Grafana (Tân đã dựng sẵn trên nền Docker).
  - Kết nối dữ liệu Grafana tới database ClickHouse.
  - Dựng các trang Dashboard báo cáo rõ ràng 3 bài toán: Đồ thị tải đang thay đổi thế nào? IP nào đang Spam (Bot)? Độ trễ chung có đang bất thường không?

## Quick Start (Dành cho chạy thử local)

1. Copy `.env.example` thành `.env` và điều chỉnh nếu cần.
2. Khởi động hạ tầng:

   ```powershell
   docker compose -f infra/docker-compose.yml --env-file .env up -d clickhouse nats grafana
   ```

3. Khởi động ML mock API:

   ```powershell
   docker compose -f infra/docker-compose.yml --env-file .env up -d ml-api
   ```

4. Seed dữ liệu mẫu vào ClickHouse (nếu bảng rỗng):

   ```powershell
   python analytics/scripts/ensure_seed.py
   ```

5. Chạy các bài test hệ thống (bootstrap tests):

   ```powershell
   python scripts/validate_contracts.py
   python -m unittest discover -s tests -p "test_*.py" -v
   ```

## The "Zero-Conflict" Workflow

Để dự án trôi chảy, vui lòng tuân thủ các nguyên tắc sau:
- **Tôn trọng ranh giới**: Chỉ sửa code trong thư mục được phân công. Nếu buộc phải sửa file đụng chạm tới team khác, hãy liên hệ Tech Lead.
- **Tuân thủ Hợp đồng**: Mọi thay đổi về cấu trúc dữ liệu gửi/nhận phải cập nhật đồng thời ở `CONTRACTS.md`, schema JSON và examples.
- **Fallbacks là bắt buộc**: Khi module của thành viên khác chưa xong hoặc bị lỗi, code của bạn phải tự động chuyển sang đọc/ghi dữ liệu mock (ví dụ: `raw-logs.sample.jsonl`, local analyzer) để không bị ngắt quãng.

## Git Workflow

- Quy trình chuẩn: `Code trên nhánh cá nhân -> Tạo Pull Request -> Tech Lead review -> Merge vào main -> Tự động Deploy`.
- Default branch: `main` (Chỉ Tech Lead được merge).
- Feature branches cá nhân: `feat/generator`, `feat/stream`, `feat/ml`, `feat/analytics`.
- Pull Request chỉ được duyệt khi pass bài test contract (`scripts/validate_contracts.py`) và có review từ Tech Lead.

## Notes

- Tranh thủ xem thêm `docs/team-workflow.md` để hiểu về Dependency Matrix giữa các nhóm.
- File `deploy.yml` đã thiết lập chế độ secret-gated. Khai báo các secrets `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY` để bật tự động deploy.
