# Đường ống dữ liệu lớn AIOps (AIOps Big Data Pipeline)

Kho lưu trữ này là một bản mẫu thử nghiệm AIOps ưu tiên chạy cục bộ (local-first) cho ba nhiệm vụ phân tích luồng:

1. Phát hiện Bot từ IP và các cửa sổ hành vi phiên (session behavior windows).
2. Dự báo tải (Load forecasting) từ các nhóm lịch sử lưu lượng truy cập gần đây.
3. Phát hiện bất thường về hiệu suất (Performance anomaly detection) từ các cửa sổ độ trễ và lỗi.

Kiến trúc v2 là:

`generator -> NATS -> stream-processor -> ml-api -> ClickHouse -> Grafana`

Dự án hiện đang sử dụng:

`raw logs -> windowed features -> task-specific predictions`
(log thô -> các đặc trưng theo cửa sổ -> các dự đoán cụ thể theo nhiệm vụ)

Thay vì gửi một sự kiện thô duy nhất đến một endpoint ML chung chung, bộ xử lý luồng sẽ xây dựng:
- Các cửa sổ đặc trưng của bot được định danh bằng `ip + session_id + user_agent`
- Các cửa sổ đặc trưng bất thường được định danh bằng `endpoint`
- Các nhóm dự báo được định danh bằng `system` và `endpoint`

ML API cung cấp:
- `POST /predict/bot`
- `POST /predict/forecast`
- `POST /predict/anomaly`

## Cấu trúc kho lưu trữ (Repository layout)

```text
.
|-- CONTRACTS.md
|-- contracts/
|-- docs/
|-- infra/
|-- generator/
|-- stream-processor/
|-- ml-api/
|-- analytics/
|-- scripts/
`-- tests/
```

## Quyền sở hữu (Ownership)

- Tech Lead: `infra/`, `contracts/`, các tài liệu cấp cao, CI/CD
- Chủ sở hữu máy phát (Generator owner): `generator/`
- Chủ sở hữu luồng (Stream owner): `stream-processor/`
- Chủ sở hữu ML (ML owner): `ml-api/`
- Chủ sở hữu phân tích (Analytics owner): `analytics/`

## Hợp đồng dữ liệu (Contracts)

Xem [CONTRACTS.md](CONTRACTS.md) để biết các định nghĩa gói dữ liệu v2.

Các quy tắc quan trọng:
- Log thô là đầu vào cấp độ sự kiện (event-level)
- Các yêu cầu ML là các gói dữ liệu đặc trưng theo cửa sổ (feature-window payloads)
- Các dự đoán là đầu ra cụ thể theo nhiệm vụ

## Quy trình làm việc ưu tiên cục bộ (Local-first workflow)

Docker Compose chỉ chạy cơ sở hạ tầng dùng chung:
- NATS
- ClickHouse
- Grafana

Các dịch vụ ứng dụng chạy trực tiếp trên máy chủ (host):
- `generator/`
- `stream-processor/`
- `ml-api/`

Tất cả các lệnh ứng dụng cục bộ hiện đều sử dụng môi trường ảo của dự án trong `.venv/`.

### Quy trình được đề xuất trên Windows

```powershell
.\scripts\dev.ps1 create-venv
.\scripts\dev.ps1 install-all
.\scripts\dev.ps1 infra-up
.\scripts\dev.ps1 start-all
```

Windows local development now defaults to Python windowing for `stream-processor`.
`install-all` no longer installs `pyspark`; opt into Spark only when needed.
See [docs/python-first-streaming.md](docs/python-first-streaming.md) for the Windows workflow.

Dừng các dịch vụ cục bộ bằng:

```powershell
.\scripts\dev.ps1 stop-local
.\scripts\dev.ps1 infra-down
```

### Kích hoạt thủ công (tùy chọn)

Nếu bạn muốn làm việc trực tiếp bên trong môi trường ảo:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Quy trình làm việc tùy chọn với Make

Nếu đã cài đặt GNU Make:

```powershell
make create-venv
make install-all
make infra-up
make start-all
```

Optional Spark on Windows:

```powershell
make install-stream-spark
$env:STREAM_USE_SPARK_WINDOWS='1'
make run-stream
```

### Nếu thiếu `make`

Bạn không cần `make` cho kho lưu trữ này.
Sử dụng `.\scripts\dev.ps1` thay thế.

Nếu bạn vẫn muốn có GNU Make trên Windows, hãy cài đặt bằng một trong các cách sau:
- `choco install make`
- `scoop install make`
- MSYS2 sau đó chạy `pacman -S make`

Kiểm tra cài đặt bằng:

```powershell
make --version
```

## Bắt đầu nhanh (Quick start)

1. Sao chép `.env.example` thành `.env` nếu bạn muốn các cài đặt tùy chỉnh.
2. Tạo môi trường ảo cục bộ:

```powershell
.\scripts\dev.ps1 create-venv
```

3. Cài đặt các phụ thuộc:

```powershell
.\scripts\dev.ps1 install-all
```

4. Khởi động hạ tầng dùng chung:

```powershell
.\scripts\dev.ps1 infra-up
```

5. Khởi động các dịch vụ ứng dụng cục bộ:

```powershell
.\scripts\dev.ps1 start-all
```

6. Nạp dữ liệu các bảng phân tích (Seed analytics tables) nếu bạn muốn có dữ liệu mồi cho bảng điều khiển:

```powershell
.\scripts\dev.ps1 analytics-seed
```

7. Kiểm tra kho lưu trữ:

```powershell
.\scripts\dev.ps1 validate
.\scripts\dev.ps1 test
```

## Các mặc định về cửa sổ (Windowing defaults)

- Cửa sổ Bot: 60 giây, trượt 10 giây
- Cửa sổ bất thường (Anomaly window): 60 giây, trượt 10 giây
- Xem lại đường cơ sở bất thường (Anomaly baseline lookback): 5 phút
- Nhóm dự báo (Forecast bucket): 60 giây
- Kích thước lịch sử dự báo: 10 nhóm

Những giá trị này có thể thay đổi trong `.env.example`.

## Các bảng phân tích (Analytics tables)

ClickHouse lưu trữ:
- `processed_logs`
- `bot_feature_windows`
- `load_forecasts`
- `anomaly_alerts`

Grafana đọc trực tiếp từ các bảng này.

## Quy trình làm việc của nhóm (Team workflow)

- Thay đổi các hợp đồng (contracts) trước.
- Cập nhật các ví dụ cùng với các sơ đồ (schemas).
- Giữ logic dự phòng của luồng (stream fallback logic) đồng bộ với logic giả lập của ML (ML mock logic).
- Không chỉnh sửa mã nguồn của chủ sở hữu khác trừ khi thay đổi hợp đồng yêu cầu công việc phối hợp.
- Chạy `python scripts/validate_contracts.py` và `python -m unittest discover -s tests -p "test_*.py" -v` trước khi merge.

