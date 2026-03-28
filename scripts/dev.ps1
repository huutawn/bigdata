param(
    [Parameter(Mandatory = $true)]
    [string]$Task
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$LocalStateDir = Join-Path $Root '.local-dev'

function Invoke-InfraUp {
    docker-compose -f infra/docker-compose.yml --env-file .env up -d --remove-orphans nats clickhouse grafana
}

function Invoke-InfraDown {
    docker-compose -f infra/docker-compose.yml --env-file .env down -v
}

function Install-Requirements {
    param([string]$Path)
    python -m pip install -r $Path
}

function Start-BackgroundService {
    param(
        [string]$Name,
        [string]$Command
    )

    New-Item -ItemType Directory -Force $LocalStateDir | Out-Null
    $stdout = Join-Path $LocalStateDir "$Name.out.log"
    $stderr = Join-Path $LocalStateDir "$Name.err.log"
    $pidFile = Join-Path $LocalStateDir "$Name.pid"

    $process = Start-Process powershell -WorkingDirectory $Root -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $Command -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    $process.Id | Set-Content $pidFile
    Write-Host "Started $Name (PID=$($process.Id))"
}

function Stop-BackgroundServices {
    if (-not (Test-Path $LocalStateDir)) {
        return
    }

    Get-ChildItem $LocalStateDir -Filter '*.pid' | ForEach-Object {
        $pid = Get-Content $_.FullName
        if ($pid) {
            Stop-Process -Id ([int]$pid) -Force -ErrorAction SilentlyContinue
        }
        Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
    }
}

switch ($Task) {
    'help' {
        Write-Host 'Tasks:'
        Write-Host '  infra-up'
        Write-Host '  infra-down'
        Write-Host '  install-generator'
        Write-Host '  install-stream'
        Write-Host '  install-ml-api'
        Write-Host '  install-all'
        Write-Host '  run-ml-api'
        Write-Host '  run-generator'
        Write-Host '  run-stream'
        Write-Host '  start-ml-api'
        Write-Host '  start-generator'
        Write-Host '  start-stream'
        Write-Host '  start-all'
        Write-Host '  stop-local'
        Write-Host '  analytics-seed'
        Write-Host '  analytics-query'
        Write-Host '  validate'
        Write-Host '  test'
    }
    'infra-up' {
        Invoke-InfraUp
    }
    'infra-down' {
        Invoke-InfraDown
    }
    'install-generator' {
        Install-Requirements 'generator/requirements.txt'
    }
    'install-stream' {
        Install-Requirements 'stream-processor/requirements.txt'
    }
    'install-ml-api' {
        Install-Requirements 'ml-api/requirements.txt'
    }
    'install-all' {
        Install-Requirements 'generator/requirements.txt'
        Install-Requirements 'stream-processor/requirements.txt'
        Install-Requirements 'ml-api/requirements.txt'
    }
    'run-ml-api' {
        $env:ML_API_PORT = '8000'
        $env:ML_MODELS_DIR = "$Root/ml-api/models"
        $env:PYTHONPATH = "$Root/ml-api/src"
        python -m uvicorn ml_api.main:app --host 127.0.0.1 --port 8000
    }
    'run-generator' {
        $env:NATS_URL = 'nats://127.0.0.1:4222'
        $env:NATS_SUBJECT = 'logs.raw'
        $env:PYTHONPATH = "$Root/generator/src"
        python -m generator.main
    }
    'run-stream' {
        $env:NATS_URL = 'nats://127.0.0.1:4222'
        $env:NATS_SUBJECT = 'logs.raw'
        $env:ML_API_URL = 'http://127.0.0.1:8000'
        $env:CLICKHOUSE_URL = 'http://127.0.0.1:8123'
        $env:CLICKHOUSE_TABLE = 'processed_logs'
        $env:STREAM_FALLBACK_OUTPUT_PATH = "$Root/stream-processor/output/processed_logs.mock.jsonl"
        $env:PYTHONPATH = "$Root/stream-processor/src"
        python -m stream_processor.main
    }
    'start-ml-api' {
        Start-BackgroundService 'ml-api' "`$env:ML_API_PORT='8000'; `$env:ML_MODELS_DIR='$Root/ml-api/models'; `$env:PYTHONPATH='$Root/ml-api/src'; python -m uvicorn ml_api.main:app --host 127.0.0.1 --port 8000"
    }
    'start-generator' {
        Start-BackgroundService 'generator' "`$env:NATS_URL='nats://127.0.0.1:4222'; `$env:NATS_SUBJECT='logs.raw'; `$env:PYTHONPATH='$Root/generator/src'; python -m generator.main"
    }
    'start-stream' {
        Start-BackgroundService 'stream-processor' "`$env:NATS_URL='nats://127.0.0.1:4222'; `$env:NATS_SUBJECT='logs.raw'; `$env:ML_API_URL='http://127.0.0.1:8000'; `$env:CLICKHOUSE_URL='http://127.0.0.1:8123'; `$env:CLICKHOUSE_TABLE='processed_logs'; `$env:STREAM_FALLBACK_OUTPUT_PATH='$Root/stream-processor/output/processed_logs.mock.jsonl'; `$env:PYTHONPATH='$Root/stream-processor/src'; python -m stream_processor.main"
    }
    'start-all' {
        Invoke-InfraUp
        Start-BackgroundService 'ml-api' "`$env:ML_API_PORT='8000'; `$env:ML_MODELS_DIR='$Root/ml-api/models'; `$env:PYTHONPATH='$Root/ml-api/src'; python -m uvicorn ml_api.main:app --host 127.0.0.1 --port 8000"
        Start-Sleep -Seconds 2
        Start-BackgroundService 'generator' "`$env:NATS_URL='nats://127.0.0.1:4222'; `$env:NATS_SUBJECT='logs.raw'; `$env:PYTHONPATH='$Root/generator/src'; python -m generator.main"
        Start-BackgroundService 'stream-processor' "`$env:NATS_URL='nats://127.0.0.1:4222'; `$env:NATS_SUBJECT='logs.raw'; `$env:ML_API_URL='http://127.0.0.1:8000'; `$env:CLICKHOUSE_URL='http://127.0.0.1:8123'; `$env:CLICKHOUSE_TABLE='processed_logs'; `$env:STREAM_FALLBACK_OUTPUT_PATH='$Root/stream-processor/output/processed_logs.mock.jsonl'; `$env:PYTHONPATH='$Root/stream-processor/src'; python -m stream_processor.main"
    }
    'stop-local' {
        Stop-BackgroundServices
    }
    'analytics-seed' {
        $env:CLICKHOUSE_URL = 'http://127.0.0.1:8123'
        python analytics/scripts/ensure_seed.py
    }
    'analytics-query' {
        $env:CLICKHOUSE_URL = 'http://127.0.0.1:8123'
        python analytics/scripts/query_smoke.py
    }
    'validate' {
        python scripts/validate_contracts.py
    }
    'test' {
        python -m unittest discover -s tests -p 'test_*.py' -v
    }
    default {
        throw "Unknown task: $Task"
    }
}
