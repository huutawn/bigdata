# AIOps Big Data Pipeline -- Project Documentation

## 1. Project Overview

**Name:** AIOps Big Data Pipeline (Đường ống dữ liệu lớn AIOps)

**Purpose:** A local-first prototype for real-time AIOps analytics covering three ML tasks:
1. **Bot Detection** -- from IP + session behavior windows
2. **Load Forecasting** -- from recent traffic history buckets
3. **Anomaly Detection** -- from latency and error rate windows

**Architecture v2:**
```
generator -> NATS -> stream-processor -> ml-api -> ClickHouse -> Grafana
```

**Data Flow:**
```
raw logs -> windowed features -> task-specific predictions -> ClickHouse tables -> Grafana dashboards
```

**Key Design Principle (v2):** Instead of sending a single raw event to a generic ML endpoint, the stream processor builds feature windows (grouped by entity or endpoint over time) and sends task-specific payloads to separate ML endpoints.

---

## 2. Repository Structure

```
.
|-- README.md                          # Project overview and quick start
|-- CONTRACTS.md                       # Single source of truth for all data contracts
|-- Makefile                           # GNU Make task runner (Linux + Windows)
|-- .env.example                       # Environment variable defaults
|
|-- generator/                         # Log generator (synthetic + replay)
|-- stream-processor/                  # Stream processing + windowing
|-- ml-api/                            # ML prediction service (FastAPI)
|-- analytics/                         # ClickHouse DDL, seed data, Grafana
|-- contracts/                         # JSON schemas + example payloads
|-- tests/                             # Unit tests for all components
|-- scripts/                           # Dev tooling (PowerShell + Python)
|-- infra/                             # Docker Compose infrastructure
|-- docs/                              # Architecture and workflow docs
|-- .github/                           # CI/CD workflows
```

---

## 3. Component Details

### 3.1 Generator (`generator/`)

| File | Lines | Purpose |
|---|---|---|
| `src/generator/main.py` | 287 | Synthetic log generator with 24-phase traffic cycle (bot, human, incident, mixed) |
| `src/generator/replay_access_logs.py` | 429 | Real access-log replay: parses Apache/Nginx combined format, synthesizes sessions, rebases timestamps |
| `requirements.txt` | 1 | `nats-py==2.10.0` |
| `Dockerfile` | 15 | Python 3.12-slim |

**Key features:**
- Deterministic log generation with seeded RNG
- 24-phase cycle simulating realistic traffic patterns (bot scraping, login probing, 5xx incidents, normal browsing, mobile, admin)
- Load profile with diurnal traffic variation and jitter
- Replay module supports `.log`, `.txt`, `.gz` files, Kaggle datasets, time-scale compression, session synthesis

### 3.2 Stream Processor (`stream-processor/`)

| File | Lines | Purpose |
|---|---|---|
| `src/stream_processor/main.py` | 939 | Core pipeline: NATS consumer, window builder, ML caller, ClickHouse writer, fallback handler |
| `src/stream_processor/mock_analyzer.py` | 76 | Deterministic mock prediction functions |
| `src/stream_processor/__init__.py` | 1 | Package init |
| `requirements.txt` | 1 | `nats-py==2.10.0` |
| `requirements-spark.txt` | 1 | `pyspark==3.5.5` (optional) |
| `Dockerfile` | 21 | Python 3.12-slim + OpenJDK 17 |

**Windowing configurations:**

| Task | Window | Slide | Grouping Key |
|---|---|---|---|
| Bot Detection | 60s | 10s | `ip + session_id + user_agent` |
| Anomaly Detection | 60s | 10s | `endpoint` |
| Load Forecasting | 60s buckets | -- | `system` + `endpoint` |

**Bot window features (14 total):**
`number_of_requests`, `total_duration_s`, `average_time_ms`, `repeated_requests`, `http_response_2xx/3xx/4xx/5xx`, `get_method`, `post_method`, `head_method`, `other_method`, `night`, `max_barrage`

**Anomaly window features (7 total):**
`request_count`, `avg_latency_ms`, `p95_latency_ms`, `p99_latency_ms`, `status_5xx_ratio`, `baseline_avg_latency_ms`, `baseline_5xx_ratio`

**Forecast features (5 total):**
`history_rps` (10-bucket history), `rolling_mean_5`, `rolling_std_5`, `hour_of_day`, `day_of_week`

**Fallback chain:**
- NATS unavailable -> load `contracts/examples/raw-logs.sample.jsonl`
- ML API unavailable -> use local mock analyzers
- ClickHouse unavailable -> dump rows to `stream-processor/output/processed_rows.mock.jsonl`

### 3.3 ML API (`ml-api/`)

| File | Lines | Purpose |
|---|---|---|
| `src/ml_api/main.py` | 141 | FastAPI REST API with Pydantic validation for 3 endpoints |
| `src/ml_api/analyzer.py` | 271 | Dual-mode prediction: real scikit-learn models OR heuristic mocks |
| `src/ml_api/__init__.py` | 1 | Package init |
| `requirements.txt` | 4 | `fastapi==0.115.12`, `uvicorn[standard]==0.34.0`, `joblib==1.4.2`, `scikit-learn==1.6.1` |
| `Dockerfile` | 17 | Python 3.12-slim |

**Endpoints:**
- `GET /healthz` -- reports status, mode (`mock` or `model`), and tasks
- `POST /predict/bot` -- bot detection
- `POST /predict/forecast` -- load forecasting
- `POST /predict/anomaly` -- anomaly detection

**Dual-mode operation:**
- **Model mode:** Loads `.joblib` artifacts from `ml-api/models/` and uses `model.predict_proba()` / `model.predict()`
- **Mock mode:** Uses deterministic heuristic scoring (weighted feature combinations)
- Forecast model has an additional **guardrail** that caps predictions against a heuristic upper bound

**Model artifacts:**
| File | Source | Training Data |
|---|---|---|
| `bot_model.joblib` | Google Colab | Kaggle web server access logs (218 rows in `simple_features.csv`) |
| `forecast_model.joblib` | Google Colab | Wikimedia Analytics API -- de.wikipedia.org pageviews (6,451 rows) |
| `anomaly_model.joblib` | Google Colab | Microsoft Cloud Monitoring Dataset (22,033 rows) |

### 3.4 Analytics (`analytics/`)

| File | Lines | Purpose |
|---|---|---|
| `sql/create_processed_logs.sql` | 64 | ClickHouse DDL for 4 tables |
| `sql/seed_processed_logs.sql` | 16 | Seed data INSERT statements |
| `grafana/dashboards/aiops-overview.json` | -- | Dashboard: Requests per Minute, Next Minute Forecast, Top Bot Entities, Endpoint Anomaly Alerts |
| `grafana/provisioning/datasources/datasource.yml` | -- | ClickHouse datasource auto-provisioning |
| `grafana/provisioning/dashboards/dashboard.yml` | -- | Dashboard auto-provisioning |
| `scripts/ensure_seed.py` | 46 | Creates tables and seeds data if empty |
| `scripts/query_smoke.py` | 33 | Smoke test queries against all 4 tables |

**ClickHouse tables:**

| Table | Engine | Order By |
|---|---|---|
| `processed_logs` | MergeTree | `(timestamp, ip, request_id)` |
| `bot_feature_windows` | MergeTree | `(window_end, ip, session_id)` |
| `load_forecasts` | MergeTree | `(predicted_bucket_end, scope, endpoint)` |
| `anomaly_alerts` | MergeTree | `(window_end, endpoint)` |

### 3.5 Tests (`tests/`)

| File | Lines | Coverage |
|---|---|---|
| `test_generator.py` | 101 | Log determinism, batch sizing, access log parsing, sessionizer, latency heuristics |
| `test_stream_processor.py` | 258 | Bot window aggregation, forecast history, fallback paths, ML API integration |
| `test_ml_api.py` | 291 | Prediction determinism, mode switching, model artifact loading, FastAPI endpoints |
| `test_contracts.py` | 14 | Contract validation (delegates to `validate_contracts.py`) |
| `test_analytics_assets.py` | 49 | DDL table existence, seed SQL, Grafana dashboard panels |

**Total test lines: 719**

### 3.6 Contracts (`contracts/`)

**8 JSON Schema files:**
- `raw-log.schema.json`
- `bot-request.schema.json`, `bot-response.schema.json`
- `forecast-request.schema.json`, `forecast-response.schema.json`
- `anomaly-request.schema.json`, `anomaly-response.schema.json`
- `processed-log.schema.json`

**9 Example files:**
- `raw-log.sample.json`, `raw-logs.sample.jsonl`
- `bot-request.sample.json`, `bot-response.sample.json`
- `forecast-request.sample.json`, `forecast-response.sample.json`
- `anomaly-request.sample.json`, `anomaly-response.sample.json`
- `processed-log.sample.json`

### 3.7 Scripts (`scripts/`)

| File | Lines | Purpose |
|---|---|---|
| `dev.ps1` | 265 | PowerShell task runner (Windows): infra, install, start/stop, validate, test |
| `validate_contracts.py` | 146 | Custom JSON Schema validator (no external dependencies) |

### 3.8 Infrastructure (`infra/`)

| File | Lines | Content |
|---|---|---|
| `docker-compose.yml` | 69 | 3 services: NATS, ClickHouse, Grafana |
| `clickhouse/users.d/default-user.xml` | 13 | ClickHouse user config (no password, all IPs allowed) |

**Infrastructure services:**

| Service | Image | Port | Memory Limit |
|---|---|---|---|
| NATS | `nats:2.10.22-alpine` | 4222 (client), 8222 (monitoring) | 128MB |
| ClickHouse | `clickhouse/clickhouse-server:24.12-alpine` | 8123 (HTTP), 9000 (native) | 768MB |
| Grafana | `grafana/grafana-oss:11.5.2` | 3000 | 384MB |

### 3.9 CI/CD (`.github/`)

| File | Lines | Content |
|---|---|---|
| `workflows/ci.yml` | 57 | Contract validation, unit tests, docker-compose validation, ClickHouse smoke test |
| `workflows/deploy.yml` | 23 | SSH-based deploy (gated by secrets) |
| `pull_request_template.md` | 18 | PR checklist (ownership, contracts, fallbacks, tests) |

---

## 4. Technologies / Frameworks

| Category | Technology |
|---|---|
| **Language** | Python 3.12 |
| **Message Broker** | NATS 2.10 (JetStream) |
| **Column Database** | ClickHouse 24.12 |
| **Visualization** | Grafana 11.5.2 |
| **Web Framework** | FastAPI 0.115 + Uvicorn 0.34 |
| **ML Libraries** | scikit-learn 1.6.1, joblib 1.4.2 |
| **Stream Processing** | Pure Python (default), PySpark 3.5.5 (optional) |
| **CI/CD** | GitHub Actions |
| **DevOps** | Docker Compose, GNU Make, PowerShell |

---

## 5. Line Count Summary

(excluding `.venv/`, `.git/`, `__pycache__/`, `.pyc` files)

| Component | Python Files | Total Lines |
|---|---|---|
| `stream-processor/` | 3 | 1,016 |
| `generator/` | 2 | 717 |
| `ml-api/` | 3 | 413 |
| `tests/` | 5 | 719 |
| `scripts/` | 2 | 411 |
| `analytics/` | 2 | 79 |
| **Total application Python** | **17** | **3,084** |

Additional files:
- `Makefile`: 277 lines
- `scripts/dev.ps1`: 265 lines
- `docs/`: 1,184 lines (5 files)
- `CONTRACTS.md`: 241 lines

---

## 6. ML Models: Real or Mock?

**Dual-mode system.** The ML API operates in two modes:

### Model Mode (when `.joblib` files exist)
- Loads real scikit-learn models via `joblib.load()`
- Uses `model.predict_proba()` for bot/anomaly (classification)
- Uses `model.predict()` for forecast (regression)
- Forecast has a **guardrail** that caps predictions against heuristic upper bounds
- Reports `mode: "model"` on `/healthz`

### Mock Mode (default, when no model artifacts)
- Uses deterministic heuristic scoring:
  - **Bot:** Weighted sum of request count, repeated requests, 4xx/5xx ratios, max barrage, night flag, suspicious user-agent, known bot IPs (threshold: 0.55)
  - **Forecast:** Current RPS + trend + smoothed rolling mean (smoothing: 0.2)
  - **Anomaly:** Weighted latency ratio, p95/p99 ratios, 5xx error delta vs baseline (threshold: 0.6)
- Reports `mode: "mock"` on `/healthz`

### Training Data Sources
| Model | Data Source | Rows | Notes |
|---|---|---|---|
| Bot | Kaggle web server access logs | 218 | `simple_features.csv` |
| Forecast | Wikimedia Analytics API (de.wikipedia.org) | 6,451 | Real hourly pageview data |
| Anomaly | Microsoft Cloud Monitoring Dataset | 22,033 | Ecommerce API latency data |

**Note:** Training happens in external Google Colab notebooks (linked in `ml-api/models/colab.md`). No training scripts exist in the repo.

---

## 7. Real Data Processing vs Simulated

### Real Processing
- NATS message pub/sub with batching, flushing, and timeout handling
- Sliding window aggregation (grouping events by entity/endpoint over time)
- Feature engineering (percentiles, rolling statistics, ratio computations)
- HTTP calls to ML API with timeout and error handling
- ClickHouse INSERT operations (JSONEachRow format)
- Fallback to file output when dependencies are unavailable

### Simulated by Default
- The default `generator` creates synthetic logs with a deterministic 24-phase pattern
- Mock mode uses heuristic scoring instead of trained models

### Real Data Option
- `replay_access_logs.py` can ingest real Apache/Nginx access logs
- Supports Kaggle datasets (`kagglehub` integration)
- Synthesizes sessions, infers route templates, estimates latency
- Time-scale compression for faster replay

---

## 8. Documentation Files

| File | Lines | Content |
|---|---|---|
| `docs/v2-streaming-design.md` | 497 | Architecture explanation: NATS batching vs ML windowing, feature payload construction, end-to-end flow |
| `docs/linux-testing.md` | 283 | Linux run guide, manual start instructions, Kaggle replay, test checklist |
| `docs/team-workflow.md` | 51 | Team ownership, branching strategy, dependency matrix, PR checklist |
| `docs/python-first-streaming.md` | 44 | Windows Python-first workflow (Spark is opt-in) |
| `docs/local-dev.md` | 109 | Local-first development guide, prerequisites, URLs, helper commands |

---

## 9. Team Ownership Model

| Role | Ownership |
|---|---|
| Tech Lead | `infra/`, `contracts/`, `.github/`, `docs/`, top-level docs |
| Member 1 | `generator/` |
| Member 2 | `stream-processor/` |
| Member 3 | `ml-api/` |
| Member 4 | `analytics/` |

**Branching:** `main` (Tech Lead merge), `feat/generator`, `feat/stream`, `feat/ml`, `feat/analytics`

---

## 10. Strengths

1. **Sound architecture:** The v2 window-based feature engineering correctly separates NATS transport batches from ML analysis windows. Task-specific payloads are well-designed.

2. **Comprehensive fallback chain:** Every dependency has a graceful degradation path -- NATS (fail fast), ML API (local mocks), ClickHouse (file output), no models (heuristic mocks).

3. **Strong contract discipline:** JSON schemas, example payloads, and a custom validator enforce interface consistency across team boundaries.

4. **Well-tested:** 719 lines of unit tests covering all components, including mock/fallback paths, model artifact loading, and FastAPI endpoint testing.

5. **Dual Python/Spark window builders:** Simple env var toggle (`STREAM_USE_SPARK_WINDOWS`) switches between pure-Python and PySpark-backed windowing.

6. **Real training data:** Forecast model trained on 6,451 rows of real Wikimedia traffic data; anomaly model on 22,033 rows from Microsoft's cloud monitoring dataset.

7. **Sophisticated replay capability:** The `replay_access_logs.py` module handles gzip, session synthesis, route template inference, latency heuristics, and time-scale compression.

8. **Cross-platform support:** PowerShell (Windows) and Bash (Linux) workflows, plus an OS-detecting Makefile.

9. **Good documentation:** 1,184 lines covering architecture, team workflow, and setup guides for both platforms.

10. **Forecast guardrail:** The forecast model has a safety mechanism that caps predictions against a heuristic upper bound to prevent runaway outputs.

---

## 11. Weaknesses

1. **No training scripts in repo:** Model training happens in external Google Colab notebooks. The training pipeline is not reproducible from the repo alone.

2. **ClickHouse security:** `default-user.xml` allows connections from `0.0.0.0/0` with no password. Fine for local dev, dangerous if exposed.

3. **Hardcoded Grafana credentials:** `admin/admin` is in `docker-compose.yml`.

4. **No integration/e2e tests:** All tests are unit tests with mocking. No test runs the full pipeline end-to-end with real NATS, ML API, and ClickHouse.

5. **Deploy workflow is incomplete:** Only restarts infrastructure containers. Does not deploy application services (generator, stream-processor, ml-api).

6. **No structured logging:** All components use `print()`. No log levels, no structured logging, no log rotation.

7. **No application observability:** Only infrastructure has healthchecks. Application services have no `/metrics` endpoint beyond ML API's `/healthz`.

8. **No proper packaging:** No `pyproject.toml` or `setup.py`. Everything assumes Python 3.12 with manual `PYTHONPATH` setup.

9. **No linting/type-checking in CI:** No `mypy`, `ruff`, `flake8`, or `black` in the CI pipeline.

10. **Tiny sample training data:** `sample_training.csv` has only 4 rows -- clearly placeholder data.

11. **Windows-only dev script:** `dev.ps1` is PowerShell-only. No equivalent Bash dev script for Linux (Linux users must use Make or manual commands).

12. **No backpressure mechanism:** The stream processor polls NATS with a fixed interval. If ML API or ClickHouse is slow, there is no backpressure or queue management.

---

## 12. Quick Start

### Windows (PowerShell)
```powershell
.\scripts\dev.ps1 create-venv
.\scripts\dev.ps1 install-all
.\scripts\dev.ps1 infra-up
.\scripts\dev.ps1 start-all
.\scripts\dev.ps1 analytics-seed
```

### Linux (Make)
```bash
make create-venv
make install-all
make infra-up
make start-all
make analytics-seed
```

### Local URLs
| Service | URL |
|---|---|
| NATS | `nats://127.0.0.1:4222` |
| ML API | `http://127.0.0.1:8000` |
| ClickHouse | `http://127.0.0.1:8123` |
| Grafana | `http://127.0.0.1:3000` (admin/admin) |

### Validation
```bash
python scripts/validate_contracts.py
python -m unittest discover -s tests -p "test_*.py" -v
```
