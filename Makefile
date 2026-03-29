.RECIPEPREFIX := >
.ONESHELL:
SHELL := powershell.exe
.SHELLFLAGS := -NoProfile -ExecutionPolicy Bypass -Command

ROOT := $(CURDIR)
LOCAL_STATE_DIR := $(ROOT)/.local-dev
VENV_DIR := $(ROOT)/.venv
VENV_PYTHON := $(VENV_DIR)/Scripts/python.exe
NATS_URL_LOCAL := nats://127.0.0.1:4222
ML_API_URL_LOCAL := http://127.0.0.1:8000
CLICKHOUSE_URL_LOCAL := http://127.0.0.1:8123

.PHONY: help infra-up infra-down create-venv install-generator install-stream install-stream-spark install-ml-api install-all \
        run-generator run-stream run-ml-api start-generator start-stream start-ml-api \
        start-all stop-local analytics-seed analytics-query validate test

help:
> Write-Host 'Targets:'
> Write-Host '  infra-up         Start NATS, ClickHouse, and Grafana in Docker'
> Write-Host '  infra-down       Stop infra containers and remove volumes'
> Write-Host '  create-venv      Create the local project virtual environment'
> Write-Host '  install-all      Install base Python dependencies for all local app services'
> Write-Host '  install-stream-spark Install optional Spark dependency for stream-processor'
> Write-Host '  run-ml-api       Run the ML API in the current terminal'
> Write-Host '  run-generator    Run the generator in the current terminal'
> Write-Host '  run-stream       Run the stream processor in the current terminal'
> Write-Host '  start-all        Start ML API, generator, and stream processor in background'
> Write-Host '  stop-local       Stop local background app services started by Makefile'
> Write-Host '  analytics-seed   Create and seed the ClickHouse table from the host'
> Write-Host '  analytics-query  Run the analytics smoke queries from the host'
> Write-Host '  validate         Validate contracts'
> Write-Host '  test             Run bootstrap unit tests'

infra-up:
> docker-compose -f infra/docker-compose.yml --env-file .env up -d --remove-orphans nats clickhouse grafana

infra-down:
> docker-compose -f infra/docker-compose.yml --env-file .env down -v

create-venv:
> if (-not (Test-Path '$(VENV_PYTHON)')) { python -m venv '$(VENV_DIR)' }
> & '$(VENV_PYTHON)' -m pip install --upgrade pip

install-generator:
> $(MAKE) create-venv
> & '$(VENV_PYTHON)' -m pip install -r generator/requirements.txt

install-stream:
> $(MAKE) create-venv
> & '$(VENV_PYTHON)' -m pip install -r stream-processor/requirements.txt

install-stream-spark:
> $(MAKE) install-stream
> & '$(VENV_PYTHON)' -m pip install -r stream-processor/requirements-spark.txt

install-ml-api:
> $(MAKE) create-venv
> & '$(VENV_PYTHON)' -m pip install -r ml-api/requirements.txt

install-all:
> $(MAKE) install-generator
> $(MAKE) install-stream
> $(MAKE) install-ml-api

run-ml-api:
> $$env:ML_API_PORT = '8000'
> $$env:ML_MODELS_DIR = '$(ROOT)/ml-api/models'
> $$env:PYTHONPATH = '$(ROOT)/ml-api/src'
> & '$(VENV_PYTHON)' -m uvicorn ml_api.main:app --host 127.0.0.1 --port 8000

run-generator:
> $$env:NATS_URL = '$(NATS_URL_LOCAL)'
> $$env:NATS_SUBJECT = 'logs.raw'
> $$env:PYTHONPATH = '$(ROOT)/generator/src'
> & '$(VENV_PYTHON)' -m generator.main

run-stream:
> $$env:NATS_URL = '$(NATS_URL_LOCAL)'
> $$env:NATS_SUBJECT = 'logs.raw'
> $$env:ML_API_URL = '$(ML_API_URL_LOCAL)'
> $$env:CLICKHOUSE_URL = '$(CLICKHOUSE_URL_LOCAL)'
> $$env:STREAM_FALLBACK_OUTPUT_PATH = '$(ROOT)/stream-processor/output/processed_rows.mock.jsonl'
> $$env:PYTHONPATH = '$(ROOT)/stream-processor/src'
> & '$(VENV_PYTHON)' -m stream_processor.main

start-ml-api:
> New-Item -ItemType Directory -Force '$(LOCAL_STATE_DIR)' | Out-Null
> $$command = "$$env:ML_API_PORT='8000'; $$env:ML_MODELS_DIR='$(ROOT)/ml-api/models'; $$env:PYTHONPATH='$(ROOT)/ml-api/src'; & '$(VENV_PYTHON)' -m uvicorn ml_api.main:app --host 127.0.0.1 --port 8000"
> $$process = Start-Process powershell -WorkingDirectory '$(ROOT)' -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-Command', $$command -PassThru -RedirectStandardOutput '$(LOCAL_STATE_DIR)/ml-api.out.log' -RedirectStandardError '$(LOCAL_STATE_DIR)/ml-api.err.log'
> $$process.Id | Set-Content '$(LOCAL_STATE_DIR)/ml-api.pid'
> Write-Host "Started ml-api (PID=$$($$process.Id))"

start-generator:
> New-Item -ItemType Directory -Force '$(LOCAL_STATE_DIR)' | Out-Null
> $$command = "$$env:NATS_URL='$(NATS_URL_LOCAL)'; $$env:NATS_SUBJECT='logs.raw'; $$env:PYTHONPATH='$(ROOT)/generator/src'; & '$(VENV_PYTHON)' -m generator.main"
> $$process = Start-Process powershell -WorkingDirectory '$(ROOT)' -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-Command', $$command -PassThru -RedirectStandardOutput '$(LOCAL_STATE_DIR)/generator.out.log' -RedirectStandardError '$(LOCAL_STATE_DIR)/generator.err.log'
> $$process.Id | Set-Content '$(LOCAL_STATE_DIR)/generator.pid'
> Write-Host "Started generator (PID=$$($$process.Id))"

start-stream:
> New-Item -ItemType Directory -Force '$(LOCAL_STATE_DIR)' | Out-Null
> $$command = "$$env:NATS_URL='$(NATS_URL_LOCAL)'; $$env:NATS_SUBJECT='logs.raw'; $$env:ML_API_URL='$(ML_API_URL_LOCAL)'; $$env:CLICKHOUSE_URL='$(CLICKHOUSE_URL_LOCAL)'; $$env:STREAM_FALLBACK_OUTPUT_PATH='$(ROOT)/stream-processor/output/processed_rows.mock.jsonl'; $$env:PYTHONPATH='$(ROOT)/stream-processor/src'; & '$(VENV_PYTHON)' -m stream_processor.main"
> $$process = Start-Process powershell -WorkingDirectory '$(ROOT)' -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-Command', $$command -PassThru -RedirectStandardOutput '$(LOCAL_STATE_DIR)/stream-processor.out.log' -RedirectStandardError '$(LOCAL_STATE_DIR)/stream-processor.err.log'
> $$process.Id | Set-Content '$(LOCAL_STATE_DIR)/stream-processor.pid'
> Write-Host "Started stream-processor (PID=$$($$process.Id))"

start-all:
> $(MAKE) infra-up
> $(MAKE) start-ml-api
> Start-Sleep -Seconds 2
> $(MAKE) start-generator
> $(MAKE) start-stream
> Write-Host "Local stack started. Logs are in $(LOCAL_STATE_DIR)"

stop-local:
> if (Test-Path '$(LOCAL_STATE_DIR)') {
>   Get-ChildItem '$(LOCAL_STATE_DIR)' -Filter '*.pid' | ForEach-Object {
>     $$pid = Get-Content $$_.FullName
>     if ($$pid) {
>       Stop-Process -Id ([int]$$pid) -Force -ErrorAction SilentlyContinue
>     }
>     Remove-Item $$_.FullName -Force -ErrorAction SilentlyContinue
>   }
> }

analytics-seed:
> $$env:CLICKHOUSE_URL = '$(CLICKHOUSE_URL_LOCAL)'
> & '$(VENV_PYTHON)' analytics/scripts/ensure_seed.py

analytics-query:
> $$env:CLICKHOUSE_URL = '$(CLICKHOUSE_URL_LOCAL)'
> & '$(VENV_PYTHON)' analytics/scripts/query_smoke.py

validate:
> & '$(VENV_PYTHON)' scripts/validate_contracts.py

test:
> & '$(VENV_PYTHON)' -m unittest discover -s tests -p "test_*.py" -v
