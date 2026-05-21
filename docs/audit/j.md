# Audyt — Gemini 3.1 Pro Preview (2026-05-20)

> Audyt **niedokończony** — brakuje perspektyw: second-opinion, skeptic, visionary oraz finalnej syntezy. Ten plik łączy wszystkie ukończone sekcje.

---

## 1. Kontekst projektu

### Stack
- **Backend:** Python (FastAPI, SQLModel, fastapi-users, Alembic)
- **Frontend:** TypeScript, SvelteKit 5, Tailwind CSS 4, DaisyUI 5, ECharts
- **Discord Bot:** Python, discord.py
- **Baza danych:** PostgreSQL 16
- **Infrastruktura:** Podman Compose (nie Docker), Caddy (TLS + proxy)

### Entry pointy
- **Backend:** `backend/app/main.py` (`uv run fastapi dev app/main.py` / produkcyjny kontener)
- **Frontend:** `frontend/src/` (SvelteKit, build jako node server)
- **Discord Bot:** `discord_bot/bot.py` (`uv run python bot.py`)
- **Docker/Podman:** `infra/compose/docker-compose.dev.yml` / `docker-compose.prod.yml`
- **Reverse Proxy:** `infra/caddy/Caddyfile`

### Mapa warstw i komunikacji
- **SvelteKit (UI)** ↔ backend `/api/*` po HTTP.
- **Discord Bot** → backend POST (`/api/ingest/prices`).
- **Caddy** routuje `/api/*` i `/admin*` na backend, reszta → frontend node server.
- Brak kolejek/brokerów — wszystko synchronicznie po HTTP. PostgreSQL = jedyne miejsce współdzielenia stanu.
- **Frontend State** opiera się na Svelte 5 Runes (`$state`, `$derived`), bez globalnego store.

### Stan testów i CI
- **Backend:** integracyjne `pytest` w `backend/tests/` (prawdziwa DB testowa).
- **Discord Bot:** unit testy w `discord_bot/tests/`.
- **Frontend:** brak testów; tylko `openapi-typescript` + `svelte-check` w CI.
- **CI/CD:** oddzielne workflow per moduł w `.github/workflows/`.

### Czego NIE MA
- ❌ GraphQL, gRPC
- ❌ Redis, RabbitMQ, Kafka
- ❌ React, Vue
- ❌ Zewnętrzny Watcher Daemon (usunięty — ceny dodawane przez Discord Bot)

---

## 2. Plan audytu (perspektywy i pytania)

### backend
- **Scope:** `backend/app/`, `backend/alembic/`
- **Pytania:**
  1. Czy API właściwie wykorzystuje SQLModel (N+1)?
  2. Czy obsługa błędów i walidacja outputu są poprawne?
  3. Czy transakcje są atomowe (np. `/api/ingest/prices`)?

### frontend
- **Scope:** `frontend/src/`
- **Pytania:**
  1. Czy logika UI poprawnie i bezpiecznie używa Svelte 5 runes?
  2. Czy komponenty nie łamią kontraktów z `api.d.ts`?
  3. Jak wygląda obsługa błędów auth / session expiration?

### infra
- **Scope:** `infra/`, `Makefile`, `Dockerfile`, `.github/`
- **Pytania:**
  1. Czy deployment Caddy/Podman jest bezpieczny i poprawny?
  2. Czy CI łapie realne błędy i poprawnie używa `uv`?

### discordbot
- **Scope:** `discord_bot/`
- **Pytania:**
  1. Czy async (httpx) jest poprawnie zarządzany (sesje, timeouty)?
  2. Czy błędy API są zrozumiałe dla użytkownika?

### integration
- **Scope:** `backend/app/routers/`, `frontend/src/lib/api.d.ts`, `discord_bot/cogs/`
- **Pytania:**
  1. Czy struktury API są w pełni obsługiwane przez SvelteKit i bota?
  2. Gdzie mogą wystąpić desynchronizacje?

### security
- **Scope:** Całe repo (focus: auth/authz)
- **Pytania:**
  1. Czy `/admin` i mutujące endpointy są zabezpieczone + rate-limited?
  2. Czy sekrety nie wyciekają w kodzie/logach/UI?
  3. Czy sesje cookie (fastapi-users) i JWT są bezpieczne?

### dependencies
- **Scope:** `pyproject.toml`, `package.json`, `uv.lock`
- **Pytania:**
  1. Czy biblioteki mają krytyczne CVE?
  2. Czy lockfiles / pinning są poprawne?

### code-quality
- **Scope:** Całe repo
- **Pytania:**
  1. Gdzie są god objects / spaghetti?
  2. Czy separacja warstw jest zgodna z docs?

### tester-evaluator
- **Scope:** `backend/tests/`, `discord_bot/tests/`, frontend gaps
- **Pytania:**
  1. Gdzie brakuje testów (frontend)?
  2. Czy testy backendu chronią kontrakty?

---

## 3. Backend findings (`backend/app/`)

### 1. SELECT-then-delete anti-pattern w `user_items`
W `app/user_items/services.py` `unfollow_item` najpierw pobiera relację, potem ją kasuje:
```python
result = await session.exec(select(UserItem)...)
relation = result.one_or_none()
if relation is not None:
    await session.delete(relation)
```
Łamie regułę z `docs/ai/patterns.md` ("Nigdy SELECT-then-delete"). Race-condition przy współbieżnych unfollow. Zastąpić atomowym `DELETE ... WHERE`.

### 2. Premature commits w transakcjach
- `add_price_point` (`app/prices/services.py`) commituje wewnętrznie.
- `match_or_create_item` (`app/ingest/services.py`) commituje wewnętrznie.

W `bulk_ingest` na rząd przypadają 2 commity. `rollback` cofa tylko niezacommitowany stan → jeśli `add_price_point` padnie, nowo wstawiony `Item` zostaje. Łamie atomowość i blokuje reużycie funkcji w batch.

### 3. Brak `ON DELETE CASCADE` na FK
- `UserItem.user_id`, `UserItem.item_id`
- `UserInventory.user_id`, `UserInventory.item_id`
- `PricePoint.item_id`
- `Profile.user_id`

Usunięcie `User` / `Item` (admin / GDPR) → `IntegrityError`.

### 4. Crafting calculator nie schodzi do sub-składników
W `app/crafting/calculator.py` `total_material_cost` i `has_missing_prices` patrzą tylko na top-level. Jeśli direct ingredient nie ma ceny, ale jest craftable z własnych sub-składników — kalkulator nie robi fallbacku, ustawia `has_missing_prices = True` i nie liczy zysku.

### 5. Niezgodność docs ↔ kod (`current_active_user`)
`docs/ai/patterns.md` każe importować `current_active_user, current_superuser` z `app.auth.dependencies`, ale plik definiuje tylko `current_user`. Import error dla każdego, kto pójdzie według patternsów.

### 6. Profile creation w osobnej sesji
W `app/auth/manager.py` `on_after_register` tworzy `Profile` w `async with async_session_maker()`. Jeśli aplikacja padnie po commicie usera ale przed commitem profilu → user bez profilu (łamie invariant 1-to-1).

### 7. Martwy middleware w `AdminAuth`
`SecureAdminAuth` w `app/admin_auth.py` próbuje wstrzyknąć `SessionMiddleware` przez `self.middlewares` — `sqladmin.authentication.AuthenticationBackend` tego nie obsługuje. Kod functionally dead.

---

## 4. Frontend findings (`frontend/src/`)

Frontend zmigrowany do Svelte 5 (runes), poprawnie importuje DTO z `api.d.ts`, ale fetche budują URL-e ręcznie. Brak centralnego klienta → niespójna obsługa 401.

### 🟢 Poprawna adopcja runów Svelte 5
Cały kod (`ItemTable.svelte`, `+page.svelte`) używa `$props()`, `$state`, `$derived`. Utrzymać standard.

### 🟡 Globalny `$state` z sesją userka — ryzyko wycieku SSR
`frontend/src/lib/auth.svelte.ts` eksportuje `user = $state(...)` na poziomie modułu. Przy SSR (adapter-node) moduły dzielą pamięć między żądaniami → wyciek sesji. Sugestia: Svelte Context API albo `export const ssr = false`.

### 🟠 Niespójna obsługa 401, brak interceptora
`routes/items/[id]/+page.svelte`, `ItemTable.svelte` — gdzieniegdzie `goto('/auth')`, gdzieniegdzie pusty `catch`. Sesja wygasła w tle → user widzi "nic się nie zapisuje". Sugestia: wrapper na `fetch` z globalnym handlem 401.

### 🟡 Ręczne URL-e zamiast pełnego klienta z OpenAPI
Typy z `api.d.ts`, ale ścieżki jako stringi — TS nie złapie zmiany endpointu. Sugestia: `openapi-fetch`.

---

## 5. Discord bot findings (`discord_bot/`)

### 🔴 Nowa sesja HTTP per request
`discord_bot/cogs/prices.py` (`lookup_item`, `post_price`) — `async with httpx.AsyncClient(...)` w każdej funkcji. Brak connection poolingu, TCP/TLS handshake za każdym razem. Sugestia: jeden shared `AsyncClient` powiązany z `bot.setup_hook`.

### 🟠 Brak globalnego error handlera
`discord_bot/bot.py` nie definiuje `tree.on_error` / `on_command_error`. Nieobsłużony wyjątek → user dostaje generyczne "Aplikacja nie odpowiedziała".

### 🟡 Zbyt ogólne `except (httpx.HTTPError, KeyError, ValueError)`
W `cogs/prices.py` linie ~147 i ~197 — `KeyError`/`ValueError` (błędy parsowania/logiki) są zamaskowane jako "Backend connection error". Rozdzielić.

---

## 6. Infra findings

### 🔴 Kontenery jako root
`backend/Dockerfile`, `frontend/Dockerfile`, `discord_bot/Dockerfile` — brak `USER`. Drastycznie ułatwia container escape. Dodać non-root w finalnym stage.

### 🟠 Migracje DB sklejone ze startem serwera
`infra/compose/docker-compose.prod.yml` + `backend/Dockerfile`: `sh -c "uv run alembic upgrade head && uv run uvicorn ..."`. Race przy wielu instancjach, błąd migracji blokuje serwowanie. Wydzielić init container.

### 🟡 `devDependencies` lecą na produkcję (frontend)
`frontend/Dockerfile` kopiuje całe `node_modules` bez filtra. `npm ci --omit=dev`.

### 🟡 Brak security headers w Caddy
`infra/caddy/Caddyfile` — brak HSTS, CSP, X-Frame-Options. Szczególnie podatny `/admin`.

### 💡 Kruchy wybór kontenera DB w `Makefile`
`podman exec $$(podman ps -q --filter name=db)` — łapie obcy kontener z "db" w nazwie. Użyć `$(DEV_COMPOSE) exec -T db ...`.

---

## 7. Security findings

### 🔴 Brak autoryzacji na `POST /api/ingest/prices`
`backend/app/ingest/router.py` — endpoint publiczny, każdy może bulk-insertować ceny i tworzyć itemy. API key / shared secret / login z rolą.

### 🔴 Hardcoded default secrets
`backend/app/config/settings.py` — `auth_secret` i `admin_session_secret` mają default-stringi (32 znaki). Brak `.env` na prodzie → app cicho startuje z sekretami z kodu → atakujący generuje własne JWT + sesję admina. Wymusić błąd przy braku envów.

### 🟡 Rate limiter na proxy IP
`backend/app/config/rate_limit.py` + `docker-compose.prod.yml` — uvicorn bez `--proxy-headers` / `--forwarded-allow-ips`. `slowapi.get_remote_address` widzi IP proxy → jeden user blokuje wszystkich (self-DoS).

### 🟡 CORS wildcard
`backend/app/main.py` — `allow_methods=["*"]`, `allow_headers=["*"]`. Ograniczyć do faktycznie używanych.

### 🟡 `cookie_secure=False` jako default
`backend/app/config/settings.py` + `backend/app/auth/backend.py` — domyślnie cookies bez `Secure`. Wymusić `True` dla prod.

---

## 8. Integration findings

### 🔴 Brak autoryzacji ingest (duplikat z security)
`backend/app/ingest/router.py` — `POST /api/ingest/prices` publiczny, `auto_created` pozwala tworzyć śmieciowe itemy.

### 🟠 Potencjalny INT overflow dla cen
`discord_bot/cogs/prices.py` (`addprice`) pozwala 999 999 golda ≈ ~10 mld copper. `PricePoint`/`Item` → 32-bit `INTEGER` (max ~2.14 mld). Przy cenach > 214k golda → `NumericValueOutOfRange`. `BigInteger` via `sa_column` LUB twardszy limit w bocie.

### 🟠 Duplikat profilu usera (`/api/me` vs `/api/users/me`)
`backend/app/users/router.py` + `backend/app/auth/router.py` — fastapi-users dorzuca `/users/me`, deweloper dodał własny `/me`. Wyrzucić ręczny.

### 🟡 `UserRead` — schemat OpenAPI ≠ runtime
`backend/app/auth/schemas.py` — `@model_serializer(mode="wrap")` dynamicznie usuwa `is_superuser`, `is_active` z odpowiedzi. OpenAPI o tym nie wie → `api.d.ts` deklaruje pola jako `boolean`, runtime daje `undefined`. Użyć `Field(exclude=True)`.

### 🟡 Brak grade'u "All" w bocie
Backend default `ItemGrade.ALL`, `discord_bot/cogs/prices.py` `GRADE_CHOICES` od `Basic`(0) do 11. Exact-match → user nie znajdzie itemu z `All`. Albo zmienić default na `Basic`, albo zrobić "All" jako filtr.

---

## 9. Dependencies findings

### 🔴 CVE w `pyjwt` 2.12.1 (PYSEC-2025-183)
`backend/uv.lock` — podbić pyjwt, odświeżyć lock.

### 🟡 CVE w `cookie` (GHSA-pxg6-pf52-xh8x)
Tranzytywka z `@sveltejs/kit`. `npm audit fix` + bump SvelteKita.

### 💡 Stare paczki Python
`certifi` (2026.4.22 vs 2026.5.20), `greenlet`, `wtforms`, `yarl`. `certifi` ważne dla TLS CA chain.

### 💡 Stary frontend toolchain
`@sveltejs/kit` 2.57.1→2.60.1, Vite, Tailwind, ECharts (czeka na v6.1 — major).

---

## 10. Code quality findings

### 🔴 God function — cała baza do RAM
`backend/app/crafting/services.py` (`load_all_recipes`, `load_all_items`) ładuje wszystkie itemy/przepisy do dict-ów. `calculate` i `list_summaries` operują na in-memory mapach. Tysiące itemów → RAM eksploduje. Rewrite na Recursive CTE per `item_id` lub invalidowany cache.

### 🟠 Skopiowana logika drzewa craftingu
`frontend/src/routes/items/[id]/+page.svelte:36` + `frontend/src/lib/components/crafting/RecipeTree.svelte:19` — `computeNodeCost(node, scale)` skopiowane. Trzeci wariant: `sumLabour` w `RecipeCard.svelte`. Wyekstrahować do `$lib/crafting.ts`.

### 🟠 Duplikacja fixture'ów w testach
`backend/tests/test_*.py` — async `db_session()` skopiowany niemal w każdym pliku. Do `conftest.py`.

### 🟠 `utcnow()` skopiowane 5x
`backend/seed.py:17`, `backend/app/items/models.py:7`, `profiles/models.py:7`, `user_items/models.py:7`, `prices/models.py:6`. Do `app/utils/datetime.py`.

### 🟡 Dead code w `admin_auth.py:51-69`
`SecureAdminAuth` z `SessionMiddleware` w `__init__` — sqladmin tego nie podpina. Iluzja bezpieczeństwa. Usunąć, ustawić sesję na poziomie głównej instancji FastAPI.

### 💡 Hardcoded `CATEGORIES`/`GRADES` w komponentach
`frontend/src/lib/components/ItemTable.svelte:34`, `frontend/src/routes/inventory/+page.svelte:10` — lokalne tablice. Do `$lib/constants.ts` lub endpoint w backendzie.

---

## 11. Tester / evaluator findings

### 🔴 Zero testów frontendu
`frontend/` — brak Vitest, Playwright, brak plików testowych. Każdy refactor = lotto. Wprowadzić Vitest (unit) + Playwright (e2e).

### 🟠 Zero coverage dla `AdminAuth`
`backend/app/admin_auth.py` — `login/logout/authenticate` (sqladmin) na 0%. Krytyczne dla `/admin`. Dopisać testy z mockowanym Request.

### 🟡 Duplikacja `db_session` w 6 plikach
`backend/tests/test_*.py`. Do `conftest.py` (już zgłoszone w code-quality).

### 🟡 DeprecationWarnings z SQLModel
`backend/app/ingest/services.py:44`, `backend/app/user_inventory/services.py:62`, i inne — `.execute()` zamiast `.exec()`. Setki ostrzeżeń zaśmiecają CI.

### 🟡 Brak `pytest-cov` w bocie
`discord_bot/pyproject.toml`, `discord_bot/bot.py` — sam plik bota nieprzetestowany (testowany tylko cog `prices`). Dodać `pytest-cov` + test rejestracji.

### 💡 Dead schema `UserItemRead`
`backend/app/user_items/schemas.py` — Pydantic model nieużywany nigdzie. Usunąć.

---

## 12. Status

**Ukończone perspektywy:** backend, frontend, discordbot, infra, security, integration, dependencies, code-quality, tester-evaluator.

**Pominięte (puste pliki):** second-opinion, skeptic, visionary, synthesis.

Ostatnia aktywność: 2026-05-21 07:40 (tester-evaluator).
