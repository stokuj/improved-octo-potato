# Google-only Login Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** In production you sign in only with Google, and only into an account that already exists. Dev and e2e keep the password login. `/admin` uses the same cookie, and a session lasts 7 days.

**Architecture:**
- The fastapi-users OAuth router runs with our `VerifiedGoogleOAuth2` client, which accepts only a verified primary email.
- `UserManager.oauth_callback` only looks the user up by email; it never creates a user and never stores tokens.
- The password login route is mounted only outside prod, and logout is our own route in every environment.
- sqladmin validates the `fastapiusersauth` cookie.
- The frontend runs the Google flow through `/auth` and a new `/auth/callback`.

**Tech Stack:** FastAPI, fastapi-users 15.0.5, httpx-oauth 0.17.x, sqladmin 0.27, SvelteKit 2.70 (Svelte 5), vitest, Playwright.

**Spec:** `docs/ai/superpowers/specs/2026-10-21-google-login-design.md`

## Global Constraints

- Branch `feature/google-login`. Never push or merge without the user's request. Commits follow `type(scope): description` and end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Never modify `.env*` files except `infra/.env.example`.
- Session length is `604800` s, used for both the cookie max-age and the JWT lifetime.
- No new DB tables, no migration, no Google tokens stored anywhere.
- Google sign-in only ever matches an existing user that is active and a superuser, by email (case-insensitive, as `get_by_email` already does).
- The frontend stays on SvelteKit 2: no dependabot majors.
- `PUBLIC_PASSWORD_LOGIN` is read from `$env/dynamic/public`, never from `$env/static/public`.
- Backend tests need Postgres. Locally: `docker run -d --rm --name pg-test -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=app_test -p 5434:5432 postgres:16-alpine`, then `TEST_PG_HOSTPORT=localhost:5434 uv run pytest` (from `backend/`).
- Comments, docs and copy are in English.

## Review Focus

1. **Reloaded `/auth/callback`.** The code is reused, Google answers `invalid_grant`, and httpx-oauth returns 500. The user should see the error and a link back, not a blank page or a spinner. Pinned in Task 5: `finishGoogleLogin` returns a message on 500.
2. **Email case differs** between Google and the CLI account (`Owner@Example.com` vs `owner@example.com`). Login should still work. Pinned in Task 2: `test_google_login_email_case_insensitive`.
3. **Garbage or expired `fastapiusersauth` cookie on `/admin`.** It should redirect to `/auth`, not give a 500. Pinned in Task 4: `test_admin_garbage_cookie_redirects`.
4. **`PUBLIC_PASSWORD_LOGIN` unset** (prod, CI, plain local). `npm run check` and `npm run build` must still pass. Pinned in Task 5, Step 6.
5. **People API disabled**, so the profile call fails. The user should get a 400 with a readable message, not a 500. Pinned in Task 2: `test_google_profile_error_gives_400`.

---

### Task 1: Settings and 7-day session

**Files:**
- Modify: `backend/pyproject.toml` and `backend/uv.lock` (via `uv add`).
- Modify: `backend/app/core/settings.py`, `backend/app/auth/backend.py`.
- Modify: `backend/tests/conftest.py` (env block at the top).
- Test: `backend/tests/core/test_settings_validator.py`, `backend/tests/auth/test_backend.py` (new).

**Interfaces:**
- Produces: `settings.google_client_id: str = ""`, `settings.google_client_secret: str = ""`, `settings.frontend_url: str = "http://localhost:5173"`.
- Produces: `SESSION_SECONDS = 604800` in `app/auth/backend.py`.

- [ ] **Step 1: Add the dependency**

  Run `cd backend && uv add "httpx-oauth>=0.17,<0.18"`.

  Expected: `uv.lock` updated, and `uv run python -c "import httpx_oauth"` exits 0.

- [ ] **Step 2: Write the failing tests**

  Test env setup:
  - In `conftest.py`, next to `AUTH_SECRET`, set `os.environ["GOOGLE_CLIENT_ID"] = "test-google-client-id"` and `os.environ["GOOGLE_CLIENT_SECRET"] = "test-google-client-secret"`.
  - In `test_settings_validator.py`, add `"GOOGLE_CLIENT_ID"`, `"GOOGLE_CLIENT_SECRET"` and `"FRONTEND_URL"` to `_SECRET_ENV_KEYS`.

  ```python
  _PROD_SECRETS = dict(
      auth_secret="a" * 40, admin_session_secret="b" * 40,
      reset_token_secret="c" * 40, verification_token_secret="d" * 40,
  )

  def test_prod_requires_google_settings(clean_env):
      from app.core.settings import Settings
      with pytest.raises(ValidationError) as exc:
          Settings(environment="prod", **_PROD_SECRETS)
      assert "google" in str(exc.value).lower()

  def test_prod_accepts_google_settings(clean_env):
      from app.core.settings import Settings
      s = Settings(environment="prod", google_client_id="id", google_client_secret="secret", **_PROD_SECRETS)
      assert s.frontend_url == "http://localhost:5173"
  ```

  In `tests/auth/test_backend.py`:

  ```python
  def test_session_lasts_seven_days():
      from app.auth.backend import SESSION_SECONDS, cookie_transport, get_jwt_strategy
      assert SESSION_SECONDS == 604800
      assert cookie_transport.cookie_max_age == 604800
      assert get_jwt_strategy().lifetime_seconds == 604800
  ```

- [ ] **Step 3: Run the tests and watch them fail**

  Run `TEST_PG_HOSTPORT=localhost:5434 uv run pytest tests/core/test_settings_validator.py tests/auth/test_backend.py -v`.

  Expected: 3 FAIL. The prod test raises no Google error, and `SESSION_SECONDS` cannot be imported.

- [ ] **Step 4: Implement**

  - Add the three settings.
  - In `_check_secrets`, when `environment == "prod"` and either Google value is empty, raise `ValueError("google_client_id and google_client_secret are required in prod")`.
  - In `backend.py`, define `SESSION_SECONDS = 604800` and use it for `cookie_max_age` and `lifetime_seconds`.

- [ ] **Step 5: Run the tests and watch them pass**

  Run the same command, then the full suite: `TEST_PG_HOSTPORT=localhost:5434 uv run pytest -q`.

  Expected: all pass.

- [ ] **Step 6: Commit**

  `feat(auth): Google settings and 7-day session`

---

### Task 2: Google OAuth router with existing-account-only callback

**Files:**
- Create: `backend/app/auth/oauth.py`. Its first line: `# Google OAuth client: verified primary email only.`
- Modify: `backend/app/auth/manager.py`, `backend/app/auth/router.py`.
- Test: `backend/tests/auth/test_oauth.py` (new).

**Interfaces:**
- Consumes: the Task 1 settings.
- Produces:
  - `class VerifiedGoogleOAuth2(GoogleOAuth2)` with `async get_id_email(self, token: str) -> tuple[str, str | None]`;
  - `google_client: VerifiedGoogleOAuth2 | None`, which is None when either Google setting is empty;
  - routes `GET /api/auth/google/authorize` and `GET /api/auth/google/callback`.

- [ ] **Step 1: Write the failing tests**

  Helpers, inside the test file:
  - `fake_google(monkeypatch, *, email: str, verified: bool = True, profile_error: bool = False)`:
    - patches `google_client.get_access_token` with an async function returning `OAuth2Token({"access_token": "t", "expires_in": 3600})`;
    - patches `google_client.get_profile` to return `{"resourceName": "people/1", "emailAddresses": [{"value": email, "metadata": {"primary": True, "verified": verified}}]}`;
    - with `profile_error=True`, `get_profile` raises `GetProfileError(response=httpx.Response(403))` instead.
  - `google_login(c) -> httpx.Response`:
    - calls `GET /api/auth/google/authorize` and asserts 200;
    - takes `state` from the `authorization_url` query string (`parse_qs`);
    - then returns `GET /api/auth/google/callback?code=x&state=<state>` on the same client, so the CSRF cookie goes with it.

  Tests:
  - `test_authorize_returns_google_url`: `authorization_url` starts with `https://accounts.google.com/` and contains `redirect_uri=http%3A%2F%2Flocalhost%3A5173%2Fauth%2Fcallback`. The response sets the `fastapiusersoauthcsrf` cookie.
  - `test_google_login_existing_superuser`: with `make_user(superuser=True)` and `fake_google(email=user.email)`, the response is 204 and sets `fastapiusersauth`. After it, `GET /api/users/me` returns 200 with that email.
  - `test_google_login_email_case_insensitive`: the user email is `Mixed-<uuid>@Example.com` and Google returns it lowercased. Expect 204.
  - `test_google_login_unknown_email_refused`: Google returns `nobody-<uuid>@example.com`. Expect 400 with `detail == "LOGIN_BAD_CREDENTIALS"`, and no `User` row with that email.
  - `test_google_login_non_superuser_refused`: `make_user(superuser=False)`. Expect 400 `LOGIN_BAD_CREDENTIALS`.
  - `test_google_login_inactive_refused`: a superuser with `is_active=False`, set via `session`. Expect 400 `LOGIN_BAD_CREDENTIALS`.
  - `test_google_unverified_email_refused`: `verified=False`. Expect 400 `OAUTH_NOT_AVAILABLE_EMAIL`.
  - `test_google_profile_error_gives_400`: `profile_error=True`. Expect 400 `OAUTH_NOT_AVAILABLE_EMAIL`.
  - `test_google_callback_without_csrf_cookie_refused`: call authorize on one client, then the callback on a fresh client. Expect 400 `OAUTH_INVALID_STATE`.

- [ ] **Step 2: Run the tests and watch them fail**

  Run `TEST_PG_HOSTPORT=localhost:5434 uv run pytest tests/auth/test_oauth.py -v`.

  Expected: an ImportError on `app.auth.oauth`, or 404s.

- [ ] **Step 3: Implement**

  - **`oauth.py`.** `get_id_email`:
    - calls `self.get_profile(token)`;
    - on `GetProfileError`, logs a warning with the response status and returns `("", None)`;
    - picks the address with `metadata.primary`;
    - returns `(profile["resourceName"], value if metadata.get("verified") else None)`.

    The module then sets `google_client = VerifiedGoogleOAuth2(id, secret) if id and secret else None`.
  - **`manager.py`.** Override `oauth_callback`, keeping the library signature.
    - It calls `self.get_by_email(account_email)`.
    - On `UserNotExists`, or a user who is not active or not a superuser, it raises `HTTPException(400, detail=ErrorCode.LOGIN_BAD_CREDENTIALS)`.
    - Otherwise it returns the user.
    - It never creates users or touches OAuth accounts.
  - **`router.py`.** When `google_client` is set, include the OAuth router under prefix `/auth/google`, tag `auth`, built with:
    ```python
    fastapi_users.get_oauth_router(
        google_client,
        auth_backend,
        settings.auth_secret,
        redirect_url=f"{settings.frontend_url}/auth/callback",
        csrf_token_cookie_secure=settings.cookie_secure,
    )
    ```

- [ ] **Step 4: Run the tests and watch them pass**

  Run the file, then the full suite.

  Expected: all pass.

- [ ] **Step 5: Commit**

  `feat(auth): Google sign-in for existing superusers`

---

### Task 3: Password login outside prod only, own logout

**Files:**
- Modify: `backend/app/auth/router.py`.
- Test: `backend/tests/auth/test_router.py`.

**Interfaces:**
- Produces:
  - `build_router(*, password_login: bool) -> APIRouter` in `app/auth/router.py`;
  - module-level `router = build_router(password_login=settings.environment != "prod")`;
  - `POST /api/auth/logout`, which answers 204 and clears the cookie.
- The fastapi-users `get_auth_router` is no longer included anywhere.

- [ ] **Step 1: Write the failing tests**

  Helper `prod_like_client()`: a fresh `FastAPI()` with `app.state.limiter = limiter` and `include_router(build_router(password_login=False), prefix="/api")`, wrapped in an `AsyncClient(ASGITransport)`.

  - `test_prod_has_no_password_login`: `POST /api/auth/login` with form data returns 404 or 405.
  - `test_prod_logout_works`:
    - get a cookie by logging in through the normal `client` with `make_user` and `login`;
    - copy the `fastapiusersauth` cookie into the prod-like client;
    - `POST /api/auth/logout` returns 204, and the `set-cookie` header contains `fastapiusersauth=""` or `Max-Age=0`.
  - `test_dev_logout_works`: the same with the normal `client`, then `GET /api/users/me` returns 401.
  - `test_only_one_login_route`: in `app.main.app.routes`, exactly one route has path `/api/auth/login`.

- [ ] **Step 2: Run the tests and watch them fail**

  Run `TEST_PG_HOSTPORT=localhost:5434 uv run pytest tests/auth/test_router.py -v`.

  Expected:
  - `build_router` is missing, so ImportError;
  - `test_only_one_login_route` fails with 2 routes.

- [ ] **Step 3: Implement**

  - Move today's router body into `build_router`.
  - Register `login_throttled` only `if password_login`.
  - Add `logout`:
    - deps `fastapi_users.authenticator.current_user_token(active=True)` and `auth_backend.get_strategy`;
    - it returns `await auth_backend.logout(strategy, user, token)`.
  - Drop the `get_auth_router` include and its shadowing comment.
  - Keep the users router and the Task 2 Google include.

- [ ] **Step 4: Run the tests and watch them pass**

  Run the full backend suite, `uv run ruff check . && uv run ruff format --check .`, and `uv run alembic check` against the test DB, the way CI does.

  Expected: all pass, and alembic reports no changes.

- [ ] **Step 5: Regenerate frontend API types**

  Follow the CLAUDE.md "Regenerate API types" commands, then run `cd frontend && npm run check`.

  Expected: 0 errors.

- [ ] **Step 6: Commit**

  `feat(auth): no password login in prod; explicit logout route`

---

### Task 4: sqladmin reads the auth cookie

**Files:**
- Modify: `backend/app/admin/auth.py`.
- Test: `backend/tests/admin/test_auth.py`.

**Interfaces:**
- Consumes: `cookie_transport.cookie_name` and `get_jwt_strategy()` from `app.auth.backend`; `get_user_db` and `get_user_manager`; `settings.frontend_url`.

- [ ] **Step 1: Write the failing tests**

  Replace the existing test.
  - `test_admin_without_cookie_redirects_to_frontend_auth`: `client.get("/admin/", follow_redirects=False)` gives 302 or 303 with `location == "http://localhost:5173/auth"`.
  - `test_admin_superuser_cookie_ok`: `superuser_client.get("/admin/")` gives 200.
  - `test_admin_non_superuser_cookie_redirects`: log in as `make_user(superuser=False)` on a fresh client. Expect a redirect to `http://localhost:5173/auth`.
  - `test_admin_garbage_cookie_redirects`: cookie `fastapiusersauth=garbage`. Expect a redirect to `http://localhost:5173/auth`, not a 500.

- [ ] **Step 2: Run the tests and watch them fail**

  Run `TEST_PG_HOSTPORT=localhost:5434 uv run pytest tests/admin -v`.

  Expected: the superuser test gets a redirect instead of 200, and the location is `/admin/login`.

- [ ] **Step 3: Implement**

  - **`authenticate`.**
    - Reads the cookie.
    - When there is a token, it resolves a user manager the way `login` does today and calls `await get_jwt_strategy().read_token(token, user_manager)`.
    - It returns `True` only for an active superuser, and otherwise `RedirectResponse(f"{settings.frontend_url}/auth", status_code=302)`.
  - **`login`.** Always returns `False`. Delete the password code.
  - **`logout`.** Returns a redirect to `{frontend_url}/auth` with the auth cookie deleted (`response.delete_cookie(cookie_transport.cookie_name)`).
  - Leave `SecureAdminAuth` and the session middleware unchanged.

- [ ] **Step 4: Run the tests and watch them pass**

  Run the full backend suite.

  Expected: all pass.

- [ ] **Step 5: Commit**

  `feat(admin): authenticate sqladmin with the app auth cookie`

---

### Task 5: Frontend Google sign-in

**Files:**
- Modify: `frontend/src/lib/core/config.ts`, `frontend/src/test/mocks/config.ts`, `frontend/src/lib/core/auth.svelte.ts`, `frontend/src/routes/auth/+page.svelte`.
- Create: `frontend/src/routes/auth/callback/+page.svelte`.
- Test: `frontend/src/lib/core/auth.svelte.test.ts`.

**Interfaces:**
- Consumes: the Task 2 and Task 3 routes.
- Produces:
  - `PASSWORD_LOGIN: boolean` in `config.ts`, from `env.PUBLIC_PASSWORD_LOGIN === 'true'` (`$env/dynamic/public`);
  - `getGoogleAuthorizeUrl(): Promise<string>`;
  - `finishGoogleLogin(user: UserState, search: string): Promise<{ success: boolean; message?: string }>`.

- [ ] **Step 1: Write the failing tests**

  Use `mockFetch` from `src/test/mocks/fetch.ts` and add `export const PASSWORD_LOGIN = true;` to the config mock.
  - `getGoogleAuthorizeUrl` fetches a URL ending in `/auth/google/authorize` with `credentials: 'include'`, and returns `authorization_url` from the JSON.
  - When authorize answers 404, `getGoogleAuthorizeUrl` rejects with `Error('Google sign-in is not configured')`.
  - `finishGoogleLogin(user, '?code=c&state=s')` on 204 fetches `/auth/google/callback?code=c&state=s` with credentials. It then calls `/users/me`, returns `{ success: true }`, and the stubbed `page.url.pathname === '/market'`.
  - Error copy on 400:
    - `{detail: 'LOGIN_BAD_CREDENTIALS'}` gives `message === 'This Google account has no access.'`;
    - `{detail: 'OAUTH_NOT_AVAILABLE_EMAIL'}` gives `'Google did not return a verified email.'`;
    - any other detail gives `'Google sign-in failed. Try again.'`.
  - On 500, `finishGoogleLogin` gives `{ success: false, message: 'Google sign-in failed. Try again.' }`. This is Review Focus 1.

- [ ] **Step 2: Run the tests and watch them fail**

  Run `cd frontend && npx vitest run src/lib/core/auth.svelte.test.ts`.

  Expected: FAIL, because the functions are not exported.

- [ ] **Step 3: Implement the helpers and the config flag**

  - Put them next to `login` and `logout`, in the same style.
  - `finishGoogleLogin` reads the JSON body only when the status is not ok, and falls back to the generic message if parsing fails.

- [ ] **Step 4: Run the tests and watch them pass**

  Run `npm test`.

  Expected: all pass.

- [ ] **Step 5: Build the pages**

  **`/auth`:**
  - A full-width `btn btn-primary` labelled **"Sign in with Google"**. On click it calls `getGoogleAuthorizeUrl()` and then `window.location.assign(url)`.
  - An error from that call shows in the existing alert.
  - The existing password form renders only `{#if PASSWORD_LOGIN}`, below a DaisyUI `divider` reading "or".
  - The form button keeps the label "Sign In", because the e2e selectors depend on it.

  **`/auth/callback`:**
  - `onMount` runs `finishGoogleLogin(user, window.location.search)` once. A spinner shows while it runs.
  - On failure the page shows an `alert alert-error` with the message and a link "Back to sign in" pointing to `/auth`.

- [ ] **Step 6: Verify with the flag unset**

  Run `npm run check && npm run build`, with no `PUBLIC_PASSWORD_LOGIN` in the env. This is Review Focus 4.

  Expected: 0 errors, and the build succeeds.

- [ ] **Step 7: Commit**

  `feat(frontend): Google sign-in on /auth and /auth/callback`

---

### Task 6: Infra, docs, e2e check

**Files:**
- Modify: `infra/.env.example` and the `infra/compose/docker-compose.{dev,e2e,prod}.yml` files.
- Modify: `infra/caddy/Caddyfile` and `infra/tests/test_caddy_headers.sh`.
- Modify: `README.md`, `CLAUDE.md`, `docs/ai/architecture.md`, `docs/ai/constitution.md`, `docs/ai/roadmap.md` and `docs/ai/progress.md`.

- [ ] **Step 1: Write the failing infra check**

  Append to `test_caddy_headers.sh`: fail unless `grep -qE 'redir https://\{env.APP_DOMAIN\}\{uri\}' infra/caddy/Caddyfile`.

  Run `bash infra/tests/test_caddy_headers.sh`.

  Expected: FAIL.

- [ ] **Step 2: Implement the infra changes**

  - **Caddyfile.** The main site block serves only `{env.APP_DOMAIN}`. A new block `{env.APP_WWW_DOMAIN} { redir https://{env.APP_DOMAIN}{uri} permanent }` handles `www`.
  - **Prod compose, backend:**
    - `GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID:?GOOGLE_CLIENT_ID is required}`;
    - the same pattern for `GOOGLE_CLIENT_SECRET`;
    - `FRONTEND_URL: https://${APP_DOMAIN}`.
  - **Dev compose, backend:** `GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID:-}` and `GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET:-}`.
  - **Dev compose, frontend:** add `PUBLIC_PASSWORD_LOGIN: "true"` to `environment`.
  - **E2e compose:** `frontend-e2e` gets `environment: { PUBLIC_PASSWORD_LOGIN: "true" }`, a runtime env, not a build arg.
  - **`infra/.env.example`.** A new `# ── Google sign-in ──` section with `GOOGLE_CLIENT_ID=`, `GOOGLE_CLIENT_SECRET=` and `# FRONTEND_URL=https://example.com (prod default comes from APP_DOMAIN)`. Each line gets a one-line comment.

  Re-run `bash infra/tests/test_caddy_headers.sh` and every `infra/tests/*.sh`.

  Expected: all exit 0.

- [ ] **Step 3: Write the docs**

  **README**, a new section "Google sign-in setup". These are the spec's six steps, verbatim in meaning:
  1. Enable the People API.
  2. Create a Web OAuth client.
  3. Add the redirect URIs `https://<domain>/auth/callback` and `http://localhost:5173/auth/callback`.
  4. Set the consent screen to Testing, with the owner as the only test user.
  5. Put the ID and secret in the prod env.
  6. Run `create-superuser` with the Google account's primary email.

  The README also adds that local password login needs `PUBLIC_PASSWORD_LOGIN=true`, which dev compose already sets.

  **CLAUDE.md**, Architecture:
  - the auth bullet becomes "Google OAuth (existing superusers only) + password login outside prod; cookie JWT 7 days";
  - one gotcha: e2e uses the password form, never Google.

  **`architecture.md`:** the auth section, plus the Google flow in 4 steps.

  **`constitution.md`, API rules:**
  - "Production has no password login."
  - "Google sign-in never creates accounts."

  **`roadmap.md`:** "Google-only login" goes under Done.

  **`progress.md`:** a 2026-10-21 entry.

- [ ] **Step 4: Run the e2e regression**

  Run `make e2e-up && make e2e-migrate && make e2e-seed && make e2e-test`. Podman is absent locally, so use the docker-compose equivalents the Makefile wraps, as in the previous plan.

  Expected: the same 10/10 as before.

  Then `make e2e-down`, or the docker equivalent.

- [ ] **Step 5: Commit**

  `docs(auth): Google sign-in setup; infra: www redirect, Google env`
