param(
    [Parameter(Mandatory = $true)]
    [string]$Task
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$LocalStateDir = Join-Path $Root '.local-dev'
$VenvDir = Join-Path $Root '.venv'
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
$EnvFile = if (Test-Path (Join-Path $Root '.env')) {
    Join-Path $Root '.env'
} else {
    Join-Path $Root '.env.example'
}

function Ensure-Venv {
    if (-not (Test-Path $VenvPython)) {
        python -m venv $VenvDir
    }
}

function Get-Python {
    if (-not (Test-Path $VenvPython)) {
        throw "Virtual environment not found. Run '.\\scripts\\dev.ps1 install-all' first."
    }
    return $VenvPython
}

function Invoke-InfraUp {
    docker-compose -f infra/docker-compose.yml --env-file $EnvFile up -d --remove-orphans nats clickhouse grafana
}

function Invoke-InfraDown {
    docker-compose -f infra/docker-compose.yml --env-file $EnvFile down -v
}

function Install-Requirements {
    param([string]$Path)
    Ensure-Venv
    $python = Get-Python
    & $python -m pip install --upgrade pip
    & $python -m pip install -r $Path
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
        $processId = Get-Content $_.FullName
        if ($processId) {
            Stop-Process -Id ([int]$processId) -Force -ErrorAction SilentlyContinue
        }
        Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
    }
}

switch ($Task) {
    'help' {
        Write-Host 'Tasks:'
        Write-Host '  infra-up'
        Write-Host '  infra-down'
        Write-Host '  create-venv'
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
    'create-venv' {
        Ensure-Venv
        Write-Host "Virtual environment is ready at $VenvDir"
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
        $python = Get-Python
        $env:ML_API_PORT = '8000'
        $env:ML_MODELS_DIR = "$Root/ml-api/models"
        $env:PYTHONPATH = "$Root/ml-api/src"
        & $python -u -m uvicorn ml_api.main:app --host 127.0.0.1 --port 8000
    }
    'run-generator' {
        $python = Get-Python
        $env:NATS_URL = 'nats://127.0.0.1:4222'
        $env:NATS_SUBJECT = 'logs.raw'
        $env:PYTHONPATH = "$Root/generator/src"
        & $python -u -m generator.main
    }
    'run-stream' {
        $python = Get-Python
        $env:NATS_URL = 'nats://127.0.0.1:4222'
        $env:NATS_SUBJECT = 'logs.raw'
        $env:ML_API_URL = 'http://127.0.0.1:8000'
        $env:CLICKHOUSE_URL = 'http://127.0.0.1:8123'
        $env:STREAM_FALLBACK_OUTPUT_PATH = "$Root/stream-processor/output/processed_rows.mock.jsonl"
        $env:PYTHONPATH = "$Root/stream-processor/src"
        & $python -u -m stream_processor.main
    }
    'start-ml-api' {
        $python = Get-Python
        Start-BackgroundService 'ml-api' "`$env:ML_API_PORT='8000'; `$env:ML_MODELS_DIR='$Root/ml-api/models'; `$env:PYTHONPATH='$Root/ml-api/src'; & '$python' -u -m uvicorn ml_api.main:app --host 127.0.0.1 --port 8000"
    }
    'start-generator' {
        $python = Get-Python
        Start-BackgroundService 'generator' "`$env:NATS_URL='nats://127.0.0.1:4222'; `$env:NATS_SUBJECT='logs.raw'; `$env:PYTHONPATH='$Root/generator/src'; & '$python' -u -m generator.main"
    }
    'start-stream' {
        $python = Get-Python
        Start-BackgroundService 'stream-processor' "`$env:NATS_URL='nats://127.0.0.1:4222'; `$env:NATS_SUBJECT='logs.raw'; `$env:ML_API_URL='http://127.0.0.1:8000'; `$env:CLICKHOUSE_URL='http://127.0.0.1:8123'; `$env:STREAM_FALLBACK_OUTPUT_PATH='$Root/stream-processor/output/processed_rows.mock.jsonl'; `$env:PYTHONPATH='$Root/stream-processor/src'; & '$python' -u -m stream_processor.main"
    }
    'start-all' {
        Invoke-InfraUp
        $python = Get-Python
        Start-BackgroundService 'ml-api' "`$env:ML_API_PORT='8000'; `$env:ML_MODELS_DIR='$Root/ml-api/models'; `$env:PYTHONPATH='$Root/ml-api/src'; & '$python' -u -m uvicorn ml_api.main:app --host 127.0.0.1 --port 8000"
        Start-Sleep -Seconds 2
        Start-BackgroundService 'generator' "`$env:NATS_URL='nats://127.0.0.1:4222'; `$env:NATS_SUBJECT='logs.raw'; `$env:PYTHONPATH='$Root/generator/src'; & '$python' -u -m generator.main"
        Start-BackgroundService 'stream-processor' "`$env:NATS_URL='nats://127.0.0.1:4222'; `$env:NATS_SUBJECT='logs.raw'; `$env:ML_API_URL='http://127.0.0.1:8000'; `$env:CLICKHOUSE_URL='http://127.0.0.1:8123'; `$env:STREAM_FALLBACK_OUTPUT_PATH='$Root/stream-processor/output/processed_rows.mock.jsonl'; `$env:PYTHONPATH='$Root/stream-processor/src'; & '$python' -u -m stream_processor.main"
    }
    'stop-local' {
        Stop-BackgroundServices
    }
    'analytics-seed' {
        $python = Get-Python
        $env:CLICKHOUSE_URL = 'http://127.0.0.1:8123'
        & $python analytics/scripts/ensure_seed.py
    }
    'analytics-query' {
        $python = Get-Python
        $env:CLICKHOUSE_URL = 'http://127.0.0.1:8123'
        & $python analytics/scripts/query_smoke.py
    }
    'validate' {
        $python = Get-Python
        & $python scripts/validate_contracts.py
    }
    'test' {
        $python = Get-Python
        & $python -m unittest discover -s tests -p 'test_*.py' -v
    }
    default {
        throw "Unknown task: $Task"
    }
}
