# ArcheRage Market Tracker

Charts for ArcheRage auction-house prices from the CSV files of the ArcheMarket addon (separate repo). Stack: FastAPI · SvelteKit · PostgreSQL · podman compose.

## Quick start (dev)

```bash
cp infra/.env.example infra/.env          # optional; defaults work without it
make dev-up                               # db + backend :8000 + frontend :5173
make create-superuser EMAIL=me@example.com PASSWORD='a-long-password'
make seed                                 # optional: import the sample CSVs
```

## Importing data

1. Sign in at `/auth` with the superuser account.
2. Open `/import` and drop `market.csv` and `listings.csv` from the addon folder (`Documents/Addon/archemarket/`), or use **Choose files**.
3. The summary shows, per file, how many rows were inserted, updated, skipped, and which lines had errors.

Uploading the same file again is safe: nothing is duplicated, and for each item and date the newest scan wins. The addon only appends to its CSVs, so you can archive or empty old files at any time.

## Resetting the database

- **Dev:** `make dev-reset` (drops the dev volume and starts fresh), then `make create-superuser` again.
- **Prod:** stop the stack, drop the `postgres_prod_data` volume, then start it again. Migrations run on start.

## More

`make help` lists all commands. Architecture and rules live in `docs/ai/`.
