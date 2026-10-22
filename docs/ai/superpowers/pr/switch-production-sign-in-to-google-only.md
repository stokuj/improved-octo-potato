---
title: Switch production sign-in to Google only
issue: none
verdict: ready
created: 2026-10-22
---

# Switch production sign-in to Google only

## What

Production sign-in is now "Continue with Google". It works only for an account that already exists: an active superuser created by the `create-superuser` CLI, matched by the Google account's **verified** primary email.

- The password route `POST /api/auth/login` is mounted only outside prod, so dev and e2e keep the form.
- `/admin` (sqladmin) now uses the same auth cookie instead of its own password form.
- Sessions last 7 days instead of 1 hour.

The change adds no new tables and stores no Google tokens.

## Why

The app has one user, the owner, who imports CSVs. A Google sign-in removes the production password and puts the account behind Google's 2-step verification. Spec: `docs/ai/superpowers/specs/2026-10-21-google-login-design.md`.

No linked issue.

## How to test

1. Start a test database: `docker run -d --rm --name pg-test -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=app_test -p 5434:5432 postgres:16-alpine`.
2. Run `cd backend && TEST_PG_HOSTPORT=localhost:5434 uv run pytest -q`. Expected: `96 passed`. Coverage by file:
   - `tests/auth/test_oauth.py`: the Google flow with a faked Google. Covers an existing superuser, email case, unknown, non-superuser, inactive and unverified accounts, a People API failure, and a missing CSRF cookie.
   - `tests/auth/test_router.py`: no password login in prod, and logout works in prod.
   - `tests/admin/test_auth.py`: `/admin` accepts the cookie, redirects to `/auth` otherwise, and the sqladmin password form is not a way in.
3. Run `cd frontend && npm test && npm run check`. Expected: 43 tests pass, 0 svelte-check errors.
4. Run `env -u PUBLIC_PASSWORD_LOGIN npm run build`. Expected: the build succeeds with the flag unset.
5. Run e2e: `make e2e-up && make e2e-migrate && make e2e-seed && make e2e-test`. Expected: 10/10, using the password form; no test talks to Google.
6. Optional, real Google: follow the README section "Google sign-in setup", set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`, run `make dev-up`, and click "Continue with Google" on `http://localhost:5173/auth`.

## Risks

- **Prod does not start until Google is configured.** Compose and the settings validator both require `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. Create the OAuth client before deploying, per the README.
- **Owner lockout if the emails differ.** The superuser's email must equal the Google account's primary email, which also has to be verified by Google. Re-run `create-superuser` with that email on the prod stack.
- **People API.** It must be enabled in the Google Cloud project. If it isn't, every sign-in gets 400 "Google did not return a verified email", and the backend log shows Google's reason.
- **Caddyfile change.**
  - The site addresses used `{env.APP_DOMAIN}`, which Caddy does not expand there, so `caddy validate` failed on `main`. They now use `{$APP_DOMAIN}`.
  - `www` now redirects to the apex domain, because the auth cookie is host-only.
  - The `/admin` IP allowlist line still uses a runtime `{env.ADMIN_ALLOWED_IPS}` placeholder. It validates, but was not checked against the real prod env.
- **Sessions are 7 days, with no server-side revocation.** Logout clears the cookie, as before.

## Rollback

Revert this PR. There are no migrations and no data changes. After the revert, prod needs password login again: set a password with `create-superuser`. The Google env vars become unused.

## Contract impact

- **API:**
  - New `GET /api/auth/google/authorize` and `GET /api/auth/google/callback`.
  - `POST /api/auth/login` is gone in prod.
  - `POST /api/auth/logout` is unchanged: 204, clears the cookie.
- **Config:**
  - New backend env vars `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` (required in prod), and `FRONTEND_URL` (default `http://localhost:5173`; prod uses `https://${APP_DOMAIN}`).
  - New frontend runtime env `PUBLIC_PASSWORD_LOGIN=true`, set in dev and e2e compose.
- **Session:** the auth cookie and JWT lifetime go from 1 h to 7 days.
- **Admin:** `/admin` signs in through the app's `/auth`; the sqladmin login form no longer accepts passwords.
