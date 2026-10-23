# Google-only login — design

Status: draft, 2026-10-21. Branch `feature/google-login` (from `main` after PR #15).

## Intent

The app has one account: the owner, a superuser who imports ArcheMarket CSVs. Today they sign in with an email and password, and the session lasts one hour. The owner wants to sign in with Google instead. That means no password to keep or leak in production, and Google's 2-step verification protects the account.

Success: in production the only way in is "Sign in with Google" with the owner's Google account. Any other Google account is refused. Sign-in is one click, and the owner stays signed in for a week.

## Goals

- Google sign-in (OAuth 2.0 / OpenID Connect) for the existing superuser account.
- No password login in production.
- `/admin` (sqladmin) uses the same login and cookie, with no separate password form.
- The session lasts 7 days instead of 1 hour.
- Dev and e2e still work without Google, using the current password login.

## Non-goals

- More users, self-registration, roles. Accounts still come only from `create-superuser`.
- Other providers (GitHub, Microsoft…).
- Server-side token revocation. Logout only clears the cookie, as today.
- Storing or using Google access tokens. We only need the verified email, once, at login.

## Anti-goals (failure even if it "works")

- A Google account that is not the owner's can sign in, or creates a user row.
- Production still accepts a password at some route, including the fastapi-users `/auth/login` that the throttled route shadows today.
- e2e or local dev now needs a real Google account or network access to Google.

## Decided (by the owner, in chat)

- Google only, inside the app. No proxy gate (Cloudflare Access) and no hosted provider (Auth0/Clerk).
- Only accounts that already exist may sign in. They are created by `python -m app.auth.cli create-superuser EMAIL PASSWORD`.
- Password login is off in production and stays on for dev and e2e.
- `/admin` reads the same auth cookie.
- Session length: 7 days.

## How it works

### Flow

1. On `/auth` the frontend calls `GET /api/auth/google/authorize` with `credentials: 'include'`. The backend returns `{authorization_url}` and sets the fastapi-users CSRF cookie (`fastapiusersoauthcsrf`). The browser goes to `authorization_url`.
2. Google sends the browser back to the frontend at `{FRONTEND_URL}/auth/callback?code=…&state=…`.
3. That page calls `GET /api/auth/google/callback?code=…&state=…` with `credentials: 'include'`. The backend checks the state and CSRF cookie, exchanges the code, reads the Google email and applies the account rules below. On success it sets the usual `fastapiusersauth` cookie (HTTP 204).
4. The page runs `checkMe` and goes to `/market`. On failure it shows the backend's error and a link back to `/auth`.

### Backend

- **Router.** Add `httpx-oauth` and mount `fastapi_users.get_oauth_router(GoogleOAuth2(client_id, client_secret), auth_backend, state_secret=settings.auth_secret, redirect_url=f"{settings.frontend_url}/auth/callback", csrf_token_cookie_secure=settings.cookie_secure)` at `/api/auth/google`.
- **Account rules.** Override `UserManager.oauth_callback`:
  - look the user up by `account_email` only;
  - if there is no such user, or the user is not active, or not a superuser, raise `HTTPException(400, ErrorCode.LOGIN_BAD_CREDENTIALS)`;
  - otherwise return the user;
  - never create users and never store OAuth accounts or tokens.
  - **My call:** this means no `oauth_account` table, no migration and no Google tokens in the DB. The email is the link, and the account allowlist is the users table itself.
- **Verified email only.**
  - httpx-oauth's `GoogleOAuth2.get_id_email` reads the People API and returns the primary address without checking `metadata.verified`.
  - The app therefore uses its own small subclass (in `app/auth/oauth.py`) whose `get_id_email` returns the primary address **only if it is verified**, and `None` otherwise. On `None` the library already answers 400 `OAUTH_NOT_AVAILABLE_EMAIL`.
  - `GetIdEmailError` (for example, the People API is disabled) maps to 400 instead of the 500 the router would give today.
  - Check this behaviour against the httpx-oauth version that `uv add` pins.
- **Password login.** The throttled `/auth/login` and the fastapi-users login route are mounted only when `settings.environment != "prod"`. Logout (`POST /api/auth/logout`) stays in every environment. `get_auth_router` always bundles login with logout, so in prod we write a small logout route of our own.
- **Settings.** New settings `google_client_id`, `google_client_secret` and `frontend_url` (default `http://localhost:5173`).
  - The Google router is mounted only when both Google values are set.
  - In prod both Google values are required: the validator fails startup without them, just like the secret checks.
- **Session.** `cookie_max_age` and the JWT `lifetime_seconds` are both 7 days (604800).
- **Admin.**
  - `AdminAuth.authenticate` reads the `fastapiusersauth` cookie and validates it with `get_jwt_strategy().read_token(token, user_manager)`. It requires an active superuser and otherwise returns `RedirectResponse(f"{settings.frontend_url}/auth")`.
  - `login()` always returns False, because the sqladmin form is no longer a way in.
  - `logout()` deletes the auth cookie and redirects to `/auth`.
  - The admin session middleware and `ADMIN_SESSION_SECRET` stay as they are, since sqladmin requires a secret.
- **CLI.** `create-superuser EMAIL PASSWORD` is unchanged. In prod the password is unused but harmless.

### Frontend

- **`/auth`.**
  - A "Sign in with Google" button (`btn`, DaisyUI) calls the authorize endpoint and redirects.
  - The email/password form is shown only when `PUBLIC_PASSWORD_LOGIN === 'true'`. The flag is read from `$env/dynamic/public`, so the build and `svelte-check` don't fail when it is unset (`$env/static/public` exports only defined variables). Dev and e2e compose set it, and prod leaves it unset.
  - **My call:** an env flag, because the e2e stack is a production build, so `$app/environment.dev` cannot tell the two apart.
- **`/auth/callback`.** A new route that runs the step-3 call once on mount and handles success and error as above.
- **`auth.svelte.ts`.** Add `startGoogleLogin()` and `finishGoogleLogin(user, search)` next to `login`/`logout`, in the same style.
- **CSP.** The frontend never talks to Google from script, only by navigation, so `connect-src` does not change.

### Infra

- `infra/.env.example`: add `GOOGLE_CLIENT_ID=`, `GOOGLE_CLIENT_SECRET=`, `FRONTEND_URL=` with a one-line comment each. Per the repo rules this is the only `.env*` file the builder may touch.
- Prod compose passes them to the backend, with `FRONTEND_URL=https://${APP_DOMAIN}`.
- Dev and e2e compose set `PUBLIC_PASSWORD_LOGIN=true` as a runtime env var for the frontend container.
- **`www` domain.** The auth cookie is host-only on the apex domain, so Caddy redirects the `www` domain to the apex. Otherwise `/admin` opened on `www` would never see the cookie.
- README gets a short "Google sign-in setup" section for the owner:
  1. In Google Cloud Console, create a project and **enable the People API**.
  2. Create an OAuth client of type "Web application".
  3. Add the authorized redirect URIs `https://<domain>/auth/callback` and `http://localhost:5173/auth/callback`.
  4. Set the consent screen to *Testing* and add the owner's Gmail as the only test user. Google then refuses everyone else before they reach the app.
  5. Put the client ID and secret in the prod env.
  6. Run `create-superuser` with the **primary email of that Google account**.

## Tests

**Backend.** Real Postgres, as everywhere. Google is faked by monkeypatching `GoogleOAuth2.get_access_token` and `get_id_email` on the client instance. Each test gets a real state and CSRF cookie by calling `/authorize` first.
- A known active superuser gets 204 and the auth cookie, and `/api/users/me` works with it.
- An unknown email gets 400 and no new user row.
- A user who is not a superuser gets 400, and so does an inactive superuser.
- A missing or mismatched CSRF cookie gets 400 (the library does this; one test pins it).
- In prod settings, `POST /api/auth/login` returns 404 or 405, not 400 or 204, and logout still works. The builder decides how to build the app with prod settings in a test, for example a router factory taking `Settings`.
- Admin:
  - with the auth cookie of a superuser, `/admin/` returns 200;
  - without a cookie it redirects to `{frontend_url}/auth`;
  - with a non-superuser's cookie it redirects as well.
- The cookie and JWT lifetime is 604800.
- The settings validator rejects prod without the Google settings. `tests/core/test_settings_validator.py` gets the new fields.
- Google `get_id_email`:
  - an unverified primary email yields `None`, and the callback answers 400;
  - a `GetIdEmailError` yields 400.
- The existing `tests/admin/test_auth.py` redirect assertion changes from `/admin` to `{frontend_url}/auth`.

**Frontend.**
- vitest for the new auth helpers: correct URLs, `credentials: 'include'`, and the error path.
- The existing e2e suite keeps passing unchanged, since the password form is on in e2e.
- No e2e test talks to Google.

## Left to the builder

- Exact file split inside `app/auth/` (e.g. `oauth.py` for the client, with a one-line reason comment, per the module rules).
- Error copy on `/auth/callback`.
- Whether the Google button shows when the Google router is not mounted (dev without credentials). A 404 from authorize can just show an error.
- Updating `docs/ai/architecture.md`, `constitution.md` (the "accounts only from CLI" rule stays, and prod gets "no password login") and `CLAUDE.md`.
