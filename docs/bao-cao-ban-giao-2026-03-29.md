# BAO CAO BAN GIAO DU AN AIOps Big Data Pipeline

## 1. Thong tin chung

- Thoi diem lap bao cao: 2026-03-29
- Thu muc du an: `D:\bigdata-main`
- Nhanh hien tai: `main`
- Trang thai Git tai thoi diem ban giao: khong co thay doi chua commit theo `git status --short`

## 2. Pham vi du an ban giao

Du an hien tai la mot pipeline AIOps local-first phuc vu 3 bai toan:

1. Phat hien bot dua tren IP, session va user agent.
2. Du bao tai dua tren nhom lich su luu luong.
3. Phat hien bat thuong hieu suat dua tren do tre va loi.

Kien truc tong the:

`generator -> NATS -> stream-processor -> ml-api -> ClickHouse -> Grafana`

Thanh phan chinh trong repo:

- `generator/`: sinh raw log va day vao NATS.
- `stream-processor/`: doc log tu NATS, tao feature windows, goi ML API hoac fallback, ghi vao ClickHouse.
- `ml-api/`: cung cap endpoint du doan cho bot, forecast, anomaly.
- `analytics/`: DDL ClickHouse, seed data, smoke query, dashboard Grafana.
- `infra/`: Docker Compose cho NATS, ClickHouse, Grafana.
- `contracts/` va `CONTRACTS.md`: quy dinh payload, schema va vi du du lieu.
- `scripts/dev.ps1`: task runner chinh de khoi tao va van hanh local.

## 3. Cach van hanh du an

### 3.1 Ha tang dung chung chay bang Docker

Theo `infra/docker-compose.yml`, cac dich vu ha tang duoc cau hinh:

- NATS
- ClickHouse
- Grafana

Cong mac dinh:

- NATS client: `4222`
- NATS monitor: `8222`
- ClickHouse HTTP: `8123`
- ClickHouse native: `9000`
- Grafana: `3000`
- ML API host port: `8000`

### 3.2 Dich vu ung dung chay tren host

Theo tai lieu va script hien tai, cac dich vu sau duoc thiet ke de chay truc tiep tren may:

- `generator`
- `stream-processor`
- `ml-api`

Virtual environment duoc dat tai:

- `.venv/`

Lenh khoi tao/van hanh de xuat:

```powershell
.\scripts\dev.ps1 create-venv
.\scripts\dev.ps1 install-all
.\scripts\dev.ps1 infra-up
.\scripts\dev.ps1 start-all
```

Lenh dung:

```powershell
.\scripts\dev.ps1 stop-local
.\scripts\dev.ps1 infra-down
```

Luu y tren may Windows hien tai can goi script voi `-ExecutionPolicy Bypass`, vi goi truc tiep `.\scripts\dev.ps1 ...` dang bi chan boi PowerShell execution policy.

Vi du:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 test
```

## 4. Trang thai thuc te tai thoi diem ban giao

### 4.1 Ket qua kiem tra

Da thuc hien cac lenh kiem tra sau:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 validate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 test
```

Ket qua:

- `validate`: thanh cong, thong bao `Contracts and examples are valid.`
- `test`: thanh cong, tong cong 12 test, `OK (skipped=1)`

Chi tiet can luu y:

- 11 test pass.
- 1 test bi skip: `test_healthz_and_prediction_endpoints`, ly do `fastapi is not installed`.

### 4.2 Tinh trang log va process local

Thu muc log local hien co:

- `.local-dev/generator.out.log`
- `.local-dev/generator.err.log`
- `.local-dev/ml-api.out.log`
- `.local-dev/ml-api.err.log`
- `.local-dev/stream-processor.out.log`
- `.local-dev/stream-processor.err.log`

Quan sat log:

- `generator.out.log` cho thay generator da publish deu raw logs vao subject `logs.raw`.
- `stream-processor.out.log` cho thay stream processor da xu ly log va ghi du lieu, co cac ban ghi dang:
  - `Processed 5 raw logs from nats and wrote to clickhouse (...)`
- `ml-api.err.log` ghi nhan loi:
  - `.venv\Scripts\python.exe: No module named uvicorn`

Kiem tra PID file trong `.local-dev/` cho thay:

- Co ton tai file PID cu cho `generator`, `ml-api`, `stream-processor`.
- Tuy nhien process voi cac PID do khong con ton tai.

Ket luan hien trang van hanh:

- Repo o trang thai sach ve Git.
- Contracts va unit tests dang dat.
- Co dau vet cho thay `generator` va `stream-processor` tung chay va xu ly du lieu thanh cong.
- Cac process local hien khong con chay du, PID file dang la du lieu cu.
- `ml-api` dang gap van de thieu dependency runtime trong `.venv`.

## 5. Cau hinh quan trong

Theo `.env.example`, mot so bien cau hinh chinh:

- `NATS_URL=nats://nats:4222`
- `NATS_SUBJECT=logs.raw`
- `ML_API_URL=http://127.0.0.1:8000`
- `CLICKHOUSE_URL=http://127.0.0.1:8123`
- `GENERATOR_BATCH_SIZE=5`
- `STREAM_BATCH_SIZE=5`
- `BOT_WINDOW_SECONDS=60`
- `BOT_WINDOW_SLIDE_SECONDS=10`
- `ANOMALY_WINDOW_SECONDS=60`
- `ANOMALY_WINDOW_SLIDE_SECONDS=10`
- `ANOMALY_BASELINE_LOOKBACK_SECONDS=300`
- `FORECAST_BUCKET_SECONDS=60`
- `FORECAST_HISTORY_SIZE=10`
- `STREAM_USE_SPARK_WINDOWS=1`

## 6. Hop dong va ranh gioi phu trach

Theo `docs/team-workflow.md`:

- Tech Lead phu trach: `infra/`, `contracts/`, `.github/`, `docs/`
- Thanh vien 1: `generator/`
- Thanh vien 2: `stream-processor/`
- Thanh vien 3: `ml-api/`
- Thanh vien 4: `analytics/`

Nguyen tac quan trong khi tiep nhan:

- Moi thay doi contract phai cap nhat `CONTRACTS.md`, schema, examples va validation.
- `stream-processor` va `ml-api` phai dong bo logic fallback/mock.
- Neu doi thong so windowing thi can cap nhat ca code va tai lieu.

## 7. Ton dong, rui ro va huong xu ly

### 7.1 Ton dong hien huu

1. PowerShell tren may hien tai chan thuc thi script mac dinh.
2. `ml-api` khong khoi dong duoc trong moi truong hien tai do thieu `uvicorn`.
3. Test endpoint cua ML API dang bi skip do thieu `fastapi`.
4. Thu muc `.local-dev/` dang con PID file cu, de gay nham rang dich vu van dang chay.

### 7.2 Nhan dinh nguyen nhan kha nang cao

- Moi truong `.venv` chua duoc cai day du bang `install-all`, hoac da duoc tao tuoc nhung chua dong bo dependency moi nhat.
- `ml-api/requirements.txt` co khai bao:
  - `fastapi==0.115.12`
  - `uvicorn[standard]==0.34.0`

Vi vay loi nhieu kha nang nam o moi truong cai dat, khong phai do thieu khai bao dependency trong repo.

### 7.3 De xuat cho nguoi nhan ban giao

1. Chay lai cai dat dependency:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 install-all
```

2. Xoa PID cu neu can lam sach trang thai local:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 stop-local
```

3. Khoi dong lai he thong:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 infra-up
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 start-all
```

4. Kiem tra sau khoi dong:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 validate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 test
```

5. Neu can dashboard co du lieu mau:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 analytics-seed
```

## 8. Ket luan ban giao

Tai thoi diem ban giao, repo co cau truc ro rang, tai lieu tuong doi day du, contracts hop le va bo test hien tai dat yeu cau. He thong da co dau vet cho thay generator va stream processor tung van hanh duoc. Van de chinh can xu ly ngay sau tiep nhan la dong bo lai moi truong `.venv` de khoi phuc `ml-api`, dong thoi lam sach cac PID/log cu de tranh nham lan trang thai chay.
