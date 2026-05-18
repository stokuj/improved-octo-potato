# Watcher

Tails JSONL file produced by the in-game addon and POSTs batches to the project's `/api/ingest/prices`.

## Run on Windows

```powershell
cd watcher
uv sync
copy .env.example .env  # then edit
uv run python -m watcher.main
```

## Config (`.env`)

```
WATCHER_JSONL_PATH=C:\ArcheRage\Documents\Addon\pricetracker\prices.jsonl
WATCHER_API_URL=https://your-domain.com/api/ingest/prices
WATCHER_BATCH_SIZE=100
WATCHER_POLL_INTERVAL_SECONDS=2.0
```

## Tests

```bash
uv run pytest -v
```
