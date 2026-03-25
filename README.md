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

- **Tech Lead**: 
  - Khởi tạo repo, quản lý `infra/`, `contracts/`, `docs/`, và CI/CD.
  - Thiết lập FastAPI skeleton cho `ml-api/` để có Mock API cho team làm việc.
  - Cung cấp file DDL/schema. Merge code và review PR.
- **Người 2 (Generator)**: 
  - Đọc `CONTRACTS.md` (mục Raw Log) để viết Python script sinh log định dạng JSON định kỳ và đẩy vào NATS topic `logs.raw`. 
  - Xử lý lỗi: nếu NATS down thì tự fail sớm.
- **Người 3 (Stream Processor)**: 
  - Dùng Spark Streaming đọc dữ liệu từ NATS.
  - Gửi dữ liệu gọi sang HTTP API `POST http://ml-api:8000/analyze`.
  - Ghi tổng hợp kết quả (kèm nhãn Bot, Dự báo tải, Độ trễ) vào ClickHouse.
  - Xử lý fallback (đọc file mẫu nếu NATS lỗi, dùng mock analyzer nội bộ nếu ML API sập, dump ra file nếu ClickHouse chưa lên).
- **Người 4 (ML & AI)**: 
  - Huấn luyện mô hình phát hiện Bot, dự đoán tải và độ trễ trên Colab/Jupyter (có thể tự tạo dataset theo schema hoặc lấy từ Kaggle).
  - Đưa mô hình thực tế vào thay thế cho logic Mock hiện tại trong FastAPI của module `ml-api/`.
- **Người 5 (Analytics)**: 
  - Không cần chờ luồng dữ liệu thật, dùng ngay dữ liệu mẫu (hoặc script `ensure_seed.py`) để thiết lập các bảng trong ClickHouse.
  - Xây dựng Dashboard trên Grafana để trực quan hóa đúng 3 bài toán: Bot, Tải, Bất thường.

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
