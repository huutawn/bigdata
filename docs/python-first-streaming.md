# Python-First Streaming on Windows

The default Windows workflow uses Python window builders for `stream-processor`.

## Default behavior

- `STREAM_USE_SPARK_WINDOWS=0` in `.env.example`
- `StreamSettings` defaults to Python windowing when the flag is not set
- `install-all` does not install `pyspark`

This keeps the local setup lighter and avoids Spark startup issues on Windows unless you explicitly opt in.

## Recommended local flow

```powershell
.\scripts\dev.ps1 create-venv
.\scripts\dev.ps1 install-all
.\scripts\dev.ps1 infra-up
.\scripts\dev.ps1 start-all
```

## Optional Spark opt-in

Install the Spark dependency only when you want to experiment with the Spark-backed window builders:

```powershell
.\scripts\dev.ps1 install-stream-spark
$env:STREAM_USE_SPARK_WINDOWS='1'
.\scripts\dev.ps1 run-stream
```

GNU Make users can do the same:

```powershell
make install-stream-spark
$env:STREAM_USE_SPARK_WINDOWS='1'
make run-stream
```

## Notes

- NATS, ClickHouse, and Grafana are still the shared local infrastructure.
- `generator` and `ml-api` are unchanged.
- Spark remains available as an opt-in path for future experiments, but it is no longer part of the default Windows setup.