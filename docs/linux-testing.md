# Linux Run and Manual Test Guide

This guide shows the simplest way to run the project on Linux and manually verify the main services.

## Prerequisites

- Python 3.12
- Docker and Docker Compose
- Bash
- Optional: GNU Make

## Quick start with Make

```bash
cd /path/to/bigdata
make create-venv
make install-all
make infra-up
make start-all
```

`make` on Linux now uses Bash-native recipes. The earlier `powershell.exe` error happened because the old `Makefile` was Windows-only.

This starts:

- Kafka for host apps on `127.0.0.1:9094`
- ClickHouse on `127.0.0.1:8123`
- Grafana on `127.0.0.1:3000`
- ML API on `127.0.0.1:8000`
- Generator on the host
- Stream processor on the host

Stop everything with:

```bash
make stop-local
make infra-down
```

## Manual start without Make

Create the virtual environment and install dependencies:

```bash
cd /path/to/bigdata
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r generator/requirements.txt
pip install -r stream-processor/requirements.txt
pip install -r ml-api/requirements.txt
```

Start shared infrastructure:

```bash
docker-compose -f infra/docker-compose.yml --env-file .env.example up -d kafka clickhouse grafana
```

Start the application services in separate terminals.

Terminal 1, ML API:

```bash
cd /path/to/bigdata
source .venv/bin/activate
PYTHONPATH=$PWD/ml-api/src ML_MODELS_DIR=$PWD/ml-api/models python -m uvicorn ml_api.main:app --host 127.0.0.1 --port 8000
```

Terminal 2, generator:

```bash
cd /path/to/bigdata
source .venv/bin/activate
PYTHONPATH=$PWD/generator/src \
KAFKA_BOOTSTRAP_SERVERS=localhost:9094 \
KAFKA_TOPIC=logs.raw \
python -m generator.main
```

If you want to replace the synthetic generator with a real access-log file, stop the default generator and run the replay module instead.

For a local file already copied into the repo, for example `./access.log`, run:

```bash
cd /path/to/bigdata
source .venv/bin/activate
PYTHONPATH=$PWD/generator/src \
KAFKA_BOOTSTRAP_SERVERS=localhost:9094 \
KAFKA_TOPIC=logs.raw \
python -m generator.replay_access_logs --input-dir "$PWD/access.log" --time-scale 600 --repeat
```

Preview the first normalized records without publishing to Kafka:

```bash
PYTHONPATH=$PWD/generator/src \
python -m generator.replay_access_logs \
  --input-dir "$PWD/access.log" \
  --max-records 50 \
  --output-jsonl .local-dev/access-preview.jsonl \
  --skip-publish
```

The replay module accepts either a single file path such as `access.log` or a directory containing many `.log`, `.txt`, or `.gz` files.

If your source really comes from a directory returned by Kaggle, that still works too:

This works with a directory returned by:

```python
import kagglehub

path = kagglehub.dataset_download("eliasdabbas/web-server-acc-logs")
```

If your `kaggle.json` is stored in the project root instead of `~/.kaggle/kaggle.json`, make sure it is owner-only:

```bash
chmod 600 kaggle.json
```

And point Kaggle to the current directory before downloading:

```bash
export KAGGLE_CONFIG_DIR=$PWD
```

Then run:

```bash
cd /path/to/bigdata
source .venv/bin/activate
KAGGLE_LOG_DIR=/path/returned/by/kagglehub
export KAGGLE_CONFIG_DIR=$PWD
PYTHONPATH=$PWD/generator/src \
KAFKA_BOOTSTRAP_SERVERS=localhost:9094 \
KAFKA_TOPIC=logs.raw \
python -m generator.replay_access_logs --input-dir "$KAGGLE_LOG_DIR" --time-scale 600 --repeat
```

What this replay module does:

- finds `.log`, `.txt`, or `.gz` access-log files under the dataset directory
- parses combined Apache/Nginx-style lines into the repo's `raw-log v2` schema
- rebases the old 2019 timestamps to "now" so Grafana shows live data
- synthesizes `request_id`, `session_id`, `route_template`, and `latency_ms`

If you only want to preview the normalized output without publishing to Kafka:

```bash
PYTHONPATH=$PWD/generator/src \
python -m generator.replay_access_logs \
  --input-dir "$KAGGLE_LOG_DIR" \
  --max-records 50 \
  --output-jsonl .local-dev/kaggle.raw.jsonl \
  --skip-publish
```

Terminal 3, stream processor:

```bash
cd /path/to/bigdata
source .venv/bin/activate
PYTHONPATH=$PWD/stream-processor/src \
KAFKA_BOOTSTRAP_SERVERS=localhost:9094 \
KAFKA_TOPIC=logs.raw \
ML_API_URL=http://127.0.0.1:8000 \
CLICKHOUSE_URL=http://127.0.0.1:8123 \
python -m stream_processor.main
```

## Manual test checklist

### 1. Check ML API

```bash
curl http://127.0.0.1:8000/healthz
```

Expected result:

- `status` should be `ok`
- `tasks` should include `bot`, `forecast`, and `anomaly`

### 2. Check generator

Watch the generator terminal or log output.

Expected result:

- repeated messages showing raw logs are being published to `logs.raw`

### 3. Check stream processor

Watch the stream processor terminal or log output.

Expected result:

- repeated messages showing raw logs are processed
- output should mention bot windows, forecasts, and anomalies

### 4. Test ML endpoints manually

Bot prediction:

```bash
curl -X POST http://127.0.0.1:8000/predict/bot \
  -H "Content-Type: application/json" \
  -d '{
    "feature_version": "v2",
    "window_start": "2026-03-24T10:00:00Z",
    "window_end": "2026-03-24T10:01:00Z",
    "entity": {
      "ip": "1.2.3.4",
      "session_id": "sess-bot-1",
      "user_agent": "Googlebot/2.1"
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
  }'
```

### 5. Seed and query analytics tables

If Grafana is empty, seed data manually:

```bash
cd /path/to/bigdata
source .venv/bin/activate
CLICKHOUSE_URL=http://127.0.0.1:8123 python analytics/scripts/ensure_seed.py
CLICKHOUSE_URL=http://127.0.0.1:8123 python analytics/scripts/query_smoke.py
```

Expected result:

- row counts returned for `processed_logs`
- row counts returned for `bot_feature_windows`
- row counts returned for `load_forecasts`
- row counts returned for `anomaly_alerts`

## Grafana

Open:

- [http://127.0.0.1:3000](http://127.0.0.1:3000)

Default login:

- username: `admin`
- password: `admin`

After login, open the dashboard:

- `AIOps Overview`

If the dashboard is empty:

- confirm `docker-compose` started `clickhouse` and `grafana`
- confirm `ml-api`, `generator`, and `stream-processor` are running
- run the analytics seed commands above

## Useful checks

Run the automated test suite:

```bash
cd /path/to/bigdata
source .venv/bin/activate
python -m unittest discover -s tests -p "test_*.py" -v
```
