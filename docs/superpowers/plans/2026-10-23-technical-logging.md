# Technical Logging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every backend log line is one JSON object on stdout, with an event name, fields and the request id, written through one helper.

**Architecture:**
- A new `app/core/logging.py` provides:
  - a JSON formatter on the root logger;
  - a thin `EventLogger` wrapper, `get_logger(__name__).info("event", **fields)`;
  - a pure ASGI `RequestIdMiddleware` that sets a `ContextVar`, echoes `X-Request-ID` and writes one `http.request` line per request.
- Uvicorn's access log is turned off, because the middleware replaces it.
- The two existing loggers (Codex icons, Google OAuth) switch to the helper.

**Tech Stack:** Python 3.13 stdlib `logging`, `contextvars` and `json`; FastAPI/Starlette ASGI; pytest with `caplog`.

**Spec:** `docs/superpowers/specs/2026-10-23-item-base-architecture-design.md`, section "Logging (`core/logging.py`)"; decision in `docs/adr/0010-two-logging-layers.md` (technical layer only; the business layer is step 3).

**Branch:** `feature/technical-logging`, cut from `main` once PR #23 and `docs/adr` have merged. If they have not, cut it from `docs/adr`.

## Global Constraints

- No new dependency: stdlib only (ADR-0010 rejects structlog and python-json-logger).
- **Line keys, in this order:** `ts`, `level`, `module`, `event`, `request_id`, then the event's fields. An exception goes under `exc`.
- **`ts`** is UTC ISO 8601 with milliseconds and a `Z` suffix, e.g. `2026-10-23T18:00:00.123Z`.
- **Event names** are dotted `module.verb`: `http.request`, `icons.fetch_failed`, `auth.oauth_failed`.
- **The request id** is the incoming `X-Request-ID` when it matches `^[A-Za-z0-9-]{1,64}$`, otherwise `uuid4().hex`. It is `-` outside a request.
- **Never log** character names, emails or query strings. `http.request` logs `scope["path"]` only.
- **The CLI's `print`** in `auth/cli.py` stays: it is the command's reply, not a log.
- **New setting** `log_level: str = "INFO"`, read from env `LOG_LEVEL`. Never edit `.env*` files.
- Comments and docs are in English. Commit format is `type(scope): description`.

## Review Focus

1. **A field that is not JSON-serialisable** (a `datetime`, a `UUID`, an exception object). The line is still written, with the value as `str`. Pinned in Task 1.
2. **Two concurrent requests with different ids.** Each response echoes its own id and each `http.request` line carries its own id, with no bleed through the `ContextVar`. Pinned in Task 2.
3. **An app that raises inside a request.** The `http.request` line is still written with status 500, and the request id is reset afterwards. Pinned in Task 2.
4. **A query string carrying a secret** (`/auth/callback?code=…`). The logged path has no query. Pinned in Task 2.
5. **A second call to `configure_logging`** (a reloaded `app.main` in the prod-docs test). It installs no second handler and does not remove pytest's `caplog` handler. Pinned in Task 1.

---

### Task 1: JSON formatter, EventLogger, configure_logging

**Files:**
- Create: `backend/app/core/logging.py`
- Modify: `backend/app/core/settings.py`: add `log_level: str = "INFO"` next to `sql_echo`
- Test: `backend/tests/core/test_logging.py`

**Interfaces:**
- Produces:
  - `request_id: ContextVar[str]` (default `"-"`)
  - `class JsonFormatter(logging.Formatter)`
  - `class EventLogger` with `debug/info/warning/error(event: str, **fields) -> None` and `exception(event: str, **fields) -> None`, which logs with `exc_info=True`
  - `get_logger(name: str) -> EventLogger`
  - `configure_logging(level: str = "INFO") -> None`

How the pieces fit:
- `EventLogger` calls `logging.Logger.log(level, event, extra={"fields": fields, "request_id": request_id.get()})`, so the id is captured at call time.
- `JsonFormatter` reads `record.request_id` when present and otherwise `request_id.get()`, for third-party loggers.
- It merges `record.fields` when present, and serialises with `json.dumps(..., default=str)`.
- `configure_logging`:
  - removes only the handlers it installed before, tagged by an attribute, and adds one `StreamHandler(sys.stdout)` with `JsonFormatter` to the root;
  - sets the root level;
  - for `uvicorn`, `uvicorn.error` and `uvicorn.access`, clears their handlers and sets `propagate = True`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/core/test_logging.py
def _line(call) -> dict:
    """Run call(get_logger("app.test")) with logging.getLogger("app.test") given one
    StreamHandler(io.StringIO()) + JsonFormatter, propagate=False, level DEBUG; return json.loads of the last line."""

def test_line_has_event_fields_and_request_id():
    token = request_id.set("abc-123")
    try:
        line = _line(lambda log: log.info("import.done", rows=3, connector="market"))
    finally:
        request_id.reset(token)
    assert list(line)[:5] == ["ts", "level", "module", "event", "request_id"]
    assert line["level"] == "INFO" and line["module"] == "app.test" and line["event"] == "import.done"
    assert line["request_id"] == "abc-123" and line["rows"] == 3 and line["connector"] == "market"
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z", line["ts"])

def test_request_id_outside_a_request_is_dash():
    assert _line(lambda log: log.info("x.y"))["request_id"] == "-"

def test_exception_goes_under_exc():
    def call(log):
        try:
            raise ValueError("boom")
        except ValueError:
            log.exception("x.failed", item_type=7)
    line = _line(call)
    assert line["level"] == "ERROR" and "ValueError: boom" in line["exc"] and line["item_type"] == 7

def test_unserialisable_fields_become_strings():
    when = datetime(2026, 10, 23, 18, 0)
    line = _line(lambda log: log.info("x.y", at=when, who=uuid.UUID(int=1), err=OSError("down")))
    assert line["at"] == str(when) and line["who"] == str(uuid.UUID(int=1)) and line["err"] == "down"

def test_configure_logging_is_idempotent_and_keeps_other_handlers(caplog):
    configure_logging("INFO"); configure_logging("INFO")
    ours = [h for h in logging.getLogger().handlers if isinstance(h.formatter, JsonFormatter)]
    assert len(ours) == 1
    assert caplog.handler in logging.getLogger().handlers
    assert logging.getLogger("uvicorn.access").handlers == [] and logging.getLogger("uvicorn.access").propagate
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd backend && TEST_PG_HOSTPORT=localhost:5434 uv run pytest tests/core/test_logging.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.core.logging'`.

- [ ] **Step 3: Implement `app/core/logging.py` and the `log_level` setting as in Interfaces**

The first line is the module's reason comment: `# JSON-lines logging for the whole app, configured once, with the request id from a contextvar.`

- [ ] **Step 4: Run them to verify they pass**

Run: `cd backend && TEST_PG_HOSTPORT=localhost:5434 uv run pytest tests/core/test_logging.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/logging.py backend/app/core/settings.py backend/tests/core/test_logging.py
git commit -m "feat(core): JSON-lines logging with one event helper"
```

### Task 2: Request-id middleware, wiring, uvicorn access log off

**Files:**
- Modify: `backend/app/core/logging.py`: add `RequestIdMiddleware`
- Modify: `backend/app/main.py`:
  - call `configure_logging(settings.log_level)` before the app is built;
  - call `app.add_middleware(RequestIdMiddleware)` **after** the CORS middleware, so it is the outermost layer.
- Modify: `backend/app/auth/cli.py`: call `configure_logging(settings.log_level)` at the start of `main()`.
- Modify: `infra/compose/docker-compose.dev.yml:25`, `infra/compose/docker-compose.prod.yml:23` and `backend/Dockerfile:26`: add `--no-access-log` to each `uvicorn` command.
- Test: `backend/tests/core/test_request_id.py`

**Interfaces:**
- Consumes: `request_id`, `get_logger` from Task 1.
- Produces: `class RequestIdMiddleware` with `__init__(self, app)` and `async __call__(self, scope, receive, send)`. It is a pure ASGI middleware.

How the middleware behaves:
- A non-`http` scope passes straight through.
- For `http`:
  - it picks the id and sets the `ContextVar`, keeping the token;
  - it wraps `send` to add `x-request-id` to `http.response.start` and to remember the status;
  - it times the call;
  - in `finally` it logs `http.request` with `method`, `path` (`scope["path"]`), `status` (500 when no response started) and `ms` (float, 1 decimal), then resets the token;
  - it re-raises any exception.

- [ ] **Step 1: Write the failing tests**

```python
# tests/core/test_request_id.py; uses the existing `client` fixture (ASGITransport over app.main.app)
async def test_valid_request_id_is_echoed(client):
    r = await client.get("/openapi.json", headers={"X-Request-ID": "abc-123"})
    assert r.headers["x-request-id"] == "abc-123"

async def test_invalid_request_id_is_replaced(client):
    r = await client.get("/openapi.json", headers={"X-Request-ID": "bad id!"})
    assert re.fullmatch(r"[0-9a-f]{32}", r.headers["x-request-id"])

async def test_request_is_logged_once_without_query(client, caplog):
    caplog.set_level("INFO")
    await client.get("/openapi.json?code=secret", headers={"X-Request-ID": "abc-123"})
    [rec] = [r for r in caplog.records if r.getMessage() == "http.request"]
    assert rec.fields == {"method": "GET", "path": "/openapi.json", "status": 200, "ms": rec.fields["ms"]}
    assert rec.request_id == "abc-123" and "secret" not in caplog.text

async def test_concurrent_requests_keep_their_own_ids(client, caplog):
    caplog.set_level("INFO")
    a, b = await asyncio.gather(
        client.get("/openapi.json", headers={"X-Request-ID": "id-a"}),
        client.get("/openapi.json", headers={"X-Request-ID": "id-b"}))
    assert (a.headers["x-request-id"], b.headers["x-request-id"]) == ("id-a", "id-b")
    assert sorted(r.request_id for r in caplog.records if r.getMessage() == "http.request") == ["id-a", "id-b"]

async def test_failing_app_still_logs_500_and_resets_id(caplog):
    async def boom(scope, receive, send): raise RuntimeError("boom")
    transport = ASGITransport(app=RequestIdMiddleware(boom), raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        await c.get("/x", headers={"X-Request-ID": "id-x"})
    [rec] = [r for r in caplog.records if r.getMessage() == "http.request"]
    assert rec.fields["status"] == 500 and rec.request_id == "id-x"
    assert request_id.get() == "-"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd backend && TEST_PG_HOSTPORT=localhost:5434 uv run pytest tests/core/test_request_id.py -v`
Expected: FAIL with `ImportError: cannot import name 'RequestIdMiddleware'`.

- [ ] **Step 3: Implement `RequestIdMiddleware` and the wiring listed under Files**

- [ ] **Step 4: Run the new tests, then the whole suite**

Run: `cd backend && TEST_PG_HOSTPORT=localhost:5434 uv run pytest tests/core -v && TEST_PG_HOSTPORT=localhost:5434 uv run pytest -q`
Expected: the 5 new tests pass, and the full suite is green.

- [ ] **Step 5: Check the real server**

Run: `cd backend && LOG_LEVEL=INFO timeout 8 uv run uvicorn app.main:app --port 8077 --no-access-log & sleep 4; curl -s -o /dev/null -H 'X-Request-ID: smoke-1' localhost:8077/openapi.json; wait`
Expected: stdout shows only JSON lines, among them one with `"event": "http.request"` and `"request_id": "smoke-1"`, and uvicorn's own startup lines as JSON with the request id `-`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/logging.py backend/app/main.py backend/app/auth/cli.py backend/tests/core/test_request_id.py \
        infra/compose/docker-compose.dev.yml infra/compose/docker-compose.prod.yml backend/Dockerfile
git commit -m "feat(core): request id middleware, one access line per request"
```

### Task 3: Switch the existing loggers, document the pattern

**Files:**
- Modify: `backend/app/inventory/icons.py:4,16,67,69,73`: `log = get_logger(__name__)`. Events:
  - `icons.path_unusable` with `item_type`;
  - `icons.no_icon_box` with `item_type`;
  - `icons.fetch_failed` with `item_type` and `error` set to `repr(e)`.
- Modify: `backend/app/auth/oauth.py:2,12,25,51`: `log = get_logger(__name__)`. Events:
  - `auth.oauth_failed` with `step="profile"`, `status=code` and `reason=body`;
  - `auth.oauth_failed` with `step="code_exchange"` and `reason=exc.detail`.
- Modify: `backend/tests/auth/test_oauth.py:153-181`: assert on the record fields instead of `caplog.text`. For example: `[rec] = [r for r in caplog.records if r.getMessage() == "auth.oauth_failed"]; assert "People API has not been used" in rec.fields["reason"]`, and the same pattern for `"invalid_grant"`.
- Modify: `CLAUDE.md`, the "Shared plumbing is in `core/`" bullet. Add "JSON-lines logging (`get_logger(__name__).info("event", **fields)`, never `print` for logs)".

**Interfaces:**
- Consumes: `get_logger` from Task 1.

- [ ] **Step 1: Change the two OAuth tests to read record fields**

- [ ] **Step 2: Run them to verify they fail**

Run: `cd backend && TEST_PG_HOSTPORT=localhost:5434 uv run pytest tests/auth/test_oauth.py -k "logs_google_reason or hides_google_text" -v`
Expected: FAIL, because no record has the message `auth.oauth_failed`.

- [ ] **Step 3: Switch `oauth.py` and `icons.py` to `get_logger` with the events under Files; update `CLAUDE.md`**

- [ ] **Step 4: Run everything**

Run: `cd backend && TEST_PG_HOSTPORT=localhost:5434 uv run pytest -q && uv run ruff check . && uv run ruff format --check . && grep -rn "logging.getLogger\|print(" app`
Expected:
- the suite is all green;
- ruff is clean;
- grep prints only `app/core/logging.py` (its own `logging.getLogger` calls) and `app/auth/cli.py` (the CLI reply).

- [ ] **Step 5: Commit**

```bash
git add backend/app/inventory/icons.py backend/app/auth/oauth.py backend/tests/auth/test_oauth.py CLAUDE.md
git commit -m "refactor(logging): icons and OAuth log JSON events"
```
