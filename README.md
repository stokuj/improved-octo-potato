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

1. Sign in at `/auth` with the superuser account (Google in prod; the password form in dev).
2. Open `/import` and drop `market.csv` and `listings.csv` from the addon folder (`Documents/Addon/archemarket/`), or use **Choose files**. Market files are admin only.
   For your items, click **Bag** in game (ArcheBag addon; it saves the bag and the warehouse), and **Chest** → **Save** with a house chest open. Drop `inventory.csv` and `chests.csv` from `Documents/Addon/archebag/`. They show on `/items`: characters on the left, house chests on the right.
3. The summary shows, per file, how many rows were inserted, updated, skipped, and which lines had errors.

Uploading the same file again is safe: nothing is duplicated, and for each item and date the newest scan wins. The addon only appends to its CSVs, so you can archive or empty old files at any time.

## Google sign-in setup

Production signs in with Google only, and only into an account that already exists.

1. In [Google Cloud Console](https://console.cloud.google.com/), create a project and **enable the People API** (APIs & Services → Library). Without it, every sign-in fails.
2. Create an OAuth client: APIs & Services → Credentials → Create credentials → OAuth client ID → **Web application**.
3. Add the authorized redirect URIs `https://<your-domain>/auth/callback` and `http://localhost:5173/auth/callback`.
4. On the OAuth consent screen keep the publishing status **Testing** and add your Gmail as the only test user. Google then refuses every other account before it reaches the app.
5. Put the client ID and secret in the prod env as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. The prod stack does not start without them.
6. Create the account with the **primary email of that Google account**, on the prod stack (`make create-superuser` targets the dev stack):
   ```bash
   podman compose --env-file infra/.env -f infra/compose/docker-compose.prod.yml \
     exec backend uv run python -m app.auth.cli create-superuser you@gmail.com 'any-long-password'
   ```
   In prod the password is never used, so pass any throwaway value, not a real password (it stays in the shell history).

In dev the password form is shown because compose sets `PUBLIC_PASSWORD_LOGIN=true`. Running `npm run dev` outside compose needs that variable too. Google works in dev only when the two `GOOGLE_*` variables are set.

## Resetting the database

- **Dev:** `make dev-reset` (drops the dev volume and starts fresh), then `make create-superuser` again.
- **Prod:** stop the stack, drop the `postgres_prod_data` volume, then start it again. Migrations run on start.

## More

`make help` lists all commands. Architecture and rules live in `docs/ai/`.
