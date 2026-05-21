# Audit Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate all 🔴 critical and 🟠 high findings from the LLM-council audit (chairman verdict 2026-05-21) using strict TDD discipline.

**Architecture:** Three sequential sprints — Sprint 0 (security/infra critical, ~3h), Sprint 1 (correctness/architecture high, ~6h), Backlog (medium polish). Every behavioral change starts with a red test; pure config changes use verification commands instead of unit tests where TDD adds no signal.

**Tech Stack:** FastAPI · SQLModel · SvelteKit 5 · PostgreSQL · slowapi · fastapi-users · sqladmin · Caddy · podman compose · discord.py · pytest · vitest

**Source of truth:** Chairman verdict tables (K1–K8 critical, W1–W10 high, F1–F10 downgrades) — see prior conversation turn.

**Branching:** One feature branch per sprint (`fix/audit-sprint-0`, `fix/audit-sprint-1`). Commit after each task. No pushing until user asks.

---

## File Structure

### New files
- `backend/tests/conftest.py` — **extended** with `session`, `session_factory`, `async_client`, `sample_user`, `sample_item`, `sample_leaf_item`, `item_with_broken_recipe`, `ingest_token` fixtures (Task 0.0)
- `backend/app/ingest/dependencies.py` — Bearer token verifier for ingest endpoint
- `backend/tests/test_ingest_auth.py` — Auth tests for ingest
- `backend/tests/test_settings_validator.py` — Prod-default rejection tests
- `backend/tests/test_prices_race.py` — Concurrent `add_price_point` test
- `backend/tests/test_user_inventory_unfollow.py` — Atomic DELETE test
- `backend/tests/test_user_inventory_for_recipe.py` — Error propagation test
- `backend/tests/test_user_read_schema.py` — OpenAPI drift guard
- `backend/tests/test_auth_rate_limit.py` — Per-IP rate-limit tests
- `frontend/vitest.config.ts` — Vitest config
- `frontend/src/lib/auth.svelte.test.ts` — SSR isolation test
- `frontend/src/lib/crafting.ts` — Shared `computeNodeCost` (Sprint 1 / refactor)
- `frontend/src/lib/crafting.test.ts` — Recursion depth test
- `discord_bot/cogs/_http.py` — Shared httpx singleton

### Modified files
- `backend/app/admin_auth.py` — Remove duplicate `authentication_backend = AdminAuth(...)` (line 46)
- `backend/app/config/settings.py` — Split secrets, reject defaults in prod, add `environment` + `ingest_token`
- `backend/app/ingest/router.py` — Add `Depends(verify_ingest_token)`
- `backend/app/auth/router.py` — Wrap fastapi-users routers with rate limits
- `backend/app/auth/manager.py` — Use distinct `reset_password_token_secret` / `verification_token_secret`
- `backend/app/auth/schemas.py` — Remove `@model_serializer` strip; switch to explicit schema fields
- `backend/app/prices/services.py` — Atomic `current_price` UPDATE with row lock
- `backend/app/user_inventory/services.py` — Atomic `DELETE WHERE`, stop swallowing `AppError`
- `backend/app/main.py` — Pass `proxy_headers` flag (or document via uvicorn CLI)
- `backend/Dockerfile`, `frontend/Dockerfile`, `discord_bot/Dockerfile` — Add `USER app`
- `infra/caddy/Caddyfile` — Security headers block, restrict `/docs` to dev
- `infra/compose/docker-compose.prod.yml` — `--proxy-headers --forwarded-allow-ips="*"`, new env vars, `discord_bot` service
- `infra/compose/docker-compose.dev.yml` — Same uvicorn flags, discord_bot service
- `discord_bot/cogs/prices.py` — Use shared httpx singleton
- `frontend/package.json` — Pin TS to `~5.6.0`
- `frontend/src/lib/auth.svelte.ts` — Convert module-level `$state` to per-request context
- `frontend/src/lib/components/crafting/RecipeTree.svelte` — Import shared `computeNodeCost`, add depth guard
- `frontend/src/routes/items/[id]/+page.svelte` — Import shared `computeNodeCost`, replace `(row: any)` with typed row
- `.env.example` — Add `INGEST_TOKEN`, `RESET_TOKEN_SECRET`, `VERIFICATION_TOKEN_SECRET`, `ENVIRONMENT`

---

# Sprint 0 — Critical (🔴), target ~3h

Branch: `fix/audit-sprint-0`.

---

### Task 0.0: Test infrastructure scaffolding (PREREQUISITE)

**Why:** Current `backend/tests/conftest.py` only exposes `setup_database` and `client` (sync `TestClient`). Every test introduced in Sprint 0/1 references `session`, `session_factory`, `async_client`, `sample_user`, `sample_item`, `sample_leaf_item`, `item_with_broken_recipe`, `ingest_token` — none exist yet. Skipping this means every later task's "should fail" step fails for the wrong reason (ImportError / fixture-not-found), masking the real red.

**Files:**
- Modify: `backend/tests/conftest.py`
- Create: `infra/tests/.gitkeep` (so subsequent `chmod +x infra/tests/*.sh` steps don't race a missing dir)
- Modify: `backend/pyproject.toml` — add `pytest-mock`, `pytest-repeat`, `httpx` (if not already a dep) to `[dependency-groups].dev`

- [ ] **Step 1: Create infra/tests directory**

```bash
mkdir -p infra/tests && touch infra/tests/.gitkeep
```

- [ ] **Step 2: Add dev deps**

```bash
cd backend && uv add --dev pytest-mock pytest-repeat
```

(Verify `httpx` and `pytest-asyncio` are already present — they're transitive via fastapi/fastapi-users.)

- [ ] **Step 3: Extend conftest.py**

Append (or merge) to `backend/tests/conftest.py`:

```python
import uuid
from typing import AsyncIterator, Callable

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config.db import async_session_maker
from app.config.settings import settings as settings_singleton
from app.items.models import Item, ItemCategory, ItemGrade
from app.main import app
from app.recipes.models import Recipe, RecipeIngredient  # adjust to real module path
from app.users.models import User


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with async_session_maker() as s:
        yield s


@pytest.fixture
def session_factory() -> Callable[[], AsyncSession]:
    """Returns the async session context manager itself (call it to enter a new session)."""
    return async_session_maker


@pytest_asyncio.fixture
async def async_client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def sample_user(session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"user-{uuid.uuid4().hex[:8]}@test.local",
        hashed_password="x" * 60,
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_item(session: AsyncSession) -> Item:
    item = Item(
        name=f"item-{uuid.uuid4().hex[:8]}",
        category=ItemCategory.material,
        grade=ItemGrade.basic,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@pytest_asyncio.fixture
async def sample_leaf_item(session: AsyncSession) -> Item:
    """An item that exists but has no recipe (leaf)."""
    item = Item(
        name=f"leaf-{uuid.uuid4().hex[:8]}",
        category=ItemCategory.material,
        grade=ItemGrade.basic,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@pytest_asyncio.fixture
async def item_with_broken_recipe(session: AsyncSession) -> Item:
    """An item whose recipe references an ingredient item_id that does NOT exist
    in the items table. build_craft_tree must raise AppError on this fixture."""
    parent = Item(
        name=f"broken-{uuid.uuid4().hex[:8]}",
        category=ItemCategory.material,
        grade=ItemGrade.basic,
    )
    session.add(parent)
    await session.commit()
    await session.refresh(parent)
    # Insert a Recipe row pointing the ingredient to a non-existent item_id.
    # Adjust column names to match the real Recipe schema.
    recipe = Recipe(item_id=parent.id, labour=1)
    session.add(recipe)
    await session.flush()
    session.add(RecipeIngredient(recipe_id=recipe.id, item_id=10**9, qty=1))
    await session.commit()
    return parent


@pytest.fixture
def ingest_token(monkeypatch) -> str:
    token = "test-ingest-token-must-be-32-characters-x"
    monkeypatch.setenv("INGEST_TOKEN", token)
    monkeypatch.setattr(settings_singleton, "ingest_token", token)
    return token


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Prevent rate-limit counts leaking between tests (Task 0.8 depends on this)."""
    from app.config.rate_limit import limiter
    limiter.reset()
    yield
    limiter.reset()
```

> **NOTE:** The exact import paths for `Recipe` / `RecipeIngredient` and the columns on `User` must be adjusted to match the actual codebase. Verify by reading `backend/app/recipes/models.py` (or wherever recipes live) and `backend/app/users/models.py` before running. If column names differ (e.g. `hashed_password` vs `password_hash`), align.

- [ ] **Step 4: Verify fixtures load**

Run: `cd backend && uv run pytest --collect-only -q 2>&1 | tail -20`
Expected: no fixture-resolution errors; existing tests still collect.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/conftest.py backend/pyproject.toml backend/uv.lock infra/tests/.gitkeep
git commit -m "test(backend): add session/async_client/sample_* fixtures + infra/tests dir"
```

---

### Task 0.1: Remove duplicate `authentication_backend` (W4)

**Files:**
- Modify: `backend/app/admin_auth.py:46`

- [ ] **Step 1: Run the existing admin smoke test (baseline)**

Run: `cd backend && uv run pytest -k admin -v` (if no admin test exists, skip — this fix is a delete-only).
Expected: PASS or collected 0 (admin route boots).

- [ ] **Step 2: Delete dead line**

Open `backend/app/admin_auth.py` and remove line 46 plus the trailing blank line:

```python
# DELETE these two lines:
authentication_backend = AdminAuth(secret_key=settings.admin_session_secret)

```

The `SecureAdminAuth` assignment on line 67 remains the live one.

- [ ] **Step 3: Verify backend still imports**

Run: `cd backend && uv run python -c "from app.admin_auth import authentication_backend; print(type(authentication_backend).__name__)"`
Expected: `SecureAdminAuth`

- [ ] **Step 4: Commit**

```bash
git add backend/app/admin_auth.py
git commit -m "fix(admin): remove dead duplicate authentication_backend assignment"
```

---

### Task 0.2: Pin TypeScript to released version (K7)

**Files:**
- Modify: `frontend/package.json:25`
- Modify: `frontend/package-lock.json` (regenerated)

- [ ] **Step 1: Confirm baseline failure**

Run: `cd frontend && npm view typescript@6.0.2 version 2>&1 | head -3`
Expected: empty / `npm error code E404` (version doesn't exist on npm).

- [ ] **Step 2: Edit package.json**

Change line 25:

```json
"typescript": "~5.6.0",
```

- [ ] **Step 3: Reinstall**

Run: `cd frontend && rm -rf node_modules && npm install`
Expected: install succeeds with TS 5.6.x.

- [ ] **Step 4: Run type-check**

Run: `cd frontend && npm run check`
Expected: completes (warnings OK, no fatal TS engine errors).

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "fix(frontend): pin typescript to released ~5.6.0 (was bogus ^6.0.2)"
```

---

### Task 0.3: Run containers as non-root (K3)

**Files:**
- Modify: `backend/Dockerfile`
- Modify: `frontend/Dockerfile`
- Modify: `discord_bot/Dockerfile`

- [ ] **Step 1: Write the failing verification script**

Create `infra/tests/test_dockerfiles_non_root.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
fail=0
for f in backend/Dockerfile frontend/Dockerfile discord_bot/Dockerfile; do
  if ! grep -qE '^USER\s+\S' "$f"; then
    echo "FAIL: $f has no USER directive"
    fail=1
  fi
done
exit $fail
```

Make executable: `chmod +x infra/tests/test_dockerfiles_non_root.sh`.

- [ ] **Step 2: Run — should fail**

Run: `bash infra/tests/test_dockerfiles_non_root.sh`
Expected: 3 FAIL lines, exit 1.

- [ ] **Step 3: Patch backend/Dockerfile**

Append before the `CMD`/`ENTRYPOINT` (or final stage):

```dockerfile
# uv writes its cache to $HOME/.cache/uv by default → root-only path.
# Pin both cache and venv to /app and chown so the non-root user can use them.
ENV UV_CACHE_DIR=/app/.uv-cache \
    UV_PROJECT_ENVIRONMENT=/app/.venv
RUN useradd --create-home --shell /bin/bash app \
 && mkdir -p /app/.uv-cache \
 && chown -R app:app /app
USER app
```

> **Preferred:** drop `uv run` from runtime `CMD` entirely and invoke `/app/.venv/bin/uvicorn` and `/app/.venv/bin/alembic` directly — eliminates the cache-writability question. If you keep `uv run`, the ENV above is mandatory.

- [ ] **Step 4: Patch frontend/Dockerfile**

The `node:*-alpine` base provides a `node` user — use it (chown AFTER all COPY / build steps that produce `build/` and `node_modules/`):

```dockerfile
RUN chown -R node:node /app
USER node
```

- [ ] **Step 5: Patch discord_bot/Dockerfile**

Same pattern as backend:

```dockerfile
RUN useradd --create-home --shell /bin/bash bot && chown -R bot:bot /app
USER bot
```

- [ ] **Step 6: Re-run verification — should pass**

Run: `bash infra/tests/test_dockerfiles_non_root.sh`
Expected: exit 0, no FAIL lines.

- [ ] **Step 7: Smoke-build (one image to confirm syntax)**

Run: `cd backend && podman build -t arr-backend-test . && podman run --rm arr-backend-test id`
Expected: `uid=1000(app) gid=1000(app) ...` (or similar non-zero uid).

- [ ] **Step 8: Commit**

```bash
git add backend/Dockerfile frontend/Dockerfile discord_bot/Dockerfile infra/tests/test_dockerfiles_non_root.sh
git commit -m "fix(infra): run all containers as non-root user"
```

---

### Task 0.4: Caddy security headers + hide docs in prod + protect /admin (K4)

**Files:**
- Modify: `infra/caddy/Caddyfile`
- Modify: `backend/app/main.py` — disable FastAPI docs when `environment == "prod"`
- Modify: `frontend/svelte.config.js` — enable CSP nonce so SSR hydration scripts survive a strict `script-src`
- Modify: `.env.example` / `infra/compose/docker-compose.prod.yml` — add `ADMIN_ALLOWED_IPS` env

- [ ] **Step 1: Write the failing header test**

Create `infra/tests/test_caddy_headers.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
required=(
  "Strict-Transport-Security"
  "X-Frame-Options"
  "X-Content-Type-Options"
  "Referrer-Policy"
)
fail=0
for h in "${required[@]}"; do
  if ! grep -qiE "^\s*${h}" infra/caddy/Caddyfile; then
    echo "FAIL: missing header ${h}"
    fail=1
  fi
done
# CSP is verified separately — must come from SvelteKit, not Caddy.
if ! grep -q "csp" frontend/svelte.config.js; then
  echo "FAIL: frontend/svelte.config.js missing kit.csp config"
  fail=1
fi
exit $fail
```

`chmod +x infra/tests/test_caddy_headers.sh`.

- [ ] **Step 2: Run — should fail**

Run: `bash infra/tests/test_caddy_headers.sh`
Expected: 5 FAIL lines (4 Caddy headers + CSP config).

- [ ] **Step 3: Edit Caddyfile**

> **CSP gotcha:** SvelteKit injects inline `<script>` blobs (`__sveltekit_data`) on every SSR'd page. A bare `script-src 'self'` will brick the frontend. We rely on SvelteKit's built-in CSP nonce machinery (Step 5) — the Caddy header here uses `'strict-dynamic'` + nonce so it cooperates with SvelteKit-emitted nonces. Alternatively, drop `Content-Security-Policy` from Caddy entirely and let SvelteKit emit it per-response (its `kit.csp` config writes a `<meta http-equiv="Content-Security-Policy">` tag with the per-request nonce).

> **`/admin*` protection:** sqladmin's password login is brute-forceable from the open internet and is **not** behind slowapi. Restrict access by IP allowlist (preferred for self-hosted) or basic_auth. Below uses `remote_ip` with an env-supplied CIDR list.

Replace contents with:

```caddyfile
{
    admin off
}

(security_headers) {
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        # CSP is emitted per-response by SvelteKit (kit.csp). Caddy adds the
        # static fallbacks only — do NOT set script-src here or it will collide
        # with SvelteKit's nonced policy.
        X-Frame-Options "DENY"
        X-Content-Type-Options "nosniff"
        Referrer-Policy "strict-origin-when-cross-origin"
        Permissions-Policy "geolocation=(), microphone=(), camera=()"
        -Server
    }
}

@admin_allowed {
    remote_ip {env.ADMIN_ALLOWED_IPS}
}

{env.APP_DOMAIN}, {env.APP_WWW_DOMAIN} {
    import security_headers

    handle /api/* {
        reverse_proxy backend:8000
    }

    handle /admin* {
        @denied not remote_ip {env.ADMIN_ALLOWED_IPS}
        respond @denied "Forbidden" 403
        reverse_proxy backend:8000
    }

    # /docs, /redoc, /openapi.json intentionally NOT routed in prod.
    # FastAPI itself also disables them when ENVIRONMENT=prod (Step 4b).

    handle {
        reverse_proxy frontend:3000
    }
}
```

> Update the header verification script (`infra/tests/test_caddy_headers.sh`) — `Content-Security-Policy` is no longer in the Caddyfile (SvelteKit emits it). Drop it from the `required=(...)` list, OR replace with a `frontend/svelte.config.js` check that `kit.csp` is configured.

- [ ] **Step 4: Configure SvelteKit CSP nonce**

Edit `frontend/svelte.config.js`:

```js
const config = {
  kit: {
    csp: {
      mode: "auto", // nonce on SSR, hash on prerendered pages
      directives: {
        "default-src": ["self"],
        "img-src": ["self", "data:"],
        "script-src": ["self", "strict-dynamic"],
        "style-src": ["self", "unsafe-inline"],
        "connect-src": ["self"],
        "frame-ancestors": ["none"],
      },
    },
    // ... existing config preserved
  },
};
```

- [ ] **Step 4b: Disable FastAPI docs in prod**

Edit `backend/app/main.py`:

```python
_is_prod = settings.environment == "prod"

app = FastAPI(
    lifespan=lifespan,
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url=None if _is_prod else "/openapi.json",
)
```

Add a test in `backend/tests/test_docs_disabled_in_prod.py`:

```python
import importlib
import pytest


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_docs_404_in_prod(monkeypatch, path):
    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setenv("AUTH_SECRET", "a" * 40)
    monkeypatch.setenv("ADMIN_SESSION_SECRET", "b" * 40)
    monkeypatch.setenv("RESET_TOKEN_SECRET", "r" * 40)
    monkeypatch.setenv("VERIFICATION_TOKEN_SECRET", "v" * 40)
    monkeypatch.setenv("INGEST_TOKEN", "i" * 40)
    import app.config.settings as s
    importlib.reload(s)
    import app.main as m
    importlib.reload(m)
    from fastapi.testclient import TestClient
    client = TestClient(m.app)
    assert client.get(path).status_code == 404
```

- [ ] **Step 4c: Wire `ADMIN_ALLOWED_IPS` env**

Append to `.env.example`:

```bash
# Comma-separated CIDR list authorised to reach /admin (sqladmin)
# Example: home VPN + office. Empty value = 403 for everyone.
ADMIN_ALLOWED_IPS=10.0.0.0/8 172.16.0.0/12
```

Add to `infra/compose/docker-compose.prod.yml` caddy env:

```yaml
      ADMIN_ALLOWED_IPS: ${ADMIN_ALLOWED_IPS:?ADMIN_ALLOWED_IPS is required (set to a CIDR or 0.0.0.0/0 if you really want public)}
```

- [ ] **Step 5: Re-run header test**

Run: `bash infra/tests/test_caddy_headers.sh`
Expected: exit 0.

- [ ] **Step 6: Validate Caddy syntax**

Run: `podman run --rm -v $PWD/infra/caddy/Caddyfile:/etc/caddy/Caddyfile:ro -e APP_DOMAIN=example.com -e APP_WWW_DOMAIN=www.example.com -e ADMIN_ALLOWED_IPS=10.0.0.0/8 caddy:2-alpine caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile`
Expected: `Valid configuration`.

- [ ] **Step 7: Commit**

```bash
git add infra/caddy/Caddyfile infra/tests/test_caddy_headers.sh \
        frontend/svelte.config.js \
        backend/app/main.py backend/tests/test_docs_disabled_in_prod.py \
        .env.example infra/compose/docker-compose.prod.yml
git commit -m "fix(infra): security headers + SvelteKit CSP nonce + admin IP allowlist + hide FastAPI docs in prod"
```

---

### Task 0.5: Uvicorn `--proxy-headers` so rate limit sees real client IP (K2)

**Files:**
- Modify: `infra/compose/docker-compose.prod.yml`
- Modify: `infra/compose/docker-compose.dev.yml`

- [ ] **Step 1: Write the failing grep test**

Create `infra/tests/test_uvicorn_proxy_headers.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
for f in infra/compose/docker-compose.prod.yml infra/compose/docker-compose.dev.yml; do
  if ! grep -q -- "--proxy-headers" "$f"; then
    echo "FAIL: $f missing --proxy-headers"
    exit 1
  fi
done
echo OK
```

`chmod +x infra/tests/test_uvicorn_proxy_headers.sh`.

- [ ] **Step 2: Run — should fail**

Run: `bash infra/tests/test_uvicorn_proxy_headers.sh`
Expected: `FAIL: ...prod.yml missing --proxy-headers`.

- [ ] **Step 3: Patch prod compose**

In `infra/compose/docker-compose.prod.yml` backend service, edit the `command:` block. Scope `--forwarded-allow-ips` to the compose network range (NOT `"*"` — wildcard lets anyone spoof `X-Forwarded-For` if the backend port is ever exposed to the host). Also make sure backend uses `expose:` not `ports:` so port 8000 is not published.

```yaml
    command: >
      sh -c "uv run alembic upgrade head &&
             uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
                    --proxy-headers --forwarded-allow-ips='10.0.0.0/8,172.16.0.0/12,192.168.0.0/16'"
    expose:
      - "8000"
```

- [ ] **Step 4: Patch dev compose**

Same edit in `infra/compose/docker-compose.dev.yml` backend `command:` (dev may still bind to host via `ports:` for direct curl — that's fine in dev, slowapi just sees the host IP).

- [ ] **Step 5: Re-run — should pass**

Run: `bash infra/tests/test_uvicorn_proxy_headers.sh`
Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add infra/compose/docker-compose.prod.yml infra/compose/docker-compose.dev.yml infra/tests/test_uvicorn_proxy_headers.sh
git commit -m "fix(infra): enable uvicorn --proxy-headers so slowapi sees client IP"
```

---

### Task 0.6: Split auth secrets + reject default secrets in prod (K5, K8)

**Files:**
- Modify: `backend/app/config/settings.py`
- Modify: `backend/app/auth/manager.py`
- Create: `backend/tests/test_settings_validator.py`
- Modify: `.env.example`
- Modify: `infra/compose/docker-compose.prod.yml`

- [ ] **Step 1: Write failing tests**

> **`_env_file=None` gotcha:** pydantic-settings v2 does **not** accept `_env_file` as a positional/keyword init arg — it's a `model_config` field. Passing it raises `TypeError`. To prevent `.env` interference we instead `chdir(tmp_path)` (so no `.env` is on the lookup path) and `monkeypatch.delenv` everything.

Create `backend/tests/test_settings_validator.py`:

```python
import pytest
from pydantic import ValidationError


_SECRET_ENV_KEYS = (
    "AUTH_SECRET", "ADMIN_SESSION_SECRET", "RESET_TOKEN_SECRET",
    "VERIFICATION_TOKEN_SECRET", "INGEST_TOKEN", "ENVIRONMENT",
)


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    """Run each test from an empty cwd with no secret env vars — guarantees the
    validator sees only what the test passes in as kwargs."""
    monkeypatch.chdir(tmp_path)
    for k in _SECRET_ENV_KEYS:
        monkeypatch.delenv(k, raising=False)


def test_default_secrets_rejected_when_environment_is_prod(clean_env):
    from app.config.settings import Settings
    with pytest.raises(ValidationError) as exc:
        Settings(environment="prod")  # all secret fields fall back to defaults
    msg = str(exc.value).lower()
    assert "default" in msg or "must be set" in msg


def test_secrets_must_be_32_chars(clean_env):
    from app.config.settings import Settings
    with pytest.raises(ValidationError):
        Settings(environment="dev", auth_secret="too-short")


def test_auth_reset_verify_secrets_must_differ(clean_env):
    from app.config.settings import Settings
    same = "x" * 40
    with pytest.raises(ValidationError):
        Settings(
            environment="prod",
            auth_secret=same,
            admin_session_secret="a" * 40,
            reset_token_secret=same,
            verification_token_secret="v" * 40,
            ingest_token="i" * 40,
        )
```

- [ ] **Step 2: Run — should fail**

Run: `cd backend && uv run pytest tests/test_settings_validator.py -v`
Expected: failures because `reset_token_secret`, `verification_token_secret`, `ingest_token`, and the `environment` field don't exist on `Settings` yet — Pydantic will reject the unknown kwargs.

- [ ] **Step 3: Update `settings.py` — MERGE, don't replace**

> Current `settings.py` only has `database_url`, `async_database_url`, `auth_secret`, `admin_session_secret`, `cookie_secure`, `sql_echo`, `cors_origins` and a `validate_secrets` `field_validator`. **Add the new fields and `_check_secrets` model-validator alongside; do not drop anything.** The full file after edit should look roughly like this (re-read the live file first to merge any fields added since this plan was written):

```python
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_DEFAULT_AUTH_SECRET = "temporary-development-secret-must-be-32-chars"
_DEFAULT_ADMIN_SECRET = "temporary-admin-session-secret-must-be-32-chars"
_DEFAULT_RESET_SECRET = "temporary-reset-token-secret-must-be-32-chars-x"
_DEFAULT_VERIFY_SECRET = "temporary-verify-token-secret-must-be-32-chars"
_DEFAULT_INGEST_TOKEN = "temporary-ingest-token-must-be-32-chars-long-x"

_DEFAULTS = {
    _DEFAULT_AUTH_SECRET,
    _DEFAULT_ADMIN_SECRET,
    _DEFAULT_RESET_SECRET,
    _DEFAULT_VERIFY_SECRET,
    _DEFAULT_INGEST_TOKEN,
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    environment: Literal["dev", "test", "prod"] = "dev"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/app"
    async_database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/app"
    )

    auth_secret: str = _DEFAULT_AUTH_SECRET
    admin_session_secret: str = _DEFAULT_ADMIN_SECRET
    reset_token_secret: str = _DEFAULT_RESET_SECRET
    verification_token_secret: str = _DEFAULT_VERIFY_SECRET
    ingest_token: str = _DEFAULT_INGEST_TOKEN

    cookie_secure: bool = False
    sql_echo: bool = False

    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    @model_validator(mode="after")
    def _check_secrets(self) -> "Settings":
        secrets = {
            "auth_secret": self.auth_secret,
            "admin_session_secret": self.admin_session_secret,
            "reset_token_secret": self.reset_token_secret,
            "verification_token_secret": self.verification_token_secret,
            "ingest_token": self.ingest_token,
        }
        for name, value in secrets.items():
            if len(value) < 32:
                raise ValueError(f"{name} must be at least 32 characters long")
        if self.environment == "prod":
            for name, value in secrets.items():
                if value in _DEFAULTS:
                    raise ValueError(
                        f"{name} is using default value — must be set explicitly in prod"
                    )
        token_secrets = {
            self.auth_secret,
            self.reset_token_secret,
            self.verification_token_secret,
        }
        if len(token_secrets) != 3:
            raise ValueError(
                "auth_secret, reset_token_secret, verification_token_secret must all differ"
            )
        return self


settings = Settings()
```

- [ ] **Step 4: Run tests — should pass**

Run: `cd backend && uv run pytest tests/test_settings_validator.py -v`
Expected: 3 passed.

- [ ] **Step 5: Wire new secrets into UserManager**

Edit `backend/app/auth/manager.py` — replace any reuse of `settings.auth_secret` for reset/verify:

```python
from app.config.settings import settings
# ...
class UserManager(...):
    reset_password_token_secret = settings.reset_token_secret
    verification_token_secret = settings.verification_token_secret
    # JWT strategy continues to use settings.auth_secret
```

- [ ] **Step 6: Update `.env.example`**

Append:

```bash
ENVIRONMENT=dev
RESET_TOKEN_SECRET=please-change-me-reset-token-secret-32+chars
VERIFICATION_TOKEN_SECRET=please-change-me-verify-token-secret-32+chars
INGEST_TOKEN=please-change-me-ingest-token-32-characters-min
```

- [ ] **Step 7: Update prod compose**

In `infra/compose/docker-compose.prod.yml` backend env, add:

```yaml
      ENVIRONMENT: prod
      RESET_TOKEN_SECRET: ${RESET_TOKEN_SECRET:?RESET_TOKEN_SECRET is required}
      VERIFICATION_TOKEN_SECRET: ${VERIFICATION_TOKEN_SECRET:?VERIFICATION_TOKEN_SECRET is required}
      INGEST_TOKEN: ${INGEST_TOKEN:?INGEST_TOKEN is required}
```

- [ ] **Step 8: Run full backend test suite**

Run: `cd backend && uv run pytest -v`
Expected: all pass (no regressions in existing tests).

- [ ] **Step 9: Commit + release-note**

```bash
git add backend/app/config/settings.py backend/app/auth/manager.py backend/tests/test_settings_validator.py .env.example infra/compose/docker-compose.prod.yml infra/compose/docker-compose.dev.yml
git commit -m "fix(auth): split JWT/reset/verify secrets, reject defaults in prod

BREAKING (operational): existing prod deployments share auth_secret with reset/verify.
After this commit every outstanding password-reset and email-verification token
becomes invalid. Communicate to users; consider forcing a re-verify campaign."
```

---

### Task 0.7: Bearer-token auth on `POST /api/ingest/prices` (K1)

**Files:**
- Create: `backend/app/ingest/dependencies.py`
- Modify: `backend/app/ingest/router.py`
- Create: `backend/tests/test_ingest_auth.py`
- Modify: `discord_bot/cogs/prices.py` (or wherever it posts)

- [ ] **Step 1: Write failing auth tests**

Create `backend/tests/test_ingest_auth.py`:

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ingest_rejects_missing_token(async_client: AsyncClient):
    r = await async_client.post("/api/ingest/prices", json={"rows": []})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_ingest_rejects_bad_token(async_client: AsyncClient):
    r = await async_client.post(
        "/api/ingest/prices",
        json={"rows": []},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_ingest_accepts_valid_token(async_client: AsyncClient, ingest_token: str):
    r = await async_client.post(
        "/api/ingest/prices",
        json={"rows": []},
        headers={"Authorization": f"Bearer {ingest_token}"},
    )
    assert r.status_code == 200
```

Add to `backend/tests/conftest.py` (or extend):

```python
@pytest.fixture
def ingest_token(monkeypatch) -> str:
    token = "test-ingest-token-must-be-32-characters-x"
    monkeypatch.setenv("INGEST_TOKEN", token)
    from app.config import settings as settings_mod
    monkeypatch.setattr(settings_mod.settings, "ingest_token", token)
    return token
```

- [ ] **Step 2: Run — should fail**

Run: `cd backend && uv run pytest tests/test_ingest_auth.py -v`
Expected: 3 failures (endpoint currently returns 200/422 for missing/bad token).

- [ ] **Step 3: Implement dependency**

Create `backend/app/ingest/dependencies.py`:

```python
import hmac

from fastapi import Header, HTTPException, status

from app.config.settings import settings


async def verify_ingest_token(authorization: str | None = Header(default=None)) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(token, settings.ingest_token):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid ingest token")
```

- [ ] **Step 4: Wire into router**

Edit `backend/app/ingest/router.py`:

```python
from app.ingest.dependencies import verify_ingest_token

@router.post(
    "/prices",
    response_model=IngestResponse,
    dependencies=[Depends(verify_ingest_token)],
)
@limiter.limit("60/minute")
async def ingest_prices(...):
    ...
```

- [ ] **Step 5: Run tests — should pass**

Run: `cd backend && uv run pytest tests/test_ingest_auth.py -v`
Expected: 3 passed.

- [ ] **Step 6: Update Discord bot to send bearer**

The actual call site is **`discord_bot/cogs/prices.py:99`** inside the **`post_price`** helper (module-level function, NOT prefixed with underscore — verified in the live file):

```python
resp = await client.post(f"{api_url}/ingest/prices", json=payload)
```

Change to:

```python
resp = await client.post(
    f"{api_url}/ingest/prices",
    json=payload,
    headers={"Authorization": f"Bearer {ingest_token}"},
)
```

`ingest_token` should be read from env (e.g., `os.environ["INGEST_TOKEN"]`) — pass it through the existing call-chain rather than reading globals inside the helper, so tests can inject it. Update the existing tests in `discord_bot/tests/test_prices.py` (sites that mock `respx.post(f"{API_URL}/ingest/prices")`) to assert the request carries `Authorization: Bearer <token>` — add a header assertion to at least one test.

Add `INGEST_TOKEN` env var to `discord_bot/.env.example` (do NOT touch real `.env`).

- [ ] **Step 7: Run full backend suite — no regressions**

Run: `cd backend && uv run pytest -v`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add backend/app/ingest/ backend/tests/test_ingest_auth.py backend/tests/conftest.py \
        discord_bot/cogs/prices.py discord_bot/tests/test_prices.py discord_bot/.env.example
git commit -m "fix(ingest): require bearer INGEST_TOKEN on POST /api/ingest/prices"
```

---

### Task 0.8: Rate-limit `/auth/login,register,forgot-password` (K6)

**Files:**
- Modify: `backend/app/auth/router.py`
- Create: `backend/tests/test_auth_rate_limit.py`

**Routing context (verified):** `app/auth/router.py` mounts `fastapi_users.get_auth_router(auth_backend)` with `prefix="/auth"`, and `main.py` mounts the whole `auth_router` under the `/api` API router. So login lives at **`/api/auth/login`** (NOT `/auth/jwt/login`). Frontend `auth.svelte.ts:56` confirms this.

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_auth_rate_limit.py`:

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_rate_limited_after_5_attempts(async_client: AsyncClient):
    # Hammer login with bad creds; the 6th call within a minute must 429.
    for _ in range(5):
        r = await async_client.post(
            "/api/auth/login",
            data={"username": "x@x.com", "password": "wrong"},
        )
        assert r.status_code in (400, 401)
    r = await async_client.post(
        "/api/auth/login",
        data={"username": "x@x.com", "password": "wrong"},
    )
    assert r.status_code == 429
```

- [ ] **Step 2: Run — should fail**

Run: `cd backend && uv run pytest tests/test_auth_rate_limit.py -v`
Expected: fail (6th request still 400/401).

- [ ] **Step 3: Apply rate limit via explicitly-typed proxy endpoints**

> **Why not `__signature__` reassignment:** FastAPI inspects the route function's signature **at registration time** (inside `@router.post(...)`). slowapi separately scans for a `Request` parameter at the same moment. Reassigning `func.__signature__` AFTER the decorator already ran has no effect on either. Worse, the fastapi-users `login` endpoint takes `credentials: OAuth2PasswordRequestForm = Depends()`, `user_manager`, `strategy` — calling it with `*args, **kwargs` from a `(request, *args, **kwargs)` signature will not receive any of them (FastAPI would never inject them in the first place).
>
> **Correct approach:** write proxies with **explicit, fully-typed signatures** that re-declare every dependency the underlying endpoint needs, then call the manager/strategy directly. This bypasses the fastapi-users routes for the throttled paths and never registers a duplicate route.

Edit `backend/app/auth/router.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users import exceptions as fu_exc
from fastapi_users.router.common import ErrorCode

from app.auth.backend import auth_backend
from app.auth.dependencies import fastapi_users, get_user_manager
from app.auth.schemas import UserCreate, UserRead, UserUpdate
from app.config.rate_limit import limiter
from app.users.models import User

router = APIRouter()

# --- Throttled endpoints (registered FIRST — FastAPI picks the first match) ---


@router.post("/auth/login", tags=["auth"])
@limiter.limit("5/minute")
async def login_throttled(
    request: Request,
    credentials: OAuth2PasswordRequestForm = Depends(),
    user_manager=Depends(get_user_manager),
    strategy=Depends(auth_backend.get_strategy),
):
    user = await user_manager.authenticate(credentials)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorCode.LOGIN_BAD_CREDENTIALS,
        )
    return await auth_backend.login(strategy, user)


@router.post("/auth/register", tags=["auth"], response_model=UserRead, status_code=201)
@limiter.limit("5/hour")
async def register_throttled(
    request: Request,
    user_create: UserCreate,
    user_manager=Depends(get_user_manager),
):
    try:
        created = await user_manager.create(user_create, safe=True, request=request)
    except fu_exc.UserAlreadyExists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorCode.REGISTER_USER_ALREADY_EXISTS,
        )
    except fu_exc.InvalidPasswordException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": ErrorCode.REGISTER_INVALID_PASSWORD, "reason": e.reason},
        )
    return UserRead.model_validate(created)


@router.post("/auth/forgot-password", tags=["auth"], status_code=202)
@limiter.limit("5/hour")
async def forgot_throttled(
    request: Request,
    email: str,
    user_manager=Depends(get_user_manager),
):
    try:
        user = await user_manager.get_by_email(email)
        await user_manager.forgot_password(user, request)
    except (fu_exc.UserNotExists, fu_exc.UserInactive):
        pass  # silent — don't leak account existence
    return None


@router.post("/auth/reset-password", tags=["auth"])
@limiter.limit("5/hour")
async def reset_throttled(
    request: Request,
    token: str,
    password: str,
    user_manager=Depends(get_user_manager),
):
    try:
        await user_manager.reset_password(token, password, request)
    except (fu_exc.InvalidResetPasswordToken, fu_exc.UserNotExists, fu_exc.UserInactive):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorCode.RESET_PASSWORD_BAD_TOKEN,
        )
    except fu_exc.InvalidPasswordException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": ErrorCode.RESET_PASSWORD_INVALID_PASSWORD, "reason": e.reason},
        )


# --- Then mount the rest of fastapi-users routers (logout, verify, users/me, etc.) ---
# These do NOT re-register /login, /register, /forgot-password, /reset-password
# because FastAPI matches the first registered route per (method, path).
router.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth", tags=["auth"]
)
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"]
)
router.include_router(
    fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"]
)
router.include_router(
    fastapi_users.get_verify_router(UserRead), prefix="/auth", tags=["auth"]
)
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"]
)
```

> **Verify route ordering** before running tests: `cd backend && uv run python -c "from app.auth.router import router; [print(r.methods, r.path) for r in router.routes]"`. The throttled `/auth/login` etc. must appear **before** the fastapi-users-mounted duplicates.
>
> **OpenAPI duplicates:** FastAPI **does** include both entries in `openapi.json`. If that bothers you, exclude the fastapi-users routes for those four paths by filtering `_fu_auth_router.routes` before mounting, or hide them with `include_in_schema=False`.

- [ ] **Step 3b: Add positive-path test (catches signature regressions)**

Extend `backend/tests/test_auth_rate_limit.py`:

```python
@pytest.mark.asyncio
async def test_login_throttled_still_accepts_valid_credentials(async_client, sample_user):
    # If the proxy signature is broken, FastAPI returns 422 (form not parsed)
    # — this test catches that even before rate-limit logic is exercised.
    r = await async_client.post(
        "/api/auth/login",
        data={"username": sample_user.email, "password": "correct-horse-battery"},
    )
    # Either 200 (creds happen to match the fixture's hashed_password) or 400
    # (creds wrong). What we MUST NOT see is 422 / 500 — those indicate the
    # proxy signature is broken.
    assert r.status_code in (200, 400)
```

- [ ] **Step 4: Run rate-limit test — should pass**

Run: `cd backend && uv run pytest tests/test_auth_rate_limit.py -v`
Expected: 1 passed.

- [ ] **Step 5: Run full suite**

Run: `cd backend && uv run pytest -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/auth/router.py backend/tests/test_auth_rate_limit.py
git commit -m "fix(auth): apply slowapi rate limits to login/register/reset/verify"
```

---

### Sprint 0 verification

- [ ] **Run all backend tests**

Run: `cd backend && uv run pytest -v`
Expected: all pass.

- [ ] **Run frontend type-check**

Run: `cd frontend && npm run check`
Expected: 0 errors.

- [ ] **Run infra verification scripts**

Run: `bash infra/tests/test_dockerfiles_non_root.sh && bash infra/tests/test_caddy_headers.sh && bash infra/tests/test_uvicorn_proxy_headers.sh`
Expected: 3 × exit 0.

---

# Sprint 1 — High (🟠), target ~6h

Branch: `fix/audit-sprint-1` (cut from sprint-0).

> **EXECUTION ORDER (important):** Task 1.8 (vitest setup) MUST run before Task 1.1 (which writes the first vitest spec, `auth.svelte.test.ts`). Despite the numbering, execute as: **1.8 → 1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6 → 1.7 → 1.9**. Tasks 1.2/1.3/1.6 require `pytest-mock` and `pytest-repeat` from Task 0.0.

---

### Task 1.1: Eliminate module-level `$state` SSR leak in `auth.svelte.ts` (W1)

**Files:**
- Modify: `frontend/src/lib/auth.svelte.ts`
- Modify: `frontend/src/routes/+layout.svelte`
- Create: `frontend/src/lib/auth.svelte.test.ts`

**Scope reality check:** The existing `UserState` shape is `{ data, profile, isLoggedIn, loading }` and the module exports `user, checkMe, fetchProfile, login, register, logout, updateProfile`. Many components likely import these. We MUST preserve the public API; only the SSR sharing is broken. Strategy: keep the same exports but turn `user` into a per-request store delivered via `setContext`, and add a thin getter facade (`getUserState()`) that all consumers migrate to. To avoid breaking everything at once we ALSO leave a deprecated module-level shim that only works in the browser (`typeof window !== "undefined"` guard) and throws on the server.

- [ ] **Step 1: Inventory current consumers**

Run: `cd frontend && grep -rn "auth.svelte" src`. The known consumers (verified against the live tree) are exactly:

| File | What it imports |
|---|---|
| `src/routes/+layout.svelte` | `user, checkMe, logout` |
| `src/routes/auth/+page.svelte` | `login, register, user` |
| `src/routes/settings/+page.svelte` | `user, updateProfile` |
| `src/routes/items/[id]/+page.svelte` | `user` |
| `src/routes/inventory/+page.svelte` | `user` |
| `src/lib/components/ItemTable.svelte` | `user` |

Every file above must migrate: drop the `user` import, add `import { getUserState } from "$lib/auth.svelte"`, declare `const user = getUserState();` at the top of `<script>`, and update function calls (`login(email, pwd)` → `login(user, email, pwd)`, same for `register`, `logout`, `updateProfile`, `checkMe`). If grep finds more files than the table, add them too.

- [ ] **Step 2: Write failing isolation test**

Create `frontend/src/lib/auth.svelte.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { createUserState } from "./auth.svelte";

describe("auth state isolation", () => {
  it("each createUserState() call returns an independent store with full shape", () => {
    const a = createUserState();
    const b = createUserState();
    expect(a.isLoggedIn).toBe(false);
    expect(a.loading).toBe(true);
    a.data = { id: "x", email: "alice@example.com" } as any;
    a.isLoggedIn = true;
    expect(b.data).toBeNull();
    expect(b.isLoggedIn).toBe(false);
  });
});
```

(Requires Vitest setup from Task 1.8 — execute Task 1.8 BEFORE Task 1.1.)

- [ ] **Step 3: Run — should fail**

Run: `cd frontend && npm run test -- auth.svelte`
Expected: fail (`createUserState` not exported).

- [ ] **Step 4: Refactor `auth.svelte.ts` preserving the existing shape & API**

```ts
import { getContext, setContext } from "svelte";
import { goto } from "$app/navigation";
import { API_BASE_URL } from "$lib/config.js";
import type { UserRead, ProfileRead } from "$lib/types";

export interface UserState {
  data: UserRead | null;
  profile: ProfileRead | null;
  isLoggedIn: boolean;
  loading: boolean;
}

const KEY = Symbol("user-state");

export function createUserState(): UserState {
  return $state({ data: null, profile: null, isLoggedIn: false, loading: true });
}

export function provideUserState(): UserState {
  const s = createUserState();
  setContext(KEY, s);
  return s;
}

export function getUserState(): UserState {
  const ctx = getContext<UserState>(KEY);
  if (!ctx) throw new Error("getUserState() called outside <UserProvider>");
  return ctx;
}

// All existing functions accept the state explicitly. Callers migrate to:
//   const user = getUserState();
//   await checkMe(user);
export async function checkMe(user: UserState): Promise<void> { /* …same body, replace bare `user` with the param… */ }
export async function fetchProfile(user: UserState): Promise<void> { /* … */ }
export async function login(user: UserState, email: string, password: string) { /* … */ }
export async function register(user: UserState, email: string, password: string) { /* … */ }
export async function updateProfile(user: UserState, profileData: Partial<Pick<ProfileRead, "display_name" | "is_private">>) { /* … */ }
export async function logout(user: UserState) { /* … */ }
```

> **Do NOT** keep a module-level `export const user = $state(...)` — that is precisely the SSR leak. Every consumer must call `getUserState()` inside a component (which is the only place context is available).

- [ ] **Step 5: Wire provider in root layout**

In `frontend/src/routes/+layout.svelte` (top of `<script>`):

```svelte
<script lang="ts">
  import { provideUserState, checkMe } from "$lib/auth.svelte";
  import { onMount } from "svelte";
  const user = provideUserState();
  onMount(() => { void checkMe(user); });
</script>
```

- [ ] **Step 6: Migrate every consumer found in Step 1**

For each file using `import { user, … } from "$lib/auth.svelte"`:
- Change to: `import { getUserState, login, /* etc */ } from "$lib/auth.svelte";`
- At the top of the `<script>`: `const user = getUserState();`
- Replace function calls `await login(email, pwd)` → `await login(user, email, pwd)`.

Run after each batch: `cd frontend && npm run check`. Don't move on until 0 errors.

- [ ] **Step 7: Run unit test — should pass**

Run: `cd frontend && npm run test -- auth.svelte`
Expected: pass.

- [ ] **Step 8: Manual SSR smoke**

Run: `cd frontend && npm run build && node build` then `curl --cookie a.jar http://localhost:3000/` and `curl --cookie b.jar http://localhost:3000/` with two different sessions; confirm rendered HTML does not leak the other user's email.

- [ ] **Step 9: Commit**

```bash
# Use -A on the src tree — fish/zsh need `globstar`/`shopt -s globstar` for **/*.svelte,
# and the migrated consumers (6 files: +layout, routes/auth, routes/settings,
# routes/items/[id], routes/inventory, lib/components/ItemTable) span multiple dirs.
git add -A frontend/src/
git commit -m "fix(frontend): scope auth state per request via setContext (SSR-safe)"
```

---

### Task 1.2: Atomic `current_price` update race (W2)

**Files:**
- Modify: `backend/app/prices/services.py:95-125`
- Create: `backend/tests/test_prices_race.py`

- [ ] **Step 1: Write failing concurrency test**

Create `backend/tests/test_prices_race.py`:

```python
import asyncio
from datetime import datetime, timezone

import pytest

from app.prices.services import add_price_point
from app.prices.schemas import PricePointCreate


@pytest.mark.asyncio
async def test_concurrent_add_price_point_keeps_latest(session_factory, sample_item):
    """Two parallel writes must leave item.current_price == price of latest captured_at."""
    older = PricePointCreate(source="ah", price=100, captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    newer = PricePointCreate(source="ah", price=200, captured_at=datetime(2026, 1, 2, tzinfo=timezone.utc))

    async def write(p):
        async with session_factory() as s:
            await add_price_point(s, sample_item.id, p)

    await asyncio.gather(write(newer), write(older))

    async with session_factory() as s:
        item = await s.get(type(sample_item), sample_item.id)
        assert item.current_price == 200
        assert item.last_price_at == newer.captured_at.replace(tzinfo=None)
```

(Add `session_factory` and `sample_item` fixtures to `conftest.py` if absent.)

- [ ] **Step 2: Run — should fail or be flaky**

Run: `cd backend && uv run pytest tests/test_prices_race.py -v --count=10` (requires `pytest-repeat`; if unavailable, run 10× manually).
Expected: at least 1 failure (older write wins the race).

- [ ] **Step 3: Replace check-then-update with atomic UPDATE**

In `backend/app/prices/services.py` `add_price_point`, replace the `if item.last_price_at is None or captured_at >= item.last_price_at: item.current_price = ...` block with a single UPDATE. Note: must also bump `updated_at` (original did), and the WHERE uses `<=` to match the original's `>=` semantics (newer-or-equal ts wins, matching first-write-wins on ties — preserves prior behaviour). The leading `IS NULL` branch is mandatory because Postgres returns NULL (falsy) for any comparison against NULL.

```python
from sqlalchemy import update
from app.common.time import utcnow  # or wherever utcnow lives

# captured_at is already the naive-UTC datetime computed above; alias for clarity.
ts = captured_at  # naive UTC

session.add(point)  # keep — append the price-point row

await session.execute(
    update(Item)
    .where(Item.id == item_id)
    .where((Item.last_price_at.is_(None)) | (Item.last_price_at <= ts))
    .values(
        current_price=data.price,
        last_price_at=ts,
        updated_at=utcnow(),
    )
)
await session.commit()
await session.refresh(point)
return point
```

Remove the prior in-memory `if ... item.current_price = ...` and `session.add(item)` lines.

- [ ] **Step 4: Run race test 10× — should pass**

Run: `cd backend && uv run pytest tests/test_prices_race.py -v` (×10).
Expected: 10/10 pass.

- [ ] **Step 5: Run full suite**

Run: `cd backend && uv run pytest -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/prices/services.py backend/tests/test_prices_race.py
git commit -m "fix(prices): atomic current_price update guarded by last_price_at"
```

---

### Task 1.3: Stop swallowing `AppError` in `get_inventory_for_recipe` (W3)

**Files:**
- Modify: `backend/app/user_inventory/services.py:76-102`
- Create: `backend/tests/test_user_inventory_for_recipe.py`

**Function has TWO silent-`{}` exits — both must be fixed:**
1. Line 81-82: `if item_id not in all_recipes: return {}` — caller cannot distinguish "no recipe" from "unknown item". Convert to `NotFoundError` when the *item* itself doesn't exist; return `{}` only when the item exists but has no recipe (legitimate leaf).
2. Line 87-88: `except AppError: return {}` — swallows real failures from `build_craft_tree`. Let it bubble.

- [ ] **Step 1: Write failing test (must hit `build_craft_tree`, not the recipe short-circuit)**

```python
import pytest
import uuid

from app.config.exceptions import AppError, NotFoundError
from app.user_inventory.services import get_inventory_for_recipe


@pytest.mark.asyncio
async def test_for_recipe_raises_not_found_for_unknown_item(session):
    """Unknown item_id (no row in items table) -> NotFoundError, not silent {}."""
    with pytest.raises(NotFoundError):
        await get_inventory_for_recipe(session, user_id=uuid.uuid4(), item_id=10**9)


@pytest.mark.asyncio
async def test_for_recipe_propagates_app_error_from_broken_recipe(
    session, item_with_broken_recipe, sample_user
):
    """A recipe referencing an item missing from `items` must surface as AppError,
    not be hidden as {}. Build the fixture by inserting an Item, a Recipe whose
    ingredient item_id points to a deleted row — build_craft_tree will raise."""
    with pytest.raises(AppError):
        await get_inventory_for_recipe(
            session, user_id=sample_user.id, item_id=item_with_broken_recipe.id
        )


@pytest.mark.asyncio
async def test_for_recipe_returns_empty_for_leaf_item(session, sample_leaf_item, sample_user):
    """Item exists but has no recipe -> legitimate empty dict (not an error)."""
    result = await get_inventory_for_recipe(
        session, user_id=sample_user.id, item_id=sample_leaf_item.id
    )
    assert result == {}
```

Add `item_with_broken_recipe` and `sample_leaf_item` fixtures to `conftest.py`.

- [ ] **Step 2: Run — should fail**

Run: `cd backend && uv run pytest tests/test_user_inventory_for_recipe.py -v`
Expected: 2 failures (no exceptions raised), 1 pass (leaf case already returns `{}`).

- [ ] **Step 3: Patch service**

In `backend/app/user_inventory/services.py`, replace the existing `load_all_recipes(...) → try/except AppError → return {}` block (~lines 78-91 in the live file). Use a cheap `session.get(Item, item_id)` for the existence check instead of loading the entire items table:

```python
item = await session.get(Item, item_id)
if item is None:
    raise NotFoundError("Item not found")

all_recipes = await load_all_recipes(session)
if item_id not in all_recipes:
    return {}  # legitimate: item is a leaf / unrecipeable

all_items = await load_all_items(session)
tree = build_craft_tree(item_id, 1, {}, all_recipes, all_items)  # AppError propagates
```

`Item` is already imported in the file. Drop the `try/except AppError: return {}` wrapper entirely — the router-level exception handlers will format `AppError` correctly.

- [ ] **Step 4: Run test — should pass**

Run: `cd backend && uv run pytest tests/test_user_inventory_for_recipe.py -v`
Expected: 3 passed.

- [ ] **Step 5: Run full suite**

Run: `cd backend && uv run pytest -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/user_inventory/services.py backend/tests/test_user_inventory_for_recipe.py backend/tests/conftest.py
git commit -m "fix(user_inventory): raise NotFoundError for unknown item, propagate AppError"
```

---

### Task 1.4: Bounded recursion in `RecipeTree.svelte` + extract `computeNodeCost` (W5 + M2)

**Files:**
- Create: `frontend/src/lib/crafting.ts`
- Create: `frontend/src/lib/crafting.test.ts`
- Modify: `frontend/src/lib/components/crafting/RecipeTree.svelte:19-33`
- Modify: `frontend/src/routes/items/[id]/+page.svelte:36-52`

- [ ] **Step 1: Write failing tests**

Create `frontend/src/lib/crafting.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { computeNodeCost, MAX_RECIPE_DEPTH } from "./crafting";

describe("computeNodeCost", () => {
  it("returns leaf cost for non-recipe nodes", () => {
    expect(computeNodeCost({ price: 5, children: [] }, 1)).toBe(5);
  });

  it("sums child costs scaled", () => {
    const tree = { price: 0, children: [{ price: 10, qty: 2, children: [] }] };
    expect(computeNodeCost(tree, 1)).toBe(20);
  });

  it("throws when depth exceeds MAX_RECIPE_DEPTH (cycle protection)", () => {
    const node: any = { price: 0, qty: 1, children: [] };
    node.children.push(node); // cycle
    expect(() => computeNodeCost(node, 1)).toThrowError(/depth/i);
  });
});
```

- [ ] **Step 2: Run — should fail (module doesn't exist)**

Run: `cd frontend && npm run test -- crafting`
Expected: fail.

- [ ] **Step 3: Implement `crafting.ts`**

```ts
export const MAX_RECIPE_DEPTH = 32;

export type RecipeNode = {
  price?: number | null;
  qty?: number;
  children?: RecipeNode[];
};

export function computeNodeCost(node: RecipeNode, scale: number, depth = 0): number {
  if (depth > MAX_RECIPE_DEPTH) {
    throw new Error(`computeNodeCost: recipe depth exceeded ${MAX_RECIPE_DEPTH} (cycle?)`);
  }
  const children = node.children ?? [];
  if (children.length === 0) {
    return (node.price ?? 0) * scale;
  }
  let total = 0;
  for (const c of children) {
    total += computeNodeCost(c, scale * (c.qty ?? 1), depth + 1);
  }
  return total;
}
```

- [ ] **Step 4: Run tests — should pass**

Run: `cd frontend && npm run test -- crafting`
Expected: 3 pass.

- [ ] **Step 5: Replace duplicates**

In `RecipeTree.svelte` and `items/[id]/+page.svelte`, delete the local `computeNodeCost` and:

```ts
import { computeNodeCost } from "$lib/crafting";
```

- [ ] **Step 6: Run `npm run check`**

Run: `cd frontend && npm run check`
Expected: 0 errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/crafting.ts frontend/src/lib/crafting.test.ts frontend/src/lib/components/crafting/RecipeTree.svelte frontend/src/routes/items/[id]/+page.svelte
git commit -m "refactor(crafting): extract computeNodeCost with depth guard (DRY)"
```

---

### Task 1.5: Fix `UserRead` OpenAPI drift (W6)

**Files:**
- Modify: `backend/app/auth/schemas.py:8-15`
- Create: `backend/tests/test_user_read_schema.py`

- [ ] **Step 1: Write failing schema test**

```python
from fastapi.testclient import TestClient

from app.main import app


def test_openapi_user_read_matches_runtime():
    client = TestClient(app)
    spec = client.get("/openapi.json").json()
    user_read = spec["components"]["schemas"]["UserRead"]["properties"]
    # The runtime serializer strips these; OpenAPI must agree
    for stripped in ("is_superuser", "is_active", "is_verified"):
        assert stripped not in user_read, f"{stripped} leaked into OpenAPI"
    assert "email" in user_read
    assert "id" in user_read
```

- [ ] **Step 2: Run — should fail**

Run: `cd backend && uv run pytest tests/test_user_read_schema.py -v`
Expected: fail (fields present in OpenAPI).

- [ ] **Step 3: Replace `@model_serializer` strip with explicit schema**

> **DO NOT** swap `BaseUserCreate`/`BaseUserUpdate` for plain `BaseModel` — fastapi-users' register/update flow relies on those base classes' fields (`password`, optional `is_active`/`is_superuser`/`is_verified` for admin paths). Only `UserRead` needs to change. Subclass `BaseModel` for `UserRead` (no inheritance from `BaseUser`, so the `is_*` fields never enter the schema or the OpenAPI spec). Keep `BaseUserCreate`/`BaseUserUpdate` for the other two.

In `backend/app/auth/schemas.py`:

```python
import uuid

from fastapi_users import schemas as fu_schemas
from pydantic import BaseModel, ConfigDict, EmailStr


class UserRead(BaseModel):
    """Hand-rolled to suppress is_active / is_verified / is_superuser leakage.
    Intentionally NOT inheriting fu_schemas.BaseUser — fastapi-users only needs
    response_model to be a valid pydantic schema; it does not require subclassing."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr


class UserCreate(fu_schemas.BaseUserCreate):
    pass


class UserUpdate(fu_schemas.BaseUserUpdate):
    pass
```

After applying, manually verify `/api/users/me` and `/api/auth/register` still return 200 with the expected JSON shape (just `id` + `email`).

- [ ] **Step 4: Run test — should pass**

Run: `cd backend && uv run pytest tests/test_user_read_schema.py -v`
Expected: pass.

- [ ] **Step 5: Regenerate frontend API types**

Backend must be running locally first (`cd backend && uv run fastapi dev app/main.py`), then:
Run: `cd frontend && npm run gen:types` (the actual script name in `package.json`; it calls `openapi-typescript http://localhost:8000/openapi.json -o src/lib/api.d.ts`).
Then: `cd frontend && npm run check`
Expected: 0 errors after type regen.

- [ ] **Step 6: Commit**

```bash
git add backend/app/auth/schemas.py backend/tests/test_user_read_schema.py frontend/src/lib/api.d.ts
git commit -m "fix(auth): align UserRead OpenAPI schema with runtime serialization"
```

---

### Task 1.6: Atomic `DELETE WHERE` in `unfollow_item` (W7)

**Files:**
- Modify: `backend/app/user_items/services.py:82-94`
- Create: `backend/tests/test_user_inventory_unfollow.py`

- [ ] **Step 1: Write failing test**

> The rest of `user_items/services.py` uses `session.exec(...)` (SQLModel async). Keep `exec` here too so we don't mix APIs, and spy on `exec` (not `execute`).

```python
import pytest
from sqlmodel import delete
from app.user_items.services import unfollow_item


@pytest.mark.asyncio
async def test_unfollow_is_idempotent_and_single_roundtrip(session, sample_user, sample_item, mocker):
    spy = mocker.spy(session, "exec")
    await unfollow_item(session, user_id=sample_user.id, item_id=sample_item.id)
    await unfollow_item(session, user_id=sample_user.id, item_id=sample_item.id)  # no-op
    # Expect 2 exec calls total (one DELETE per unfollow), no SELECT
    assert spy.call_count == 2
```

- [ ] **Step 2: Run — should fail**

Run: `cd backend && uv run pytest tests/test_user_inventory_unfollow.py -v`
Expected: fail (SELECT + DELETE counted; mocker may need `pytest-mock`).

- [ ] **Step 3: Replace with atomic DELETE**

```python
from sqlmodel import and_, delete
from app.user_items.models import UserItem

async def unfollow_item(session, user_id, item_id) -> None:
    await session.exec(
        delete(UserItem).where(
            and_(UserItem.user_id == user_id, UserItem.item_id == item_id)
        )
    )
    await session.commit()
```

- [ ] **Step 4: Run test — should pass**

Run: `cd backend && uv run pytest tests/test_user_inventory_unfollow.py -v`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/user_items/services.py backend/tests/test_user_inventory_unfollow.py
git commit -m "refactor(user_items): atomic DELETE WHERE in unfollow_item"
```

---

### Task 1.7: Singleton `httpx.AsyncClient` in Discord bot (W8)

**Files:**
- Create: `discord_bot/cogs/_http.py`
- Modify: `discord_bot/cogs/prices.py`
- Modify: `discord_bot/bot.py` (lifecycle)

- [ ] **Step 1: Write failing test**

`discord_bot/tests/test_http_singleton.py`:

```python
from discord_bot.cogs._http import get_http_client

def test_get_http_client_returns_same_instance():
    a = get_http_client()
    b = get_http_client()
    assert a is b
```

- [ ] **Step 2: Run — should fail**

Run: `cd discord_bot && uv run pytest tests/test_http_singleton.py -v`
Expected: fail (module missing).

- [ ] **Step 3: Implement singleton**

`discord_bot/cogs/_http.py`:

```python
import httpx

_client: httpx.AsyncClient | None = None

def get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=10.0)
    return _client


async def close_http_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
```

- [ ] **Step 4: Refactor `prices.py`**

Replace every `async with httpx.AsyncClient(...) as client:` with `client = get_http_client()` (no `async with`).

- [ ] **Step 5: Close on bot shutdown**

In `discord_bot/bot.py`, add an `on_close` / `setup_hook` cleanup that calls `await close_http_client()`.

- [ ] **Step 6: Run tests**

Run: `cd discord_bot && uv run pytest -v`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add discord_bot/cogs/_http.py discord_bot/cogs/prices.py discord_bot/bot.py discord_bot/tests/test_http_singleton.py
git commit -m "perf(discord_bot): share singleton httpx.AsyncClient across cogs"
```

---

### Task 1.8: Vitest setup + first lib tests (W9)

**Files:**
- Create: `frontend/vitest.config.ts`
- Modify: `frontend/package.json` (scripts + devDeps)
- Create: `frontend/src/lib/currency.test.ts`

- [ ] **Step 1: Install vitest**

Run: `cd frontend && npm install -D vitest @vitest/ui jsdom @testing-library/svelte @testing-library/jest-dom`
Expected: install succeeds.

- [ ] **Step 2: Create vitest config**

`frontend/vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";
import { svelte } from "@sveltejs/vite-plugin-svelte";

export default defineConfig({
  plugins: [svelte({ hot: false })],
  test: {
    environment: "jsdom",
    globals: true,
    include: ["src/**/*.{test,spec}.{ts,svelte}"],
  },
});
```

- [ ] **Step 3: Add npm script**

In `frontend/package.json` `"scripts"`:

```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 4: Write a sanity test**

`frontend/src/lib/currency.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { formatCurrency } from "./currency";

describe("formatCurrency", () => {
  it("formats integers with thousand separators", () => {
    expect(formatCurrency(1234567)).toMatch(/1.234.567/);
  });

  it("handles zero", () => {
    expect(formatCurrency(0)).toMatch(/0/);
  });
});
```

- [ ] **Step 5: Run**

Run: `cd frontend && npm run test`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add frontend/vitest.config.ts frontend/package.json frontend/package-lock.json frontend/src/lib/currency.test.ts
git commit -m "test(frontend): introduce vitest + first lib tests"
```

---

### Task 1.9: Add `discord_bot` to docker-compose (W10)

**Files:**
- Modify: `infra/compose/docker-compose.dev.yml`
- Modify: `infra/compose/docker-compose.prod.yml`

- [ ] **Step 1: Write failing test**

`infra/tests/test_compose_has_discord.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
for f in infra/compose/docker-compose.dev.yml infra/compose/docker-compose.prod.yml; do
  if ! grep -qE '^\s*discord_bot:' "$f"; then
    echo "FAIL: $f missing discord_bot service"
    exit 1
  fi
done
echo OK
```

`chmod +x infra/tests/test_compose_has_discord.sh`.

- [ ] **Step 2: Run — should fail**

Run: `bash infra/tests/test_compose_has_discord.sh`
Expected: FAIL.

- [ ] **Step 3: Add service to prod compose**

```yaml
  discord_bot:
    build: ../../discord_bot
    restart: unless-stopped
    environment:
      DISCORD_TOKEN: ${DISCORD_TOKEN:?DISCORD_TOKEN is required}
      INGEST_TOKEN: ${INGEST_TOKEN:?INGEST_TOKEN is required}
      BACKEND_URL: http://backend:8000
    depends_on:
      backend:
        condition: service_started
```

- [ ] **Step 4: Add service to dev compose**

Same block, with `BACKEND_URL: http://backend:8000`.

- [ ] **Step 5: Re-run — should pass**

Run: `bash infra/tests/test_compose_has_discord.sh`
Expected: OK.

- [ ] **Step 6: Validate compose**

Run: `podman compose -f infra/compose/docker-compose.dev.yml config > /dev/null`
Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add infra/compose/docker-compose.dev.yml infra/compose/docker-compose.prod.yml infra/tests/test_compose_has_discord.sh
git commit -m "feat(infra): manage discord_bot via docker-compose"
```

---

### Sprint 1 verification

- [ ] **Backend full**

Run: `cd backend && uv run pytest -v`
Expected: all pass.

- [ ] **Frontend type + tests**

Run: `cd frontend && npm run check && npm run test`
Expected: 0 type errors, all tests pass.

- [ ] **Discord bot tests**

Run: `cd discord_bot && uv run pytest -v`
Expected: all pass.

- [ ] **Compose dry-run**

Run: `podman compose -f infra/compose/docker-compose.dev.yml config > /dev/null && podman compose -f infra/compose/docker-compose.prod.yml config > /dev/null`
Expected: both exit 0.

---

# Backlog — Medium (🟡)

These are smaller, independent items. Each follows the TDD pattern but is shorter; bundle them into a single `chore/audit-medium` branch with one commit per item.

| ID | Item | Outline |
|---|---|---|
| M1 | Shared `utcnow()` util | Create `backend/app/common/time.py:utcnow()`; replace 5 local copies; test compares return type + naive UTC. |
| M3 | Remove `@ts-nocheck` from `EChartsLineChart.svelte` | Add proper types for echarts series; `npm run check` is the test. |
| M4 | Type the `(row: any)` mapping in `items/[id]/+page.svelte:124` | Import row type from `api.d.ts`; test = `npm run check`. |
| M5 | Split `ItemTable.svelte` only if a real change needs it | Skip per chairman (debatable). Document in CONSTITUTION. |
| M6 | Restrict CORS `allow_methods` to `["GET", "POST", "PUT", "PATCH", "DELETE"]` | Test: `OPTIONS /api/items` returns Allow header without `*`. |
| M7 | Implement `lifespan` for httpx client / DB warm-up only when needed | YAGNI for now — leave no-op, document. |
| M8 | Add healthcheck to `backend` and `frontend` services in compose | curl `/api/health` and `/`; test = `podman compose config` + `podman healthcheck run`. |

Each backlog item: write a failing test (or verification script), implement, commit.

---

## Final Sprint 0+1 sanity gate

Before merging to main, from worktree:

- [ ] `cd backend && uv run pytest -v` → all green
- [ ] `cd frontend && npm run check && npm run test` → all green
- [ ] `cd discord_bot && uv run pytest -v` → all green
- [ ] `bash infra/tests/test_dockerfiles_non_root.sh`
- [ ] `bash infra/tests/test_caddy_headers.sh`
- [ ] `bash infra/tests/test_uvicorn_proxy_headers.sh`
- [ ] `bash infra/tests/test_compose_has_discord.sh`
- [ ] `podman compose -f infra/compose/docker-compose.dev.yml config > /dev/null`

Then: stop. Ask the user before pushing or merging (per project rule "NEVER `git push` bez wyraźnej instrukcji").
