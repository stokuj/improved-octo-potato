# Roadmap

## Done

| Feature | Notes |
|---|---|
| ArcheMarket CSV rebuild (2026-10-21) | Manual upload of `listings.csv` and `market.csv`, idempotent import, `/market` with a 14-day chart, offers and a today-vs-7-days table. Bot, addons, ingest, prices, watchlist and profiles removed. Spec: `superpowers/specs/2026-10-21-archemarket-csv-design.md` |
| Auth | Single admin account from the `create-superuser` CLI, cookie JWT (7 days) |
| Inventory: bag view (2026-10-23) | ArcheBag `inventory.csv` on `/import`; newest and previous snapshot per user and character; `/inventory` tile grid with Codex icons. Spec: `superpowers/specs/2026-10-23-inventory-design.md` |
| Google-only login (2026-10-21) | Prod signs in with Google only; existing superusers matched by verified email; `/admin` on the same cookie. Spec: `superpowers/specs/2026-10-21-google-login-design.md` |
| Admin panel | sqladmin at `/admin`, read-only market views |
| Infra | Podman compose dev/prod/e2e, Caddy, Makefile, CI (ruff, pytest, alembic check, svelte-check, vitest, docker builds, infra checks, non-blocking e2e) |

## Planned

| Feature | Priority | Notes |
|---|---|---|
| Warehouse and house chests | high | Next storage after the bag. Warehouse is per character (`X2Bank`), house chests per account (`X2Coffer`); both readable only while open in game. Needs ArcheBag work first |
| ArcheBag `icon` column | high | ArcheBag appends `icon` (game path `Game/ui/icon/<name>.dds`). The app already accepts it; until then every tile is a grade colour |
| Player registration | medium | Google sign-in creating non-admin accounts. Inventory data is already per user |
| Rebuild crafting on the new item/price model | high | Reference code: `backend/frozen`, `frontend/frozen`. Buy price = cheapest listing `unit_price`, sell price = `daily_avg`. Bag prices come from ArcheMarket step 7c |
| Graded items | medium | ArcheMarket must first write `item_type`/`item_grade` in `listings.csv`. Then key items on `(item_type, item_grade)` only, and drop `UNIQUE(name)` |
| SvelteKit 3 migration | medium | `$lib` → `#lib`, config from `svelte.config.js` into the Vite plugin, new `$app/env`. Fixes 3 low-severity `npm audit` advisories (cookie via kit 2) |
| Verify the Moscow game day | low | Two scans around Moscow midnight (about 22:00 CET) to confirm when day 14 rolls over |
| ESLint + Prettier, Python type checker | low | Not set up yet |
| Make e2e blocking in CI | low | Once the suite has been stable for a while |
