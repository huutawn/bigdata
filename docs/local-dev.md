# Local-first development

This repository uses Docker only for shared infrastructure:
- NATS
- ClickHouse
- Grafana

Application services run directly on the host:
- `ml-api/`
- `generator/`
- `stream-processor/`

All local Python commands should run from the project virtual environment at `.venv/`.

## Prerequisites

- Python 3.12
- Docker Desktop
- PowerShell
- Optional: GNU Make

## Recommended Windows flow

Use the PowerShell task runner:

```powershell
.\scripts\dev.ps1 help
.\scripts\dev.ps1 create-venv
.\scripts\dev.ps1 install-all
.\scripts\dev.ps1 infra-up
.\scripts\dev.ps1 start-all
```

Logs are written to `.local-dev/`.

Stop local app services with:

```powershell
.\scripts\dev.ps1 stop-local
.\scripts\dev.ps1 infra-down
```

## Optional manual activation

```powershell
.\.venv\Scripts\Activate.ps1
```

## Optional Make targets

If GNU Make is installed:

```powershell
make help
make create-venv
make install-all
make infra-up
make start-all
```

## Run a single service in the foreground

```powershell
.\scripts\dev.ps1 run-ml-api
.\scripts\dev.ps1 run-generator
.\scripts\dev.ps1 run-stream
```

## Analytics helpers

```powershell
.\scripts\dev.ps1 analytics-seed
.\scripts\dev.ps1 analytics-query
```

## Validation

```powershell
.\scripts\dev.ps1 validate
.\scripts\dev.ps1 test
```

## Local URLs

When services run on the host they use:
- NATS: `nats://127.0.0.1:4222`
- ML API: `http://127.0.0.1:8000`
- ClickHouse: `http://127.0.0.1:8123`
- Grafana: `http://127.0.0.1:3000`
