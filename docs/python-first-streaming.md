# Streaming on Windows

The current Windows workflow keeps the same local-first model as the rest of the repo:

- shared infrastructure runs in Docker
- application services run directly on the host
- `stream-processor` tries Spark-backed window builders first
- if Spark is unavailable or fails at runtime, `stream-processor` falls back to the pure-Python window builders

## Recommended local flow

```powershell
.\scripts\dev.ps1 create-venv
.\scripts\dev.ps1 install-all
.\scripts\dev.ps1 infra-up
.\scripts\dev.ps1 start-all
```

## Notes

- Kafka, ClickHouse, and Grafana are still the shared local infrastructure.
- `generator` publishes to Kafka topic `logs.raw`.
- `ml-api` is unchanged from the caller perspective: it still receives task-specific feature payloads over HTTP.
- No separate `install-stream-spark` workflow is needed in the current repo; `stream-processor/requirements.txt` already includes `pyspark`.
