# Bao Cao Ban Giao Cong Viec ML API

## 1. Muc tieu cong viec
- Chuyen `ml-api` tu mock/heuristic baseline sang model-backed inference cho 3 bai toan:
  - Bot detection
  - Load forecasting
  - Anomaly detection
- Giu nguyen contract API v2 va fallback ve heuristic khi model khong san sang.

## 2. Kien truc hien tai
- `stream-processor` gom raw logs thanh feature windows va goi `ml-api`.
- `ml-api` nhan payload da tong hop, du doan theo tung task rieng:
  - `POST /predict/bot`
  - `POST /predict/forecast`
  - `POST /predict/anomaly`
- `GET /healthz` tra ve trang thai service va che do `mock`/`model`.

## 3. Cong viec da hoan thanh

### 3.1. Bot detection
- Dataset:
  - Nguon cong khai Zenodo web robot detection.
  - Dung file `simple_features.csv`.
- Training:
  - Train tren Colab bang `RandomForestClassifier`.
  - Feature chinh: `NUMBER_OF_REQUESTS`, `TOTAL_DURATION`, `AVERAGE_TIME`, `REPEATED_REQUESTS`, `HTTP_RESPONSE_*`, `*_METHOD`, `NIGHT`, `MAX_BARRAGE`.
  - Target: `ROBOT`.
- Artifact:
  - `ml-api/models/bot_model.joblib`
  - `ml-api/models/model_config.json`
- Tich hop:
  - `predict_bot()` trong `ml-api/src/ml_api/analyzer.py` da load model that neu artifact ton tai.
  - Neu loi load model hoac thieu config thi fallback ve heuristic cu.
- Kiem thu:
  - `/healthz` tra ve `mode: model`.
  - `/predict/bot` da test thanh cong voi payload duoc map truc tiep tu du lieu training.

### 3.2. Forecast
- Dataset:
  - Khong dung file tai san.
  - Lay du lieu truc tiep tu Wikimedia Analytics API.
  - Tien xu ly tren Colab thanh `forecast_training_dataset.csv`.
- Training:
  - Train tren Colab bang `RandomForestRegressor`.
  - Feature:
    - `history_rps_0..9`
    - `rolling_mean_5`
    - `rolling_std_5`
    - `hour_of_day`
    - `day_of_week`
  - Target: `target_next_rps`
- Artifact:
  - `ml-api/models/forecast_model.joblib`
  - `ml-api/models/forecast_model_config.json`
- Tich hop:
  - `predict_forecast()` da load model that va du doan `predicted_request_count`.
  - Van fallback ve heuristic cu neu model/config khong hop le.
- Kiem thu:
  - `/predict/forecast` tra ve `model-forecast-v2`.
  - Da test voi chuoi xu huong tang va chuoi on dinh thap, ket qua hop ly.

### 3.3. Anomaly detection
- Dataset:
  - Nguon goc tu Microsoft Cloud Monitoring Dataset.
  - Tien xu ly tren Colab thanh `anomaly_training_dataset.csv`.
- Training:
  - Train tren Colab bang `RandomForestClassifier`.
  - Feature:
    - `request_count`
    - `avg_latency_ms`
    - `p95_latency_ms`
    - `p99_latency_ms`
    - `status_5xx_ratio`
    - `baseline_avg_latency_ms`
    - `baseline_5xx_ratio`
  - Target: `target_is_anomaly`
- Artifact:
  - `ml-api/models/anomaly_model.joblib`
  - `ml-api/models/anomaly_model_config.json`
- Tich hop:
  - `predict_anomaly()` da load model that va tra `is_anomaly`, `anomaly_score`.
  - Van fallback ve heuristic cu neu model/config khong hop le.
- Kiem thu:
  - `/predict/anomaly` tra ve `model-anomaly-v2`.
  - Da test thanh cong payload anomaly va nhan score cao.

## 4. File chinh da cap nhat
- `ml-api/src/ml_api/analyzer.py`
  - Them logic load model cho bot, forecast, anomaly.
  - Giu fallback heuristic cho ca 3 task.
- `ml-api/requirements.txt`
  - Them `joblib` va `scikit-learn` de load artifact.
- `tests/test_ml_api.py`
  - Bo sung test cho model mode bot va healthz.
- `ml-api/models/`
  - Chua cac file artifact va config cua 3 model.

## 5. Cach xac nhan he thong dang dung model that
- Goi `GET /healthz`
- Ky vong:
  - `status = ok`
  - `mode = model`
- Goi tung endpoint:
  - `/predict/bot`
  - `/predict/forecast`
  - `/predict/anomaly`
- Kiem tra truong `model_version`:
  - `model-bot-v2`
  - `model-forecast-v2`
  - `model-anomaly-v2`

## 6. Tai lieu/nguon du lieu
- Bot detection:
  - Zenodo web robot detection dataset
- Forecast:
  - Wikimedia Analytics API
- Anomaly:
  - Microsoft Cloud Monitoring Dataset
- Link notebook Colab:
  - Xem `ml-api/models/colab.md`

## 7. Luu y khi ban giao
- Artifact `.joblib` la file model da train xong, can co san trong `ml-api/models/` de chay `model mode`.
- Neu artifact bi thieu hoac loi, `ml-api` se tu dong fallback sang heuristic.
- Forecast va anomaly dataset training la du lieu da tien xu ly tu nguon goc, khong phai file raw ban dau.

## 8. Ket qua tong ket
- Da hoan thanh tich hop model that cho ca 3 task trong `ml-api`.
- Da test API thanh cong o local bang Postman.
- He thong hien tai co the chay o `model mode` va san sang cho stream-processor goi den.
