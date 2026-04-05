# Quy trình làm việc của nhóm (Team Workflow)

## Quyền sở hữu (Ownership)

- Tech Lead: `infra/`, `contracts/`, `.github/`, `docs/`, các tài liệu gốc.
- Thành viên 1: `generator/`
- Thành viên 2: `stream-processor/`
- Thành viên 3: `ml-api/`
- Thành viên 4: `analytics/`

## Phân nhánh (Branching)

- `main`: Chỉ Tech Lead mới có quyền merge.
- `feat/generator`: Chủ sở hữu generator.
- `feat/stream`: Chủ sở hữu stream.
- `feat/ml`: Chủ sở hữu ml.
- `feat/analytics`: Chủ sở hữu analytics.

## Ranh giới kiến trúc v2 (v2 architecture boundaries)

- `generator` chỉ chịu trách nhiệm sản xuất các sự kiện thô (raw events).
- `stream-processor` chịu trách nhiệm về các cửa sổ đặc trưng, trạng thái runtime, việc ghi vào ClickHouse và các phương án dự phòng (fallbacks).
- `ml-api` chỉ chịu trách nhiệm về logic dự đoán. Nó nhận các gói dữ liệu đặc trưng (feature payloads), không nhận các sự kiện gateway thô.
- `analytics` chịu trách nhiệm về ClickHouse DDL, dữ liệu mồi (seed data), các truy vấn kiểm tra (smoke queries) và các bảng điều khiển Grafana.

## Quy tắc phối hợp (Coordination rules)

- Các thay đổi về hợp đồng (contract changes) phải cập nhật `CONTRACTS.md`, các sơ đồ JSON (JSON schemas), các ví dụ và việc kiểm tra hợp đồng.
- Logic giả lập (mock logic) của Stream và ML phải giữ cho hành vi đồng bộ với nhau.
- Các thay đổi về bảng điều khiển (dashboard) phải được hỗ trợ bởi các bảng đã được nạp dữ liệu và các truy vấn kiểm tra.
- Nếu các cài đặt cửa sổ Spark (Spark window settings) thay đổi, hãy cập nhật cả các giá trị mặc định trong mã nguồn và tài liệu.

## Ma trận phụ thuộc (Dependency matrix)

| Nhóm | Phụ thuộc đầu vào | Phương án dự phòng khi thiếu phụ thuộc |
| --- | --- | --- |
| Generator | Kafka | Thất bại nhanh và thoát (Fail fast and exit) |
| Stream | Log thô từ Kafka | Tải `contracts/examples/raw-logs.sample.jsonl` |
| Stream | ML API | Sử dụng các hàm dự đoán tất định cục bộ |
| Stream | ClickHouse | Kết xuất các hàng theo bảng vào `stream-processor/output/processed_rows.mock.jsonl` |
| Analytics | Các hàng ClickHouse | `ensure_seed.py` tạo và nạp dữ liệu cho tất cả các bảng phân tích |
| ML | Các tạo vật mô hình (Model artifacts) | Giữ ở chế độ giả lập cho đến khi `ml-api/models/` chứa các tạo vật |

## Danh sách kiểm tra Pull request (Pull request checklist)

- Các hợp đồng vẫn hợp lệ.
- Các ví dụ về sơ đồ (Schema examples) đã được cập nhật.
- Hành vi dự phòng (Fallback behavior) vẫn hoạt động.
- Các bài kiểm tra (Tests) bao phủ được hành vi mới.
- Các thay đổi nằm trong ranh giới sở hữu trừ khi Tech Lead đã điều phối việc cập nhật.
