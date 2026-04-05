.RECIPEPREFIX := >

ROOT := $(CURDIR)
LOCAL_STATE_DIR := $(ROOT)/.local-dev
VENV_DIR := $(ROOT)/.venv
ENV_FILE := $(if $(wildcard $(ROOT)/.env),$(ROOT)/.env,$(ROOT)/.env.example)
KAFKA_BOOTSTRAP_SERVERS_LOCAL := localhost:9094
KAFKA_TOPIC_LOCAL := logs.raw
ML_API_URL_LOCAL := http://127.0.0.1:8000
CLICKHOUSE_URL_LOCAL := http://127.0.0.1:8123

.PHONY: help infra-up infra-down create-venv install-generator install-stream install-ml-api install-all \
        run-generator run-replay run-stream run-ml-api start-generator start-replay start-stream start-ml-api \
        start-all stop-local analytics-seed analytics-query validate test

REPLAY_INPUT ?= $(ROOT)/access.log
REPLAY_TIME_SCALE ?= 30
REPLAY_SESSION_GAP_MINUTES ?= 15
REPLAY_FLUSH_EVERY ?= 1000
REPLAY_FLUSH_TIMEOUT_SECONDS ?= 30
REPLAY_FLUSH_RETRY_ATTEMPTS ?= 3
REPLAY_FLUSH_RETRY_BACKOFF_SECONDS ?= 2
REPLAY_PROGRESS_EVERY ?= 1000
REPLAY_MAX_RECORDS ?= 0
REPLAY_OUTPUT_JSONL ?=
REPLAY_REPEAT ?= 0

ifeq ($(OS),Windows_NT)
SHELL := powershell.exe
.SHELLFLAGS := -NoProfile -ExecutionPolicy Bypass -Command
DEV_SCRIPT := '$(ROOT)/scripts/dev.ps1'

help:
> & $(DEV_SCRIPT) help

infra-up:
> & $(DEV_SCRIPT) infra-up

infra-down:
> & $(DEV_SCRIPT) infra-down

create-venv:
> & $(DEV_SCRIPT) create-venv

install-generator:
> & $(DEV_SCRIPT) install-generator

install-stream:
> & $(DEV_SCRIPT) install-stream

install-ml-api:
> & $(DEV_SCRIPT) install-ml-api

install-all:
> & $(DEV_SCRIPT) install-all

run-ml-api:
> & $(DEV_SCRIPT) run-ml-api

run-generator:
> & $(DEV_SCRIPT) run-generator

run-replay:
> $$env:GENERATOR_SOURCE_DIR='$(REPLAY_INPUT)'; $$env:GENERATOR_REPLAY_TIME_SCALE='$(REPLAY_TIME_SCALE)'; $$env:GENERATOR_SESSION_GAP_MINUTES='$(REPLAY_SESSION_GAP_MINUTES)'; $$env:GENERATOR_REPLAY_FLUSH_EVERY='$(REPLAY_FLUSH_EVERY)'; $$env:GENERATOR_REPLAY_FLUSH_TIMEOUT_SECONDS='$(REPLAY_FLUSH_TIMEOUT_SECONDS)'; $$env:GENERATOR_REPLAY_FLUSH_RETRY_ATTEMPTS='$(REPLAY_FLUSH_RETRY_ATTEMPTS)'; $$env:GENERATOR_REPLAY_FLUSH_RETRY_BACKOFF_SECONDS='$(REPLAY_FLUSH_RETRY_BACKOFF_SECONDS)'; $$env:GENERATOR_REPLAY_PROGRESS_EVERY='$(REPLAY_PROGRESS_EVERY)'; $$env:GENERATOR_REPLAY_MAX_RECORDS='$(REPLAY_MAX_RECORDS)'; $$env:GENERATOR_REPLAY_OUTPUT_JSONL='$(REPLAY_OUTPUT_JSONL)'; $$env:GENERATOR_REPEAT='$(REPLAY_REPEAT)'; & $(DEV_SCRIPT) run-replay

run-stream:
> & $(DEV_SCRIPT) run-stream

start-ml-api:
> & $(DEV_SCRIPT) start-ml-api

start-generator:
> & $(DEV_SCRIPT) start-generator

start-replay:
> $$env:GENERATOR_SOURCE_DIR='$(REPLAY_INPUT)'; $$env:GENERATOR_REPLAY_TIME_SCALE='$(REPLAY_TIME_SCALE)'; $$env:GENERATOR_SESSION_GAP_MINUTES='$(REPLAY_SESSION_GAP_MINUTES)'; $$env:GENERATOR_REPLAY_FLUSH_EVERY='$(REPLAY_FLUSH_EVERY)'; $$env:GENERATOR_REPLAY_FLUSH_TIMEOUT_SECONDS='$(REPLAY_FLUSH_TIMEOUT_SECONDS)'; $$env:GENERATOR_REPLAY_FLUSH_RETRY_ATTEMPTS='$(REPLAY_FLUSH_RETRY_ATTEMPTS)'; $$env:GENERATOR_REPLAY_FLUSH_RETRY_BACKOFF_SECONDS='$(REPLAY_FLUSH_RETRY_BACKOFF_SECONDS)'; $$env:GENERATOR_REPLAY_PROGRESS_EVERY='$(REPLAY_PROGRESS_EVERY)'; $$env:GENERATOR_REPLAY_MAX_RECORDS='$(REPLAY_MAX_RECORDS)'; $$env:GENERATOR_REPLAY_OUTPUT_JSONL='$(REPLAY_OUTPUT_JSONL)'; $$env:GENERATOR_REPEAT='$(REPLAY_REPEAT)'; & $(DEV_SCRIPT) start-replay

start-stream:
> & $(DEV_SCRIPT) start-stream

start-all:
> & $(DEV_SCRIPT) start-all

stop-local:
> & $(DEV_SCRIPT) stop-local

analytics-seed:
> & $(DEV_SCRIPT) analytics-seed

analytics-query:
> & $(DEV_SCRIPT) analytics-query

validate:
> & $(DEV_SCRIPT) validate

test:
> & $(DEV_SCRIPT) test

else
.ONESHELL:
SHELL := bash
.SHELLFLAGS := -e -o pipefail -c
VENV_PYTHON := $(VENV_DIR)/bin/python

help:
> printf '%s\n' 'Targets:'
> printf '%s\n' '  infra-up         Start Kafka, ClickHouse, and Grafana in Docker'
> printf '%s\n' '  infra-down       Stop infra containers and remove volumes'
> printf '%s\n' '  create-venv      Create the local project virtual environment'
> printf '%s\n' '  install-all      Install base Python dependencies for all local app services'
> printf '%s\n' '  run-ml-api       Run the ML API in the current terminal'
> printf '%s\n' '  run-generator    Run the generator in the current terminal'
> printf '%s\n' '  run-replay       Replay access.log or REPLAY_INPUT in the current terminal'
> printf '%s\n' '  run-stream       Run the stream processor in the current terminal'
> printf '%s\n' '  start-replay     Replay access.log or REPLAY_INPUT in background'
> printf '%s\n' '  start-all        Start ML API, generator, and stream processor in background'
> printf '%s\n' '  stop-local       Stop local background app services started by Makefile'
> printf '%s\n' '  analytics-seed   Create and seed the ClickHouse table from the host'
> printf '%s\n' '  analytics-query  Run the analytics smoke queries from the host'
> printf '%s\n' '  validate         Validate contracts'
> printf '%s\n' '  test             Run bootstrap unit tests'

infra-up:
> docker-compose -f infra/docker-compose.yml --env-file '$(ENV_FILE)' up -d --remove-orphans kafka clickhouse grafana

infra-down:
> docker-compose -f infra/docker-compose.yml --env-file '$(ENV_FILE)' down -v

create-venv:
> if [ ! -x '$(VENV_PYTHON)' ]; then python3 -m venv '$(VENV_DIR)'; fi
> '$(VENV_PYTHON)' -m pip install --upgrade pip

install-generator:
> $(MAKE) create-venv
> '$(VENV_PYTHON)' -m pip install -r generator/requirements.txt

install-stream:
> $(MAKE) create-venv
> '$(VENV_PYTHON)' -m pip install -r stream-processor/requirements.txt

install-ml-api:
> $(MAKE) create-venv
> '$(VENV_PYTHON)' -m pip install -r ml-api/requirements.txt

install-all:
> $(MAKE) install-generator
> $(MAKE) install-stream
> $(MAKE) install-ml-api

run-ml-api:
> ML_API_PORT=8000 \
> ML_MODELS_DIR='$(ROOT)/ml-api/models' \
> PYTHONPATH='$(ROOT)/ml-api/src' \
> '$(VENV_PYTHON)' -u -m uvicorn ml_api.main:app --host 127.0.0.1 --port 8000

run-generator:
> KAFKA_BOOTSTRAP_SERVERS='$(KAFKA_BOOTSTRAP_SERVERS_LOCAL)' \
> KAFKA_TOPIC='$(KAFKA_TOPIC_LOCAL)' \
> PYTHONPATH='$(ROOT)/generator/src' \
> '$(VENV_PYTHON)' -u -m generator.main

run-replay:
> REPLAY_ARGS=()
> if [ -n '$(REPLAY_OUTPUT_JSONL)' ]; then REPLAY_ARGS+=(--output-jsonl '$(REPLAY_OUTPUT_JSONL)'); fi
> if [ '$(REPLAY_REPEAT)' = '1' ]; then REPLAY_ARGS+=(--repeat); fi
> KAFKA_BOOTSTRAP_SERVERS='$(KAFKA_BOOTSTRAP_SERVERS_LOCAL)' \
> KAFKA_TOPIC='$(KAFKA_TOPIC_LOCAL)' \
> GENERATOR_SOURCE_DIR='$(REPLAY_INPUT)' \
> GENERATOR_REPLAY_TIME_SCALE='$(REPLAY_TIME_SCALE)' \
> GENERATOR_SESSION_GAP_MINUTES='$(REPLAY_SESSION_GAP_MINUTES)' \
> GENERATOR_REPLAY_FLUSH_EVERY='$(REPLAY_FLUSH_EVERY)' \
> GENERATOR_REPLAY_FLUSH_TIMEOUT_SECONDS='$(REPLAY_FLUSH_TIMEOUT_SECONDS)' \
> GENERATOR_REPLAY_FLUSH_RETRY_ATTEMPTS='$(REPLAY_FLUSH_RETRY_ATTEMPTS)' \
> GENERATOR_REPLAY_FLUSH_RETRY_BACKOFF_SECONDS='$(REPLAY_FLUSH_RETRY_BACKOFF_SECONDS)' \
> GENERATOR_REPLAY_PROGRESS_EVERY='$(REPLAY_PROGRESS_EVERY)' \
> GENERATOR_REPLAY_MAX_RECORDS='$(REPLAY_MAX_RECORDS)' \
> PYTHONPATH='$(ROOT)/generator/src' \
> '$(VENV_PYTHON)' -u -m generator.replay_access_logs --input-dir '$(REPLAY_INPUT)' "$${REPLAY_ARGS[@]}"

run-stream:
> KAFKA_BOOTSTRAP_SERVERS='$(KAFKA_BOOTSTRAP_SERVERS_LOCAL)' \
> KAFKA_TOPIC='$(KAFKA_TOPIC_LOCAL)' \
> ML_API_URL='$(ML_API_URL_LOCAL)' \
> CLICKHOUSE_URL='$(CLICKHOUSE_URL_LOCAL)' \
> STREAM_FALLBACK_OUTPUT_PATH='$(ROOT)/stream-processor/output/processed_rows.mock.jsonl' \
> PYTHONPATH='$(ROOT)/stream-processor/src' \
> '$(VENV_PYTHON)' -u -m stream_processor.main

start-ml-api:
> mkdir -p '$(LOCAL_STATE_DIR)'
> nohup env \
>   ML_API_PORT=8000 \
>   ML_MODELS_DIR='$(ROOT)/ml-api/models' \
>   PYTHONPATH='$(ROOT)/ml-api/src' \
>   '$(VENV_PYTHON)' -u -m uvicorn ml_api.main:app --host 127.0.0.1 --port 8000 \
>   >'$(LOCAL_STATE_DIR)/ml-api.out.log' 2>'$(LOCAL_STATE_DIR)/ml-api.err.log' &
> echo $$! >'$(LOCAL_STATE_DIR)/ml-api.pid'
> printf 'Started ml-api (PID=%s)\n' "$$(cat '$(LOCAL_STATE_DIR)/ml-api.pid')"

start-generator:
> mkdir -p '$(LOCAL_STATE_DIR)'
> nohup env \
>   KAFKA_BOOTSTRAP_SERVERS='$(KAFKA_BOOTSTRAP_SERVERS_LOCAL)' \
>   KAFKA_TOPIC='$(KAFKA_TOPIC_LOCAL)' \
>   PYTHONPATH='$(ROOT)/generator/src' \
>   '$(VENV_PYTHON)' -u -m generator.main \
>   >'$(LOCAL_STATE_DIR)/generator.out.log' 2>'$(LOCAL_STATE_DIR)/generator.err.log' &
> echo $$! >'$(LOCAL_STATE_DIR)/generator.pid'
> printf 'Started generator (PID=%s)\n' "$$(cat '$(LOCAL_STATE_DIR)/generator.pid')"

start-replay:
> mkdir -p '$(LOCAL_STATE_DIR)'
> REPLAY_ARGS=()
> if [ -n '$(REPLAY_OUTPUT_JSONL)' ]; then REPLAY_ARGS+=(--output-jsonl '$(REPLAY_OUTPUT_JSONL)'); fi
> if [ '$(REPLAY_REPEAT)' = '1' ]; then REPLAY_ARGS+=(--repeat); fi
> nohup env \
>   KAFKA_BOOTSTRAP_SERVERS='$(KAFKA_BOOTSTRAP_SERVERS_LOCAL)' \
>   KAFKA_TOPIC='$(KAFKA_TOPIC_LOCAL)' \
>   GENERATOR_SOURCE_DIR='$(REPLAY_INPUT)' \
>   GENERATOR_REPLAY_TIME_SCALE='$(REPLAY_TIME_SCALE)' \
>   GENERATOR_SESSION_GAP_MINUTES='$(REPLAY_SESSION_GAP_MINUTES)' \
>   GENERATOR_REPLAY_FLUSH_EVERY='$(REPLAY_FLUSH_EVERY)' \
>   GENERATOR_REPLAY_FLUSH_TIMEOUT_SECONDS='$(REPLAY_FLUSH_TIMEOUT_SECONDS)' \
>   GENERATOR_REPLAY_FLUSH_RETRY_ATTEMPTS='$(REPLAY_FLUSH_RETRY_ATTEMPTS)' \
>   GENERATOR_REPLAY_FLUSH_RETRY_BACKOFF_SECONDS='$(REPLAY_FLUSH_RETRY_BACKOFF_SECONDS)' \
>   GENERATOR_REPLAY_PROGRESS_EVERY='$(REPLAY_PROGRESS_EVERY)' \
>   GENERATOR_REPLAY_MAX_RECORDS='$(REPLAY_MAX_RECORDS)' \
>   PYTHONPATH='$(ROOT)/generator/src' \
>   '$(VENV_PYTHON)' -u -m generator.replay_access_logs --input-dir '$(REPLAY_INPUT)' "$${REPLAY_ARGS[@]}" \
>   >'$(LOCAL_STATE_DIR)/replay.out.log' 2>'$(LOCAL_STATE_DIR)/replay.err.log' &
> echo $$! >'$(LOCAL_STATE_DIR)/replay.pid'
> printf 'Started replay (PID=%s)\n' "$$(cat '$(LOCAL_STATE_DIR)/replay.pid')"

start-stream:
> mkdir -p '$(LOCAL_STATE_DIR)'
> nohup env \
>   KAFKA_BOOTSTRAP_SERVERS='$(KAFKA_BOOTSTRAP_SERVERS_LOCAL)' \
>   KAFKA_TOPIC='$(KAFKA_TOPIC_LOCAL)' \
>   ML_API_URL='$(ML_API_URL_LOCAL)' \
>   CLICKHOUSE_URL='$(CLICKHOUSE_URL_LOCAL)' \
>   STREAM_FALLBACK_OUTPUT_PATH='$(ROOT)/stream-processor/output/processed_rows.mock.jsonl' \
>   PYTHONPATH='$(ROOT)/stream-processor/src' \
>   '$(VENV_PYTHON)' -u -m stream_processor.main \
>   >'$(LOCAL_STATE_DIR)/stream-processor.out.log' 2>'$(LOCAL_STATE_DIR)/stream-processor.err.log' &
> echo $$! >'$(LOCAL_STATE_DIR)/stream-processor.pid'
> printf 'Started stream-processor (PID=%s)\n' "$$(cat '$(LOCAL_STATE_DIR)/stream-processor.pid')"

start-all:
> $(MAKE) infra-up
> $(MAKE) start-ml-api
> sleep 2
> $(MAKE) start-generator
> $(MAKE) start-stream
> printf '%s\n' 'Local stack started. Logs are in $(LOCAL_STATE_DIR)'

stop-local:
> if [ -d '$(LOCAL_STATE_DIR)' ]; then
>   shopt -s nullglob
>   for pidfile in '$(LOCAL_STATE_DIR)'/*.pid; do
>     pid="$$(cat "$$pidfile")"
>     if [ -n "$$pid" ]; then
>       kill "$$pid" 2>/dev/null || true
>     fi
>     rm -f "$$pidfile"
>   done
> fi

analytics-seed:
> CLICKHOUSE_URL='$(CLICKHOUSE_URL_LOCAL)' '$(VENV_PYTHON)' analytics/scripts/ensure_seed.py

analytics-query:
> CLICKHOUSE_URL='$(CLICKHOUSE_URL_LOCAL)' '$(VENV_PYTHON)' analytics/scripts/query_smoke.py

validate:
> '$(VENV_PYTHON)' scripts/validate_contracts.py

test:
> '$(VENV_PYTHON)' -m unittest discover -s tests -p 'test_*.py' -v
endif
