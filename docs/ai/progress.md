# Progress

Continuity notes between sessions. Update at the end of each session.

## 2026-10-21: Google-only login

Branch `feature/google-login`, plan `superpowers/plans/2026-10-21-google-login.md`.

- Google OAuth via fastapi-users, with a verified-email Google client and an existing-superuser-only callback. No new tables.
- Password login only outside prod; own logout route; 7-day session.
- sqladmin authenticates with the app cookie.
- `/auth` Google button, `/auth/callback` page.
- Caddy: `www` redirects to the apex; site addresses fixed to `{$VAR}` (the old `{env.*}` failed `caddy validate`).

Next: the owner creates the Google OAuth client (README) and sets `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` in prod.

## 2026-10-21: ArcheMarket CSV rebuild

Branch `feature/archemarket-csv` (not pushed). It implements `superpowers/plans/2026-10-21-archemarket-csv.md`, and its rulings are recorded in the plan's ledger.

- **Removed:** Discord bot, `pricetracker*` addons, ingest, prices, watchlist, profiles, registration and password-reset routes, the old item pages and price chart.
- **Frozen:** crafting and inventory (`backend/frozen`, `frontend/frozen`).
- **New:**
  - the `market` module (items, market days, listings, CSV import, read API);
  - `/market` and `/import` pages;
  - `create-superuser` CLI;
  - Playwright suite in `frontend/e2e/`;
  - CI for vitest, e2e and infra.
- **Layout:** `app/core`, `app/admin`, `app/auth`, `app/market`, with tests mirroring them. `lib/core` and `lib/market` on the frontend.
- **Frontend deps:** reverted from the broken dependabot SvelteKit 3 bump to SvelteKit 2.70.3, then patched with npm audit fixes; ECharts is 6.1.

Next: the user reviews the branch, then the roadmap items (crafting and inventory rebuild first).
