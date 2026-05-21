# Synthesis — Audyt ArcheRage Market Tracker

Auditor: Opus 4.7 + 12 subagentów (równolegle + second-opinion)
Worktree: `audit-opus-4.7-20260520-2220` (branch `audit/opus-4.7-20260520-2220`)
Base: `main @ d0175bf`
Data: 2026-05-20

> Łącznie raporty mają **2333 linii** i ~**150 findings**. Synteza poniżej destyluje najważniejsze, wzorce powtarzające się ≥2× oraz konflikty między perspektywami. Second-opinion już zrobił rygorystyczny re-rank; ta synteza idzie krok dalej — agreguje wnioski i daje roadmapę.

## TL;DR — top 10 (posortowane priorytetowo)

| # | Sev | Issue | Skąd | Effort |
|---|-----|-------|------|--------|
| 1 | 🔴 | Anonimowy `/api/ingest/prices` + slowapi key na connection IP = jeden globalny bucket dla wszystkich klientów za Caddy | security SEC-001/002/010/014, integration, skeptic SKE-009, discord | ~30 min (token + key_func) |
| 2 | 🔴 | Containers run as root (backend, frontend, discord_bot) — brak `USER` | infra ×3, security SEC-009 | 15 min |
| 3 | 🔴 | Caddyfile bez nagłówków bezpieczeństwa (HSTS/CSP/X-Frame-Options/nosniff) + Caddy admin API on | infra, security SEC-004, second-opinion add | 30 min |
| 4 | 🔴 | `auth_secret` używany dla JWT + reset + verification — single key compromise = full ATO | security SEC-003 | 15 min (split secrets) |
| 5 | 🔴 | Brak rate-limit na `/auth/login`, `/auth/register`, `/auth/forgot-password` + enumeracja | security SEC-006/011 | 30 min |
| 6 | 🔴 | Swagger/ReDoc/OpenAPI exposed unauth w prod (endpoint enumeration) | security SEC-005 | 5 min (`docs_url=None` + remove Caddy handle) |
| 7 | 🟠 | PyJWT 2.12.1 ma znaną CVE — łatka dostępna | dependencies | 5 min (bump) |
| 8 | 🟠 | Brak obsługi 429/5xx + retry w frontendzie i bocie | frontend, discord, code-quality, integration, tester | 1–2h |
| 9 | 🟠 | Brak frontend tests (svelte-check ≠ test) | tester TST-007, visionary #11 | 2h (Vitest na lib) |
| 10 | 🟡 | Naive UTC w DB jako norma — dług TZ na 2 lata | skeptic SKE-001, backend, second-opinion | wielogodzinny refactor (deferowany) |

## Wzorce powtarzające się (≥2 subagentów = wysoka pewność)

Najsilniejsze sygnały — to są pewniaki:

| Wzorzec | Złapali | Lokalizacja |
|---|---|---|
| **Anonimowy ingest + globalny bucket** | security, integration, backend, skeptic, discord, second-opinion | `app/ingest/*`, `app/config/rate_limit.py` |
| **Brak USER w Dockerfile** | infra, security | wszystkie 3 Dockerfile |
| **Brak nagłówków w Caddyfile** | infra, security | `infra/caddy/Caddyfile` |
| **Brak 429/5xx handling** | frontend, discord, code-quality, integration | bot + auth.svelte.ts + ItemTable |
| **Duplikat `authentication_backend`** | backend, code-quality | `backend/app/admin_auth.py:46, 67` (dead code) |
| **Watcher daemon martwe referencje** | code-quality, skeptic | `addon/pricetracker/TESTING.md` |
| **ItemGrade enum drift (frontend vs schema)** | integration, frontend | komponenty frontu |
| **`any` w price-history mapowaniu** | frontend, code-quality | `items/[id]/+page.svelte:124` |
| **Brak testów concurrent / failure-path** | tester TST-002/003/005, backend | atomic price update, session.rollback, inventory upsert |
| **Frontend totalnie bez testów** | tester, visionary, code-quality | `frontend/` |

## Krytyczne — natychmiastowa akcja (🔴 łącznie)

| ID | Issue | Plik | Effort | Eliminuje |
|----|-------|------|--------|-----------|
| **A** | Wprowadź `INGEST_TOKEN` + Bearer w bocie, `source: Literal["ah"]` | `app/ingest/{router,services,schemas}.py`, `discord_bot/cogs/prices.py` | 30 min | SEC-002, SEC-010, SEC-014, SKE-009 |
| **B** | Uvicorn `--proxy-headers --forwarded-allow-ips`, slowapi key_func z X-Forwarded-For; slowapi na `/auth/*` (5/min login, 5/h register/forgot) | `app/main.py`, `app/config/rate_limit.py`, `app/auth/router.py`, prod compose | 1h | SEC-001, SEC-006, SEC-011 |
| **C** | Dockerfile non-root (`useradd app && USER app` w 3 plikach) | `backend/Dockerfile`, `frontend/Dockerfile`, `discord_bot/Dockerfile` | 15 min | SEC-009, infra Critical×3 |
| **D** | Caddy `header { ... }` block + `admin off` + usuń `/docs` handle | `infra/caddy/Caddyfile`, `app/main.py` `FastAPI(docs_url=None,...)` w prod | 30 min | SEC-004, SEC-005, infra Critical+High |
| **E** | Split secrets: `RESET_TOKEN_SECRET`, `VERIFICATION_TOKEN_SECRET` (+ extend `validate_secrets`) | `app/auth/manager.py`, `app/config/settings.py`, `.env.example`, prod compose | 15 min | SEC-003 |
| **F** | PyJWT bump | `backend/pyproject.toml` | 5 min | dependencies CVE |
| **G** | Usuń duplikat `authentication_backend = AdminAuth(...)` (linia 46), pozostaje SecureAdminAuth (linia 67) | `backend/app/admin_auth.py` | 2 min | code-quality 🔴 |
| **H** | Fix `.env.example` ADMIN_SESSION_SECRET (31→32+ znaków) | `.env.example:11` | 1 min | SEC-007/018 |

Suma: **~3h pracy = eliminacja ~15 findings, w tym wszystkich 🔴 z security i infra.**

## Wysokie (🟠) — kolejny sprint

| ID | Issue | Plan | Effort |
|----|-------|------|--------|
| I | Frontend 429/5xx handler + retry w bocie | `fetchWithRetry()` helper w lib + tenacity w bocie | 2h |
| J | Brak frontend testów (TST-007) | Vitest na `lib/{auth,currency,crafting}.ts` | 2h |
| K | Discord bot — singleton httpx client + per-user cooldown + on_app_command_error | refactor `cogs/prices.py` | 1h |
| L | Watcher / Lua addon dead refs (TESTING.md + nie-folio wersje) | przenieś `pricetracker{,_1..3}/` do `archive/` lub usuń; fix TESTING.md | 30 min |
| M | Race + `.one_or_none()` w `match_or_create_item` | use ON CONFLICT DO UPDATE z `set_={}` + `one_or_none()` fallback | 30 min |
| N | Rozszerzyć `test_consistency.py` (source='ah' end-to-end: seed + bot + frontend) | nowe testy | 1h |
| O | `match_or_create_item` race + concurrent `current_price` test | `asyncio.gather()` test | 1h |
| P | API.d.ts drift guard w CI | regeneruj api.d.ts, `git diff --exit-code` | 30 min |
| Q | Frontend Grade enum SSOT (current_price=null handling, `Grade.All` vs `Basic`) | jeden export z `lib/grades.ts` + użycie typu z api.d.ts | 1h |

## Konflikty opinii — werdykty (z second-opinion)

| Konflikt | Subagent A | Subagent B | Werdykt |
|---|---|---|---|
| Stack: uprościć vs rozbudować | skeptic (SKE-003–SKE-006) — wyrzuć fastapi-users/SQLModel | visionary (#2,3,5,7,8) — dodaj TimescaleDB/tRPC/TanStack | **skeptic dla MVP**, nie dodawaj warstw |
| `current_price` denormalizacja | backend 💡 — działa | skeptic SKE-008 — usuń | **zachowaj** + dodaj test (TST-002) |
| Ingest tokeny | security SEC-002 / skeptic SKE-009 / visionary #9 — kolejka? | — | **token (HMAC) wystarczy**, no message broker |
| Lua addon | skeptic — archive | visionary — universal multi-game | **archive**, multi-game to over-design |
| Frontend testing | tester — gap | visionary — Vitest+Playwright | **Vitest na lib teraz**, Playwright później |

## Przesadzone (downgraded przez second-opinion)

- **Visionary "Real-time WS/SSE"** 🔴→💡 (skala projektu: ~5 użytkowników)
- **Visionary "TimescaleDB"** 🔴→drop (29 itemów × 30 dni, plain Postgres + index wystarczy)
- **Visionary "TanStack Query"** 🔴→drop (SvelteKit `load()` jest wbudowany)
- **Visionary "tRPC"** 🟠→drop (CI guard na api.d.ts rozwiązuje drift)
- **Backend "match_or_create_item race"** 🔴→🟡 (UniqueConstraint chroni, `.one_or_none()` hygiene)
- **Code-quality "God objects"** 🟠→🟡 (367 LOC w SvelteKit z styles to nie god object)
- **Security "CORS allow_methods=*"** 🟡→💡 (z konkretnymi origins jest OK per CORS spec)
- **Dependencies "asyncpg+psycopg redundant"** 🟡→drop (standardowy pattern dla async runtime + sync alembic)

## Top 3 quick wins (low effort, high impact)

1. **PyJWT bump** (5 min) — eliminuje CVE [dependencies]
2. **Usuń duplikat `authentication_backend`** (2 min) — eliminuje 🔴 code-quality + backend 💡
3. **Fix `.env.example` ADMIN_SESSION_SECRET 31→32 chars** (1 min) — eliminuje boot crash przy copy-paste onboardingu

## Long-term roadmap (pogrupowane)

### Q3 — Hardening (po sprincie krytycznym)
- CSRF na state-changing endpoints (SEC-012)
- sqladmin rate-limit + IP allowlist (SEC-013)
- enumeration mask na `/register` i `/forgot-password` (SEC-011)
- structured logging zamiast `print()` (SEC-015)
- max-past clamp na ingest ts (SEC-021)
- multi-stage Docker builds (-60% image size; infra)

### Q4 — Auth/Stack debt
- Custom auth ~80 LOC (zastępuje fastapi-users) — rozwiązuje SEC-003 + SKE-004 (jeśli zespół chętny)
- Rozważ SQLAlchemy 2.0 + Pydantic zamiast SQLModel (SKE-005)
- Aware UTC end-to-end (SKE-001) — dług TZ
- pgbouncer + 2+ workers (visionary #7)

### Q1 next year — Observability + DX
- OpenTelemetry tracing (visionary #8)
- frontend Playwright E2E (po Vitest)
- Renovate bot / Dependabot grupowy
- `.dockerignore` everywhere (second-opinion add)

### Decline / nie rób
- TimescaleDB, tRPC, TanStack Query, Cloudflare Workers Discord bot, ML spike detection, multi-tenant
- `current_price` rewrite (działa, atomic, testowane → zachowaj)
- migracja na docker compose (jeśli zespół wybrał podman świadomie)

## Health snapshot

| Domena | Status | Komentarz |
|---|---|---|
| Backend logika | 🟢 Solidna | Wzorce konsekwentne; per-domain działa; cycle protection w crafting |
| Frontend | 🟡 Dobre, ale gap testów | Idiomatyczne runes; brak 429 handling; SSR fetch top-level |
| Infra | 🟠 Działa, ale niezahartowane | Caddy headers, USER, dev DB binding — wszystko adresowalne w 1 sprincie |
| Security | 🟠 Zero RCE/SQLi (bandit clean), ale designu brakuje | Anonymous ingest + key reuse to faktyczne wektory |
| Dependencies | 🟢 Czyste poza PyJWT CVE | Brak unused, stack nowoczesny |
| Code quality | 🟢 Z drobnymi długami | Brak ESLint/Ruff config w niektórych miejscach |
| Testy backend | 🟡 Dobre, ale luki na concurrent/failure | Invariants pokryte 4/7 |
| Testy frontend | 🔴 Zero | Vitest setup pilny |

## Final note

Projekt jest w lepszym kondycji niż statystyczny single-dev side-project. Główne ryzyko nie jest w kodzie — jest w *trust boundaries* (anonymous ingest, global rate-limit, root containers). **~3 godziny pracy na krytyczne fixy A–H eliminuje >50% wszystkich findings**. Reszta to dług który można amortyzować przez kwartały.

Discipline > perfection.
