# Audyt projektu — ArcheRage Market Tracker
# Model: opencode
# Data: 2026-05-21_07:35

---


================================================================================
# SOURCE: audit/00-context.md
================================================================================

# Audit Context — ArcheRage Market Tracker

## Stack

| Layer | Technology | Version |
|---|---|---|
| Backend | FastAPI + SQLModel + Alembic | Python 3.13 |
| Frontend | SvelteKit 5 (runes) + Tailwind 4 + DaisyUI 5 | Node 22 |
| Database | PostgreSQL 16 (alpine) | — |
| Bot | discord.py + httpx | Python 3.13 |
| Infra | Podman Compose + Caddy 2 | — |
| Package mgr | uv (backend, bot), npm (frontend) | — |

## Entry Points

| Layer | Entry | Command |
|---|---|---|
| Backend | `backend/app/main.py` | `uv run fastapi dev app/main.py` |
| Frontend | `frontend/src/routes/+page.svelte` | `npm run dev` |
| Bot | `discord_bot/bot.py` | `uv run python bot.py` |
| DB | PostgreSQL 16 | `podman compose up db` |
| Reverse proxy | `infra/caddy/Caddyfile` | Caddy in prod compose |
| Seed | `backend/seed.py` | `make seed` |
| Migrations | `backend/alembic/` | `make migrate` |

## Layer Map & Communication

```
┌──────────────┐    HTTP POST     ┌──────────────┐
│  Lua Addon   │ ──────────────►  │   Backend    │
│  (player PC) │  /api/ingest/    │  (FastAPI)   │
└──────────────┘    prices        └──────┬───────┘
                                         │
┌──────────────┐    HTTP (cookie)        │ SQLModel
│  Frontend    │ ◄──────────────────────►│ (asyncpg)
│  (SvelteKit) │    /api/*               │
└──────────────┘                         │
                                  ┌──────┴───────┐
┌──────────────┐    HTTP          │  PostgreSQL  │
│ Discord Bot  │ ──────────────►  │     16       │
│ (discord.py) │  /api/ingest/    └──────────────┘
└──────────────┘    prices
```

- Frontend → Backend: REST API via `/api/*` with JWT cookie auth
- Bot → Backend: REST API via `/api/ingest/prices` (same endpoint as addon)
- Backend → DB: asyncpg (runtime), psycopg (alembic migrations)
- Caddy: TLS termination, routes `/api/*` + `/admin*` → backend, rest → frontend

## Tests & CI

| Component | Tests | CI |
|---|---|---|
| Backend | 12 test files, pytest-asyncio, real PostgreSQL | ✅ GitHub Actions (lint + test + alembic check) |
| Frontend | None | ✅ svelte-check only |
| Discord bot | 1 test file | ✅ GitHub Actions (lint + test) |
| E2E | None | ❌ |
| Docker build | — | ✅ GitHub Actions (build only, no push) |

## What Does NOT Exist

- No e2e / integration tests across layers
- No frontend unit tests
- No monitoring / logging infrastructure (beyond Python logging)
- No message broker / queue (direct HTTP only)
- No CDN / asset optimization
- No CI/CD deployment pipeline (manual deploy implied)
- No backup strategy for PostgreSQL
- No health check endpoints (beyond compose pg_isready)


================================================================================
# SOURCE: audit/01-plan.md
================================================================================

# Audit Plan — Subagent Scopes

## 1. Backend (`backend/`)

**Scope:**
- `backend/app/` — all domain modules (models, schemas, services, routers)
- `backend/app/config/` — db, settings, rate_limit, exceptions
- `backend/app/auth/` — fastapi-users wiring
- `backend/app/admin.py`, `backend/app/admin_auth.py`
- `backend/seed.py`
- `backend/alembic/` — migrations
- `backend/tests/`
- `backend/pyproject.toml`, `backend/Dockerfile`

**Out of scope:** frontend, discord_bot, infra

**Key questions:**
1. Czy modele SQLModel są spójne z migracjami Alembic?
2. Czy serwisy poprawnie obsługują transakcje (rollback, commit)?
3. Czy rate limiting jest właściwie skonfigurowany i chroni przed abuse?
4. Czy testy pokrywają krytyczne ścieżki (ingest, inventory, crafting)?
5. Czy są problemy z wydajnością zapytań (N+1, brak indeksów)?

---

## 2. Frontend (`frontend/`)

**Scope:**
- `frontend/src/routes/` — all pages
- `frontend/src/lib/` — components, auth, config, types, utils
- `frontend/package.json`, `frontend/svelte.config.js`, `frontend/vite.config.js`
- `frontend/Dockerfile`

**Out of scope:** backend, discord_bot, infra

**Key questions:**
1. Czy fetch calls obsługują błędy (network, auth, 4xx/5xx)?
2. Czy state management (runes) jest spójny i nie powoduje race conditions?
3. Czy komponenty są wystarczająco wydajne (virtual scroll, memoization)?
4. Czy TypeScript types są poprawnie używane (brak `any`, spójność z api.d.ts)?
5. Czy auth flow jest bezpieczny (cookie handling, redirect)?

---

## 3. Infra (`infra/`, `Makefile`, Dockerfiles)

**Scope:**
- `infra/compose/docker-compose.dev.yml`
- `infra/compose/docker-compose.prod.yml`
- `infra/caddy/Caddyfile`
- `Makefile`
- `backend/Dockerfile`, `frontend/Dockerfile`, `discord_bot/Dockerfile`
- `.github/workflows/`

**Out of scope:** application code

**Key questions:**
1. Czy compose pliki są bezpieczne (secrets, port exposure)?
2. Czy Dockerfiles są optymalne (multi-stage, cache, image size)?
3. Czy CI/CD pipeline jest kompletny i poprawny?
4. Czy Caddy config jest bezpieczny i wydajny?
5. Czy Makefile targets są spójne z compose?

---

## 4. Discord Bot (`discord_bot/`)

**Scope:**
- `discord_bot/bot.py`
- `discord_bot/cogs/prices.py`
- `discord_bot/tests/`
- `discord_bot/pyproject.toml`, `discord_bot/Dockerfile`

**Out of scope:** backend, frontend, infra

**Key questions:**
1. Czy bot poprawnie obsługuje błędy (network, API, Discord rate limits)?
2. Czy slash commands są bezpieczne (walidacja inputu)?
3. Czy testy pokrywają krytyczne ścieżki?
4. Czy bot jest odporny na restart (state management)?

---

## 5. Integration (cross-layer contracts)

**Scope:**
- API contracts between frontend ↔ backend (`/api/*`)
- API contracts between bot ↔ backend (`/api/ingest/prices`)
- OpenAPI schema generation (`api.d.ts`)
- CORS configuration
- Cookie/JWT flow between frontend and backend

**Out of scope:** internal implementation details of each layer

**Key questions:**
1. Czy frontend poprawnie konsumuje API (types, error handling)?
2. Czy ingest endpoint jest spójny między addon, bot i frontend?
3. Czy CORS jest poprawnie skonfigurowany dla dev i prod?
4. Czy JWT cookie flow jest bezpieczny i spójny?
5. Czy OpenAPI schema jest aktualna z rzeczywistymi endpointami?

---

## 6. Security (cross-cutting)

**Scope:**
- All `.env*` files (existence check, not content)
- Auth/authz implementation
- Input validation (Pydantic schemas)
- SQL injection vectors (SQLModel/SQLAlchemy usage)
- XSS vectors (frontend rendering)
- CSRF protection
- CORS configuration
- Rate limiting
- Secret management
- Cookie security

**Out of scope:** functional testing

**Key questions:**
1. Czy secrets są bezpiecznie zarządzane (nie w repo)?
2. Czy walidacja wejścia jest kompletna po obu stronach?
3. Czy auth/authz chroni przed nieautoryzowanym dostępem?
4. Czy są podatności na injection (SQL, XSS, CSRF)?
5. Czy rate limiting chroni przed abuse?

---

## 7. Dependencies (`backend/`, `frontend/`, `discord_bot/`)

**Scope:**
- `backend/pyproject.toml` + `backend/uv.lock`
- `frontend/package.json` + `frontend/package-lock.json`
- `discord_bot/pyproject.toml` + `discord_bot/uv.lock`
- Known CVEs
- Deprecated packages
- EOL runtimes

**Out of scope:** application code review

**Key questions:**
1. Czy wszystkie zależności są aktualne?
2. Czy są znane CVE w używanych wersjach?
3. Czy jakieś pakiety są deprecated?
4. Czy runtime (Python 3.13, Node 22) jest wspierany?
5. Czy lock files są spójne z declared dependencies?

---

## 8. Code Quality (cross-cutting)

**Scope:**
- Code duplication across modules
- Naming consistency
- Dead code
- God objects / long functions
- Test coverage gaps
- Code style consistency

**Out of scope:** functional correctness, security

**Key questions:**
1. Czy są zduplikowane wzorce (copy-paste)?
2. Czy nazewnictwo jest spójne?
3. Czy jest martwy kod (unused imports, dead functions)?
4. Czy funkcje/classes są odpowiedzialne za jedną rzecz?
5. Czy testy mają sensowne assertions?

---

## 9. Test Evaluator (test quality assessment)

**Scope:**
- `backend/tests/` — all test files
- `discord_bot/tests/` — all test files
- Frontend test coverage (lack thereof)
- Test patterns and conventions
- Missing test scenarios

**Out of scope:** implementation code

**Key questions:**
1. Czy testy mają sensowne assertions (nie tylko "nie rzuca wyjątkiem")?
2. Czy testy pokrywają edge cases?
3. Czy brakuje krytycznych testów (unit/integration/e2e)?
4. Czy testy są deterministyczne (flaky tests)?
5. Czy test fixtures są poprawnie zarządzane?

---

## 10. Skeptic (meta-perspektywa)

**Scope:** Entire project — question necessity and complexity

**Key questions:**
1. Czy architektura nie jest over-engineered dla tej skali?
2. Czy można uprościć bez utraty funkcjonalności?
3. Czy wszystkie moduły są potrzebne?
4. Czy tech stack jest właściwy dla problemu?
5. Czy jest niepotrzebna złożoność?

---

## 11. Visionary (meta-perspektywa)

**Scope:** Entire project — suggest improvements and alternatives

**Key questions:**
1. Co gdyby użyć innego wzorca architektonicznego?
2. Jakie nowe podejścia mogłyby uprościć kod?
3. Jakie funkcjonalności mogłyby być wartościowe?
4. Jak skalować ten projekt?
5. Jakie technologie warto rozważyć?

---

## 12. Second Opinion (after all others)

**Scope:** All `findings.md` files from previous subagents

**Key questions:**
1. Które findings są najistotniejsze?
2. Które są przesadzone?
3. Jaki kontekst mogli przeoczyć?
4. Gdzie są konflikty między subagentami?
5. Co dodatkowego warto wskazać?


================================================================================
# SOURCE: audit/backend/findings.md
================================================================================

# Backend — findings

## Podsumowanie

Backend ArcheRage Market Tracker jest dobrze zaprojektowany z czystą modularną architekturą, solidnymi testami integracyjnymi na prawdziwej bazie PostgreSQL i przemyślanymi wzorcami (UUID suffix w testach, partial success dla ingest, atomic upsert dla inventory). Główne problemy to: potencjalny SQL injection przez nieescaped znaki specjalne w ILIKE, brak rate limitingu na kosztownych endpointach (crafting list, calculate), ładowanie całych tabel do pamięci w serwisach craftingowych, zduplikowana funkcja `utcnow()` w 5 plikach oraz martwy kod w `admin_auth.py`. Wydajność może stać się problemem przy wzroście danych — wiele endpointów robi N+1 lub pełne skanowanie tabel.

## Findings

### [🟠] SQL injection przez nieescaped znaki specjalne w ILIKE
- **Lokalizacja:** `backend/app/items/services.py:19`, `backend/app/user_items/services.py:28`
- **Problem:** Parametr `q` jest interpolowany bezpośrednio do wzorca ILIKE: `col(Item.name).ilike(f"%{q}%")`. Znaki specjalne `%` i `_` nie są escapowane.
- **Dlaczego to problem:** Użytkownik może wysłać `q=%` aby dopasować wszystkie rekordy lub użyć `_` jako wildcard jedno-znakowy. Przy braku escapowania `%` staje się wildcard wielo-znakowy w SQL, co może ujawnić dane lub spowodować nieoczekiwane wyniki.
- **Sugestia (bez implementacji):** Escapuj znaki specjalne ILIKE (`%`, `_`, `\`) przed interpolacją. Użyj `q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")` lub stwórz helper `_escape_ilike(pattern: str) -> str`.

### [🟠] Brak rate limitingu na kosztownych endpointach
- **Lokalizacja:** `backend/app/crafting/router.py:12-16`, `backend/app/crafting/router.py:19-25`, `backend/app/items/router.py:13-29`
- **Problem:** Endpointy `GET /api/crafting/` (list_summaries) i `POST /api/crafting/{item_id}/calculate` nie mają rate limitingu. `list_summaries` ładuje WSZYSTKIE przepisy i itemy, buduje drzewo craftingu dla każdego — to O(n*m) operacji.
- **Dlaczego to problem:** Brak ochrony przed abuse. Pojedynczy klient może zalać serwer kosztownymi requestami, zużywając CPU i pamięć. `list_summaries` jest szczególnie niebezpieczne — przy 100 przepisach z 5 składnikami każdy to 500+ operacji w pamięci per request.
- **Sugestia (bez implementacji):** Dodaj `@limiter.limit()` do endpointów craftingowych. Rozważ paginację dla `list_summaries` lub cache wyników.

### [🟠] Ładowanie całych tabel do pamięci w serwisach craftingowych
- **Lokalizacja:** `backend/app/crafting/services.py:12-25`, `backend/app/user_inventory/services.py:80-88`
- **Problem:** `load_all_recipes()` ładuje wszystkie Recipe + RecipeIngredient do pamięci. `load_all_items()` ładuje wszystkie Item. `get_inventory_for_recipe()` wywołuje obie funkcje tylko po to, żeby zbudować drzewo dla jednego itemu.
- **Dlaczego to problem:** Przy wzroście danych (tysiące itemów, setki przepisów) te funkcje zużywają coraz więcej pamięci i czasu. `get_inventory_for_recipe` jest wywoływane per-user, per-request — nie ma cache'owania.
- **Sugestia (bez implementacji):** Rozważ lazy loading (ładuj tylko potrzebną gałąź drzewa) lub cache z TTL. Dla `get_inventory_for_recipe` można załadować tylko RecipeRecipeIngredient dla danego item_id zamiast wszystkich.

### [🟡] Zduplikowana funkcja `utcnow()` w wielu modułach
- **Lokalizacja:** `backend/app/profiles/models.py:7-8`, `backend/app/items/models.py:7-8`, `backend/app/prices/models.py:6-7`, `backend/app/user_items/models.py:7-8`, `backend/seed.py:17-18`
- **Problem:** Funkcja `utcnow()` jest kopiowana w każdym module. Wszystkie mają identyczną implementację: `datetime.now(timezone.utc).replace(tzinfo=None)`.
- **Dlaczego to problem:** Naruszenie DRY. Jeśli trzeba zmienić logikę (np. dodać logging), trzeba edytować 5 plików. Łatwo o pomyłkę — ktoś zmieni jedną kopię a zapomni o pozostałych.
- **Sugestia (bez implementacji):** Wyodrębnij `utcnow()` do `app/config/datetime_utils.py` i importuj wszędzie.

### [🟡] Martwy kod i niespójność w `admin_auth.py`
- **Lokalizacja:** `backend/app/admin_auth.py:46`, `backend/app/admin_auth.py:51-69`
- **Problem:** `authentication_backend` jest definiowane dwukrotnie — linia 46 (`AdminAuth`) jest natychmiast nadpisana przez linię 67 (`SecureAdminAuth`). Klasa `SecureAdminAuth` tworzy `self.middlewares`, ale sqladmin `AuthenticationBackend` nie używa tego atrybutu — `SessionMiddleware` musi być dodany do FastAPI app, nie do auth backend.
- **Dlaczego to problem:** Martwy kod myli developerów. `SecureAdminAuth.middlewares` nie działa jak zamierzono — secure cookie mogłoby nie być aktywne mimo ustawienia `cookie_secure=True`.
- **Sugestia (bez implementacji):** Usuń martwy kod (linia 46 i klasa `SecureAdminAuth`). Jeśli secure cookie jest potrzebne, dodaj `SessionMiddleware` bezpośrednio do FastAPI app w `main.py`.

### [🟡] `add_price_point` commituje wewnętrznie — brak kontroli transakcji z zewnątrz
- **Lokalizacja:** `backend/app/prices/services.py:123`
- **Problem:** `add_price_point()` robi `await session.commit()` wewnątrz siebie. Gdy jest wywoływane z `ingest/services.py`, nie ma możliwości zrobienia rollbacku całej batch transakcji — każdy price point jest commitowany osobno.
- **Dlaczego to problem:** W `bulk_ingest` (ingest/services.py:96-100), jeśli `add_price_point` powiedzie się ale后续处理 fails, nie można zrollbackować tego konkretnego price point. Również `match_or_create_item` (ingest/services.py:46) robi własny commit, co może powodować partial commits w batchu.
- **Sugestia (bez implementacji):** Rozdzielenie logiki na `add_price_point` (bez commitu) i `add_price_point_and_commit` (z commitem). W `bulk_ingest` użyj wersji bez commitu i commituj raz na koniec batcha (luj per-row dla izolacji błędów).

### [🟡] Seed nie ustawia `last_price_at`
- **Lokalizacja:** `backend/seed.py:265-269`
- **Problem:** Seed aktualizuje `current_price` na itemie ale nie ustawia `last_price_at`. Po seedowaniu, `last_price_at` pozostaje `None` dla wszystkich itemów.
- **Dlaczego to problem:** Logika w `prices/services.py:117` sprawdza `if item.last_price_at is None or captured_at >= item.last_price_at`. Gdy `last_price_at` jest `None`, każdy nowy price point aktualizuje `current_price` — co jest OK. Ale po seedowaniu, `last_price_at` powinien wskazywać na ostatni zseedowany timestamp.
- **Sugestia (bez implementacji):** Dodaj `db_item.last_price_at = ts` w seed.py po zaktualizowaniu `current_price`.

### [🟡] `prices/services.py` ładuje wszystkie price points do pamięci przed bucketyzacją
- **Lokalizacja:** `backend/app/prices/services.py:34-35`
- **Problem:** `get_item_price_history` ładuje wszystkie pasujące PricePoint do pamięci, potem robi bucketyzację w Pythonie. Przy dużych historiach (np. 30 dni * 4 punkty/dzień * 1000 itemów = 120k rekordów per query) zużywa dużo pamięci.
- **Dlaczego to problem:** Dla interwałów `5m`, `1h`, `1d` buckety mogłyby być zrobione po stronie bazy (DATE_TRUNC). Pythonowa bucketyzacja jest OK dla małych datasetów ale nie skaluje się.
- **Sugestia (bez implementacji):** Dla nie-raw interwałów, użyj SQL `DATE_TRUNC` lub `generate_series` do agregacji po stronie bazy. Zostaw Pythonową bucketyzację tylko dla `raw`.

### [🟡] Brak `session.rollback()` po nieudanym `match_or_create_item`
- **Lokalizacja:** `backend/app/ingest/services.py:86-93`
- **Problem:** W `_process_row`, jeśli `match_or_create_item` rzuci wyjątek, session może być w stanie failed transaction. Exception jest łapany ale session nie jest rollbacowany przed kontynuacją do następnego wiersza.
- **Dlaczego to problem:** Kolejne wiersze w batchu będą używały tego samego session — mogą dostać błędy lub niespójne dane. `add_price_point` ma rollback (linia 102), ale `match_or_create_item` nie.
- **Sugestia (bez implementacji):** Dodaj `await session.rollback()` w bloku except dla `match_or_create_item` (linia 88-93).

### [🟡] `list_summaries` zwraca wszystkie craft results bez paginacji
- **Lokalizacja:** `backend/app/crafting/services.py:39-55`
- **Problem:** `list_summaries` buduje CraftResult dla każdego Recipe i zwraca wszystkie. Nie ma paginacji ani limitu.
- **Dlaczego to problem:** Przy 100+ przepisach, każdy z wieloma składnikami, ten endpoint może zwrócić megabajty danych i zużyć dużo CPU. Frontend prawdopodobnie nie potrzebuje wszystkich naraz.
- **Sugestia (bez implementacji):** Dodaj paginację (offset/limit) lub cache wyników z TTL. Rozważ lazy loading — frontend może ładować summary po kolei.

### [🟡] `admin.py` używa synchronicznego silnika dla sqladmin
- **Lokalizacja:** `backend/app/admin.py:13`
- **Problem:** `Admin(app, engine, ...)` używa synchronicznego `engine` z `app/config/db.py:12`. sqladmin wykonuje synchroniczne zapytania, co blokuje event loop.
- **Dlaczego to problem:** W produkcji, jeśli admin panel jest używany podczas ruchu, synchroniczne zapytania mogą blokować async requesty. Przy dużej liczbie rekordów w admin list view, może to powodować timeouty.
- **Sugestia (bez implementacji):** Rozważ użycie `async_engine` z sqladmin (jeśli wspiera) lub ogranicz dostęp do admin panelu do niskiego ruchu.

### [🟢] `print()` zamiast logging w `auth/manager.py`
- **Lokalizacja:** `backend/app/auth/manager.py:30`
- **Problem:** `print(f"User {user.id} has registered.")` używa `print()` zamiast proper logging.
- **Dlaczego to problem:** `print()` nie ma poziomów (DEBUG/INFO/WARNING), nie jest przechwytywany przez systemy logowania, nie ma timestampów ani kontekstu.
- **Sugestia (bez implementacji):** Zamień na `import logging; logger = logging.getLogger(__name__); logger.info(...)`.

### [🟢] Niespójna nazwa tabeli `userinventory` vs `useritem`
- **Lokalizacja:** `backend/app/user_inventory/models.py:7`
- **Problem:** `UserInventory` ma `__tablename__ = "userinventory"` (custom), ale `UserItem` (user_items/models.py) nie ma custom tablename — sqlmodel generuje `useritem`. Nazewnictwo jest niespójne.
- **Dlaczego to problem:** Drobne niespójność, ale może mylić developerów szukających tabel w DB.
- **Sugestia (bez implementacji):** Ujednolicenie — albo wszystkie tabele z custom `__tablename__`, albo żadne.

### [🟢] `col()` wrapper niepotrzebny w `user_inventory/services.py`
- **Lokalizacja:** `backend/app/user_inventory/services.py:98`
- **Problem:** `col(UserInventory.item_id).in_(ingredient_ids)` — `col()` jest niepotrzebne. `UserInventory.item_id.in_(ingredient_ids)` działa bezpośrednio na SQLModel Field.
- **Dlaczego to problem:** Zbędny import i niejasny kod. `col()` jest potrzebne gdy chce się wywołać metodę na kolumnie, ale SQLModel Field już wspiera `.in_()`.
- **Sugestia (bez implementacji):** Usuż `col` z importu i użyj `UserInventory.item_id.in_(ingredient_ids)`.

### [🟢] Test `test_consistency.py` zależy od frontend kodu
- **Lokalizacja:** `backend/tests/test_consistency.py:22-30`
- **Problem:** `test_frontend_chart_uses_ah_source` czyta plik frontendu (`+page.svelte`). Jeśli frontend zmieni nazwę stałej lub strukturę pliku, test backendu się złamie.
- **Dlaczego to problem:** Testy backendu nie powinny zależeć od frontend kodu. To tworzy sztuczne coupling.
- **Sugestia (bez implementacji):** Przenieś ten test do CI pipeline jako osobny check lub do frontend testów.

### [🟢] `Dockerfile` nie kopiuje `seed.py`
- **Lokalizacja:** `backend/Dockerfile`
- **Problem:** Dockerfile kopiuje `app`, `alembic`, `alembic.ini` ale nie kopiuje `seed.py`. Seed nie może być uruchomiony w kontenerze.
- **Dlaczego to problem:** Jeśli seed jest potrzebny w produkcji (np. pierwsze uruchomienie), trzeba go ręcznie skopiować lub uruchomić poza kontenerem.
- **Sugestia (bez implementacji):** Dodaj `COPY seed.py ./` do Dockerfile lub przenieś seed do `app/` jako management command.

### [💡] Rozważ dodanie indeksu na `PricePoint(source, captured_at)`
- **Lokalizacja:** `backend/app/prices/models.py:10-16`
- **Problem:** Zapytanie `get_item_price_history` filtruje po `item_id`, `source` i `captured_at`. Indeks na `(item_id, source, captured_at)` byłby bardziej efektywny niż osobne indeksy.
- **Dlaczego to problem:** Przy dużej tabeli price_points, zapytanie z wieloma filtrami może skanować wiele wierszy. Composite index pozwala na index-only scan.
- **Sugestia (bez implementacji):** Dodaj composite index `(item_id, source, captured_at)` w nowej migracji Alembic.

### [💡] Rozważ cache dla `load_all_recipes` i `load_all_items`
- **Lokalizacja:** `backend/app/crafting/services.py:12-25`
- **Problem:** Te funkcje są wywoływane przy każdym requeście craftingowym, ładując te same dane za każdym razem.
- **Dlaczego to problem:** Dane zmieniają się rzadko (tylko przy seed lub admin edycji), ale są ładowane z DB przy każdym requeście.
- **Sugestia (bez implementacji):** Dodaj in-memory cache z TTL (np. `cachetools.TTLCache`) lub Redis cache. Invalidacja po zmianie Recipe/RecipeIngredient/Item.

### [💡] `asyncio_default_test_loop_scope = "session"` może maskować problemy z izolacją
- **Lokalizacja:** `backend/pyproject.toml:35`
- **Problem:** Wszystkie testy dzielą jeden event loop. Fixtures z `scope="session"` (np. `setup_database`) działają poprawnie, ale testy mogą nie izolować się od siebie w ramach sesji.
- **Dlaczego to problem:** Jeśli test A modyfikuje globalny stan (np. rate limiter), test B może to zobaczyć. Na szczęście testy używają `NullPool` i osobnych session, co minimalizuje ryzyko.
- **Sugestia (bez implementacji):** Monitoruj testy pod kątem flakiness. Jeśli wystąpią, rozważ `loop_scope = "function"` zamiast `"session"`.


================================================================================
# SOURCE: audit/frontend/findings.md
================================================================================

# Frontend — findings

## Podsumowanie

Frontend jest napisany czysto w Svelte 5 (runes) z TypeScriptem, Tailwind CSS v4 i daisyUI v5. Architektura jest prosta i czytelna — routing plikowy, scentralizowany auth store, typy generowane z OpenAPI. Główna słabość to **brak obsługi błędów sieciowych w kluczowych flow (login, logout, register)** oraz **brak anulowania请求 (AbortController)** przy nawigacji. Kilka endpointów nie sprawdza 401, co może powodować ciche faily dla niezalogowanych użytkowników. Brak jakichkolwiek testów frontendowych.

## Findings

### 🟠 Brak obsługi błędów sieciowych w login/register/logout
- **Lokalizacja:** `frontend/src/lib/auth.svelte.ts:51-71` (login), `73-87` (register), `109-115` (logout)
- **Problem:** Funkcje `login()` i `register()` nie mają `try-catch` wokół `fetch()`. Jeśli sieć jest niedostępna, fetch rzuci nieobsłużonym wyjątkiem. `logout()` w ogóle nie sprawdza odpowiedzi serwera — czyści stan lokalny niezależnie od sukcesu/porażki API.
- **Dlaczego to problem:** Użytkownik zobaczy błąd konsoli zamiast komunikatu "Network error". W przypadku logout, jeśli serwer nie odpowie, użytkownik myśli że się wylogował, ale cookie JWT może nadal być aktywne.
- **Sugestia:** Otoczyć fetch w login/register blokiem try-catch zwracającym `{ success: false, message: 'Network error' }`. W logout dodać obsługę błędu i rozważyć wyczyszczenie cookie po stronie klienta tylko po potwierdzeniu serwera.

### 🟠 Brak obsługi 401 na większości endpointów API
- **Lokalizacja:** `frontend/src/routes/+page.svelte:10-21`, `frontend/src/routes/items/[id]/+page.svelte:99-129`, `frontend/src/lib/components/ItemTable.svelte:95-122`
- **Problem:** Tylko `inventory/+page.svelte` i `ItemTable` (gdy `requireAuth=true`) sprawdzają `response.status === 401` i przekierowują do `/auth`. Pozostałe strony (home, item detail, price history) nie sprawdzają 401 — po prostu wyświetlają błąd lub puste dane.
- **Dlaczego to problem:** Jeśli token wygaśnie w trakcie sesji, użytkownik zobaczy "Could not load items" zamiast being redirected do logowania. Zły UX.
- **Sugestia:** Stworzyć wrapper `fetchApi()` w `config.ts` lub `api.ts` który automatycznie sprawdza 401 i robi `goto('/auth')`. Używać go zamiast surowego `fetch()`.

### 🟠 Brak anulowania请求 (AbortController) przy nawigacji
- **Lokalizacja:** wzorzec, wiele miejsc — `items/[id]/+page.svelte`, `ItemTable.svelte`, `inventory/+page.svelte`
- **Problem:** Żadna strona nie używa `AbortController` do anulowania fetchów po odmontowaniu komponentu. Jeśli użytkownik szybko nawiguje między stronami, odpowiedzi z poprzednich fetchów mogą przyjść po odmontowaniu i próbować ustawić state na nieistniejącym komponencie.
- **Dlaczego to problem:** W Svelte 5 runes, przypisanie do `$state` po odmontowaniu jest bezpieczne (nie crashuje), ale powoduje niepotrzebne przetwarzanie i może powodować flickering jeśli użytkownik nawiguje tam-z powrotem.
- **Sugestia:** Dodać `AbortController` w `onMount` i abort w cleanup function. Przekazywać sygnał do fetch calls.

### 🟠 `@ts-nocheck` w komponencie wykresu
- **Lokalizacja:** `frontend/src/lib/components/charts/EChartsLineChart.svelte:2`
- **Problem:** `// @ts-nocheck` wyłącza całą type-checking dla tego pliku. ECharts ma skomplikowany API typów, ale wyłączenie TS maskuje potencjalne błędy.
- **Dlaczego to problem:** Type safety jest jednym z celów projektu (TypeScript w tsconfig strict mode). Wyłączenie go w komponencie odpowiedzialnym za wyświetlanie danych finansowych jest ryzykowne.
- **Sugestia:** Użyć `@ts-expect-error` na konkretnych liniach zamiast globalnego `@ts-nocheck`. Rozważyć użycie typów ECharts zamiast omijania.

### 🟡 Użycie `any` w mapowaniu danych cenowych
- **Lokalizacja:** `frontend/src/routes/items/[id]/+page.svelte:124`
- **Problem:** `data.map((row: any) => ...)` — użyto `any` zamiast proper type union. API zwraca `PricePointRead[] | PriceBucketRead[]`, ale kod nie rozróżnia tych typów.
- **Dlaczego to problem:** Łamie konwencję strict TypeScript. Jeśli kształt odpowiedzi API się zmieni, nie będzie compile-time error.
- **Sugestia:** Dodać type guard lub discriminated union check. Eksportować `PriceHistoryRow = PricePointRead | PriceBucketRead` z `types.ts`.

### 🟡 Dockerfile kopiuje całe node_modules (w tym devDependencies)
- **Lokalizacja:** `frontend/Dockerfile:20-22`
- **Problem:** `COPY --from=builder /app/node_modules ./node_modules` kopiuje wszystkie node_modules z fazy build, w tym devDependencies (svelte, vite, typescript, tailwind itp.). Nie ma `npm prune --production` ani multi-stage z `npm ci --omit=dev`.
- **Dlaczego to problem:** Zwiększa rozmiar obrazu produkcyjnego o ~200-400MB niepotrzebnych paczek. W runtime potrzebny jest tylko adapter-node i echarts.
- **Sugestia:** Dodać `RUN npm prune --production` po build lub użyć osobnego `npm ci --omit=dev` w final stage.

### 🟡 Brak CSRF protection
- **Lokalizacja:** wzorzec, wiele miejsc — `auth.svelte.ts`, `ItemTable.svelte`, `inventory/+page.svelte`
- **Problem:** Aplikacja używa cookie-based auth (`credentials: 'include'`) ze stanem-mutującymi requestami (POST, PUT, DELETE) ale nie implementuje CSRF tokens. CORS jest skonfigurowany z `allow_credentials=True`.
- **Dlaczego to problem:** Jeśli `cors_origins` jest zbyt liberalne lub jeśli atakator kontroluje subdomenę, może wykonać akcje w imieniu użytkownika. FastAPI + JWT cookies jest mniej podatne niż session-based, ale ryzyko istnieje.
- **Sugestia:** Rozważyć dodanie `SameSite=Strict` do cookie (po stronie backendu) lub double-submit cookie pattern.

### 🟡 Potencjalna rekursja nieskończona w drzewie craftingu
- **Lokalizacja:** `frontend/src/routes/items/[id]/+page.svelte:36-53`, `frontend/src/lib/components/crafting/RecipeTree.svelte:19-33`
- **Problem:** `computeNodeCost()` jest rekurencyjna — wywołuje się na `node.ingredients`. Jeśli dane API zawierają cykliczny przepis (A potrzebuje B, B potrzebuje A), funkcja wpadnie w nieskończoną rekurencję.
- **Dlaczego to problem:** Zablokuje UI thread w przeglądarce, powodując freeze strony. Backend powinien zapobiegać cyklom, ale frontend nie ma obrony.
- **Sugestia:** Dodać parametr `visited: Set<number>` i zwracać 0 jeśli node już był odwiedzony.

### 🟡 Race condition w infinite scroll ItemTable
- **Lokalizacja:** `frontend/src/lib/components/ItemTable.svelte:206-213`
- **Problem:** `$effect` sprawdza `hasMore && !loading && endIndex > items.length - 20` i wywołuje `loadItems()`. Chociaż `loadItems` ma guard `if (loading) return`, istnieje okno między sprawdzeniem warunku a ustawieniem `loading = true` wewnątrz funkcji, gdzie efekt może się odpalić ponownie.
- **Dlaczego to problem:** Może spowodować podwójne fetchowanie tych samych danych, duplikując elementy w liście.
- **Sugestia:** Użyć flagi `loading` ustawianej synchronicznie przed async operacją (już jest, ale efekt powinien to lepiej obsługiwać). Rozważyć debounce na efekcie.

### 🟡 Inventory page ładuje WSZYSTKIE itemy
- **Lokalizacja:** `frontend/src/routes/inventory/+page.svelte:42-73`
- **Problem:** Strona inventory fetchuje wszystkie itemy z API (paginated, 200 na raz, sekwencyjnie w pętli while). Dla bazy z tysiącami itemów, to wiele requestów i dużo danych w pamięci.
- **Dlaczego to problem:** Wolny czas ładowania, duży memory footprint, niepotrzebne zużycie bandwidth. Użytkownik może potrzebować tylko 10-20 itemów w inventory.
- **Sugestia:** Zamiast ładować wszystkie itemy, użyć autocomplete/search endpointu. Albo połączyć inventory z itemami w jednym API callu po stronie backendu.

### 🟡 Brak wirtualizacji w inventory table
- **Lokalizacja:** `frontend/src/routes/inventory/+page.svelte:142-185`
- **Problem:** Tabela renderuje wszystkie przefiltrowane itemy w DOM. W przeciwieństwie do `ItemTable.svelte` (który ma virtual scroll), inventory page nie ma żadnej wirtualizacji.
- **Dlaczego to problem:** Przy dużej liczbie itemów (>500) rendering setek wierszy input spowalnia przeglądarkę, szczególnie na mobile.
- **Sugestia:** Dodać virtual scroll podobny do tego w `ItemTable.svelte` lub paginację.

### 🟡 Brak minimum password length na frontendzie
- **Lokalizacja:** `frontend/src/routes/auth/+page.svelte:74-81`
- **Problem:** Pole password ma tylko `required` — nie ma walidacji minimalnej długości. Backend prawdopodobnie ma taką walidację (fastapi-users domyślnie 8 znaków), ale frontend nie informuje użytkownika o wymaganiach.
- **Dlaczego to problem:** Użytkownik wpisze "abc", dostanie 422 z backendu z niejasnym komunikatem błędu zamiast jasnej informacji o wymaganiach.
- **Sugestia:** Dodać `minlength="8"` na input i/lub wyświetlać wymagania hasła pod polem.

### 🟢 Mobile: brak alternatywy dla ukrytego przycisku "Save"
- **Lokalizacja:** `frontend/src/lib/components/ItemTable.svelte:314-323`
- **Problem:** Kolumna "Save" (gwiazdka) ma `hidden md:block` — jest całkowicie ukryta na mobile. Nie ma alternatywnego sposobu zapisania itemu na małych ekranach.
- **Dlaczego to problem:** Mobilni użytkownicy nie mogą dodawać itemów do watchlisty.
- **Sugestia:** Dodać swipe-to-save, long-press menu, albo przenieść gwiazdkę do wiersza obok nazwy itemu (widocznej na mobile).

### 🟢 Duplikacja `computeNodeCost` między komponentami
- **Lokalizacja:** `frontend/src/routes/items/[id]/+page.svelte:36-53` i `frontend/src/lib/components/crafting/RecipeTree.svelte:19-33`
- **Problem:** Funkcja `computeNodeCost` jest zaimplementowana identycznie w dwóch miejscach — w page component i w RecipeTree.
- **Dlaczego to problem:** Duplikacja kodu. Zmiana logiki w jednym miejscu bez zmiany w drugim spowoduje niespójność.
- **Sugestia:** Wydzielić do `frontend/src/lib/crafting.ts` jako eksportowaną funkcję.

### 🟢 CSS `.sticky` nadpisuje daisyUI
- **Lokalizacja:** `frontend/src/lib/components/ItemTable.svelte:344-348`
- **Problem:** Custom `.sticky` class z `backdrop-filter: blur(12px)` i `background-color` nadpisuje potencjalnie daisyUI klasy. Użyte na `.sticky.top-0.z-20` div.
- **Dlaczego to problem:** Konflikt nazw z Tailwind utility `.sticky` (position: sticky). Może powodować niezamierzone efekty wizualne.
- **Sugestia:** Zmienić nazwę klasy na np. `.sticky-header` aby uniknąć konfliktu z Tailwind.

### 🟢 Brak testów frontendowych
- **Lokalizacja:** cały `frontend/src/`
- **Problem:** Zero plików testowych w frontend. Brak unit testów, integration testów, ani e2e testów.
- **Dlaczego to problem:** Regresje w auth flow, API calls, i computed values (profit/margin) nie będą wykryte automatycznie. Szczególnie ryzykowne dla logiki craftingu.
- **Sugestia:** Dodać testy dla: auth store, currency utils, computeNodeCost, formatCurrency. Rozważyć Playwright dla krytycznych flow (login, nawigacja, crafting).

### 🟢 `grades.ts` nie zawiera wszystkich stopni z API
- **Lokalizacja:** `frontend/src/lib/grades.ts:1-14`
- **Problem:** `GRADE_COLORS` nie zawiera klucza `'Basic'` ani `'All'` (który jest w API jako ItemGrade). `gradeColor()` zwraca fallback `#9ca3af` dla brakujących kluczy.
- **Dlaczego to problem:** 'Basic' items będą wyświetlane z tym samym kolorem co 'Grand' (fallback). 'All' jest używane w filtrach jako opcja.
- **Sugestia:** Dodać `'Basic': '#9ca3af'` (lub inny kolor) do mapy.

### 💡 Rozważenie: scentralizowany API client
- **Lokalizacja:** wzorzec, wiele miejsc
- **Problem:** Każda strona komponent woła surowy `fetch()` z ręcznym budowaniem URL, headers, i error handling. To powtarzalny boilerplate.
- **Sugestia:** Stworzyć `frontend/src/lib/api.ts` z wrapperem `fetchApi<T>(path, options): Promise<T>` który: dodaje base URL, credentials, sprawdza 401/4xx/5xx, parse JSON, i typed response. Zmniejszy boilerplate i ujednolici error handling.

### 💡 Rozważenie: loading states jako enum
- **Lokalizacja:** wzorzec, wiele miejsc
- **Problem:** Stany ładowania są zarządzane przez wiele boolean flags (`loading`, `loadingItem`, `loadingHistory`, `hasMore`, `fetchError`). Trudne do zarządzania przy większej złożoności.
- **Sugestia:** Rozważyć pattern `{ status: 'idle' | 'loading' | 'error' | 'success', error?: string }` dla każdego async operation.

## API Contract validation

| Endpoint | Frontend call | Backend route | Status |
|----------|--------------|---------------|--------|
| `POST /api/auth/login` | `auth.svelte.ts:56` | `auth/router.py` (fastapi-users) | ✓ |
| `POST /api/auth/register` | `auth.svelte.ts:74` | `auth/router.py` (fastapi-users) | ✓ |
| `POST /api/auth/logout` | `auth.svelte.ts:110` | `auth/router.py` (fastapi-users) | ✓ |
| `GET /api/users/me` | `auth.svelte.ts:34` | `auth/router.py` (fastapi-users) | ✓ |
| `GET /api/profiles/me` | `auth.svelte.ts:23` | `profiles/router.py:14` | ✓ |
| `PATCH /api/profiles/me` | `auth.svelte.ts:91` | `profiles/router.py:22` | ✓ |
| `GET /api/items/` | `+page.svelte:12`, `ItemTable:97` | `items/router.py:13` | ✓ |
| `GET /api/items/{id}` | `items/[id]/+page.svelte:102` | `items/router.py:32` | ✓ |
| `GET /api/items/{id}/price-history` | `items/[id]/+page.svelte:120` | `prices/router.py:24` | ✓ |
| `GET /api/user-items/me` | `ItemTable:97` (via props) | `user_items/router.py:14` | ✓ |
| `GET /api/user-items/ids` | `ItemTable:64` | `user_items/router.py:35` | ✓ |
| `POST /api/user-items/{id}` | `ItemTable:135` | `user_items/router.py:43` | ✓ |
| `DELETE /api/user-items/{id}` | `ItemTable:136` | `user_items/router.py:58` | ✓ |
| `GET /api/inventory/` | `inventory/+page.svelte:48` | `user_inventory/router.py:13` | ✓ |
| `GET /api/inventory/for-recipe/{id}` | `items/[id]/+page.svelte:147` | `user_inventory/router.py:21` | ✓ |
| `PUT /api/inventory/{id}` | `items/[id]/+page.svelte:190`, `inventory:82` | `user_inventory/router.py:32` | ✓ |
| `POST /api/crafting/{id}/calculate` | `items/[id]/+page.svelte:133` | `crafting/router.py:19` | ✓ |

## Metrics

- Svelte files: 13 (8 routes + 5 components)
- TypeScript files: 9 (lib)
- Test files: 0
- Views: 8 | Components: 5 | Utils/lib: 6
- Lines of Svelte+TS: ~2100
- API endpoints used: 17/17 — full contract coverage

## Priority Recommendations

1. **Dodaj try-catch do login/register/logout** — niski koszt, wysoki impact na UX
2. **Stwórz `fetchApi()` wrapper** — ujednolici error handling, doda 401 redirect globalnie
3. **Dodaj AbortController** — szczególnie w `items/[id]` i `ItemTable` przy nawigacji
4. **Usuń `@ts-nocheck`** — napraw typy ECharts zamiast omijania
5. **Wyodrębnij `computeNodeCost`** do shared lib — usunie duplikację
6. **Dodaj testy** dla auth store, currency utils, computeNodeCost
7. **Optimize Dockerfile** — prune devDependencies


================================================================================
# SOURCE: audit/infra/findings.md
================================================================================

# Infra — findings

## Podsumowanie

Infrastruktura jest prosta i czytelna, ale zawiera kilka istotnych luk bezpieczeństwa. Kontenery backendu i bota działają jako root, a Dockerfile frontendu kopiuje pełne node_modules (łącznie z devDependencies) do obrazu produkcyjnego, co zwiększa rozmiar i powierzchnię ataku. Caddy nie ma żadnych nagłówków bezpieczeństwa ani rate-limitingu, a w produkcji publicznie dostępne są endpointy `/docs`, `/redoc` i `/openapi.json`. Pipeline CI nie ma testów dla frontendu i nie buduje obrazów Docker dla discord bota.

## Findings

### 🔴 Kontenery backend i discord_bot działają jako root
- **Lokalizacja:** `backend/Dockerfile:1`, `discord_bot/Dockerfile:1`
- **Problem:** Żaden Dockerfile nie definiuje użytkownika non-root. Proces uvicorn/bot.py działa jako root w kontenerze.
- **Dlaczego to problem:** W przypadku exploita (RCE w aplikacji) atakujący uzyskuje uprawnienia root w kontenerze, co ułatwia escape do hosta (szczególnie przy braku --no-new-privileges i default capabilities).
- **Sugestia (bez implementacji):** Dodać `RUN useradd -r -s /usr/sbin/nologin appuser` i `USER appuser` przed CMD. Upewnić się, że pliki mają odpowiednie uprawnienia (chown).

### 🔴 Port PostgreSQL (5432) wystawiony na host w dev z domyślnymi poświadczeniami
- **Lokalizacja:** `infra/compose/docker-compose.dev.yml:12-13`
- **Problem:** Port 5432 jest bindowany na `0.0.0.0:5432` z domyślnym hasłem `postgres/postgres`.
- **Dlaczego to problem:** Każda usługa w sieci lokalnej (VPN, open Wi-Fi) może połączyć się z bazą. W połączeniu z domyślnymi poświadczeniami to łatwy cel. Na maszynie developera z otwartym portem to realne ryzyko.
- **Sugestia (bez implementacji):** Zmienić bind na `127.0.0.1:5432:5432` (tylko localhost). Rozważyć usunięcie portu z compose i użycie `podman exec` do bezpośredniego dostępu.

### 🟠 Frontend Dockerfile kopiuje pełne node_modules (devDependencies) do obrazu produkcyjnego
- **Lokalizacja:** `frontend/Dockerfile:20-21`
- **Problem:** Etap builder używa `npm install` (nie `--omit=dev`), a potem `COPY --from=builder /app/node_modules ./node_modules` przenosi wszystko do finalnego obrazu — łącznie z vite, svelte-check, eslint i innymi devDependency.
- **Dlaczego to problem:** Zwiększa rozmiar obrazu o dziesiątki MB, wydłuża build, i zwiększa powierzchnię ataku (dodatkowe pakiety z potencjalnymi CVE).
- **Sugestia (bez implementacji):** Użyć `npm ci --omit=dev` w etapie builder (lub `npm ci` + `npm prune --omit=dev` po build, jeśli build potrzebuje devDeps). Alternatywnie użyć adaptera, który nie wymaga node_modules w runtime (np. @sveltejs/adapter-node z `npm ci --omit=dev` w finalnym etapie).

### 🟠 Frontend Dockerfile używa `npm install` zamiast `npm ci`
- **Lokalizacja:** `frontend/Dockerfile:6`
- **Problem:** `npm install` może modyfikować `package-lock.json`, co czyni build niereprodukowalnym.
- **Dlaczego to problem:** Różne buildy mogą mieć różne wersje zależności. W CI/CD to prowadzi do nieprzewidywalnych zachowań i trudniejszego debugowania.
- **Sugestia (bez implementacji):** Zmienić na `npm ci` — instaluje dokładnie wersje z lockfile i jest szybsze.

### 🟠 Caddy nie ma nagłówków bezpieczeństwa
- **Lokalizacja:** `infra/caddy/Caddyfile` (cały plik)
- **Problem:** Brak nagłówków: `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Content-Security-Policy`, `Strict-Transport-Security` (HSTS).
- **Dlaczego to problem:** Podatność na clickjacking, MIME-sniffing, referrer leak, downgrade do HTTP. Brak HSTS pozwala na SSL stripping przy pierwszym połączeniu.
- **Sugestia (bez implementacji):** Dodać blok `header` w Caddyfile z odpowiednimi nagłówkami. Caddy automatycznie zarządza TLS, ale HSTS trzeba ustawić ręcznie.

### 🟠 Endpointy /docs, /redoc, /openapi.json publicznie dostępne w produkcji
- **Lokalizacja:** `infra/caddy/Caddyfile:11-21`
- **Problem:** Dokumentacja API jest publicznie dostępna — ujawnia strukturę endpointów, modeli danych i potencjalnie wrażliwych informacji o logice biznesowej.
- **Dlaczego to problem:** Ułatwia reconnaissance atakującemu. Szczególnie /openapi.json daje pełny schemat API.
- **Sugestia (bez implementacji):** Zablokować te endpointy w produkcji lub ograniczyć do IP whitelist / uwierzytelnienia. Można to zrobić w Caddy (matcher `not remote_ip`) lub w samej aplikacji (wyłączenie docs w prod).

### 🟠 Frontend CI nie ma testów
- **Lokalizacja:** `.github/workflows/frontend.yml`
- **Problem:** Workflow uruchamia tylko `svelte-check` (type checking). Brak testów jednostkowych ani integracyjnych.
- **Dlaczego to problem:** Regresje w logice frontendu nie są wyłapywane w CI. Type checking nie zastępuje testów.
- **Sugestia (bez implementacji):** Dodać krok z `npm run test` (jeśli są testy) lub rozważyć dodanie vitest.

### 🟡 Backend Dockerfile — brak multi-stage, duży rozmiar obrazu
- **Lokalizacja:** `backend/Dockerfile:1`
- **Problem:** Używa jednego etapu buildu. Obraz zawiera uv, pip cache, cały toolchain Pythona.
- **Dlaczego to problem:** Obraz jest większy niż potrzeba. Dla slim-bookworm to ~200MB+ narzutu.
- **Sugestia (bez implementacji):** Rozważyć multi-stage: etap builder z uv do install, finalny etap z python:3.13-slim z skopiowanymi pakietami. Alternatywnie, dla obecnego stacka (uv sync) obecne podejście jest akceptowalne — pritetem jest bezpieczeństwo (root).

### 🟡 Brak healthchecków dla backend i frontend w produkcji
- **Lokalizacja:** `infra/compose/docker-compose.prod.yml:18-35`, `:36-41`
- **Problem:** Tylko db ma healthcheck. Backend i frontend nie mają — Docker/restart policy nie wie, czy serwis jest zdrowy.
- **Dlaczego to problem:** `restart: unless-stopped` restartuje kontener po crashu, ale nie po zawieszeniu (hang). Brak healthchecków oznacza, że Caddy może proxy-ować do martwego backendu.
- **Sugestia (bez implementacji):** Dodać healthcheck dla backendu (`curl -f http://localhost:8000/api/health` lub podobny). Dla frontendu — sprawdzić, czy SvelteKit ma endpoint health.

### 🟡 Docker workflow nie buduje obrazu dla discord bota
- **Lokalizacja:** `.github/workflows/docker.yml`
- **Problem:** Workflow buduje tylko backend i frontend. Discord bot nie jest walidowany pod kątem buildu Docker.
- **Dlaczego to problem:** Zmiana w Dockerfile bota lub jego zależnościach nie jest weryfikowana w CI.
- **Sugestia (bez implementacji):** Dodać job `build-discord-bot` analogiczny do istniejących.

### 🟡 CI workflows nie mają concurrency groups
- **Lokalizacja:** `.github/workflows/backend.yml`, `frontend.yml`, `discord_bot.yml`, `docker.yml`
- **Problem:** Brak `concurrency` — wiele workflow runs na tym samym branchu może się wykonywać równolegle, marnując runner minutes.
- **Dlaczego to problem:** Push-push szybko po sobie = dwa pełne buildy. Nie ma anulowania starszego run.
- **Sugestia (bez implementacji):** Dodać `concurrency: { group: "${{ github.workflow }}-${{ github.ref }}", cancel-in-progress: true }` na poziomie workflow.

### 🟡 Brak rate-limitingu w Caddy
- **Lokalizacja:** `infra/caddy/Caddyfile`
- **Problem:** Brak jakiegokolwiek rate-limitingu na reverse proxy.
- **Dlaczego to problem:** API jest podatne na brute-force (login), scraping, DDoS na poziomie aplikacji. Backend ma rate limiter (singleton w `app/config/rate_limit.py`), ale Caddy powinien być pierwszą linią obrony.
- **Sugestia (bez implementacji):** Dodać plugin `rate-limit` w Caddy lub rozważyć `request_body` limiter. Ewentualnie polegać na limiterze aplikacji, ale dodać reverse proxy-level limiting jako defense-in-depth.

### 🟡 Brak .dockerignore dla discord_bota
- **Lokalizacja:** `discord_bot/` (brak pliku)
- **Problem:** Nie ma `.dockerignore` — `COPY . .` (gdyby istniał) skopiowałby .venv, __pycache__, .env, .git do obrazu.
- **Dlaczego to problem:** Obecnie Dockerfile bota kopiuje selektywnie (`bot.py`, `cogs/`), więc to niskie ryzyko. Ale jeśli ktoś doda `COPY . .`, nie będzie ochrony.
- **Sugestia (bez implementacji):** Dodać `.dockerignore` z .venv, __pycache__, .env, .git jako dobra praktyka.

### 🟡 Backend prod: tylko 2 workery uvicorn
- **Lokalizacja:** `infra/compose/docker-compose.prod.yml:23`
- **Problem:** `--workers 2` — dla aplikacji synchronicznej (psycopg) to mało.
- **Dlaczego to problem:** Przy 2 workerach i synchronicznych zapytaniach DB, serwer może się zablokować przy większym ruchu. Zależy od obciążenia, ale standardowa rekomendacja to `2 * CPU + 1`.
- **Sugestia (bez implementacji):** Zwiększyć do 4 lub skonfigurować na podstawie dostępnych CPU. Rozważyć zmianę na async (asyncpg jest już skonfigurowany w ASYNC_DATABASE_URL).

### 💡 Frontend Dockerfile — drugi etap nie jest minimalny
- **Lokalizacja:** `frontend/Dockerfile:16`
- **Problem:** Drugi etap używa `node:22-alpine` zamiast bardziej minimalnego obrazu.
- **Dlaczego to problem:** node:22-alpine zawiera npm, npx, i inne narzędzia niepotrzebne w runtime.
- **Sugestia (bez implementacji):** Rozważyć użycie `node:22-alpine` z `npm ci --omit=dev` lub dedykowanego obrazu runtime (np. distroless, jeśli adapter na to pozwala).

### 💡 Docker workflow buduje obrazy ale ich nie pushuje
- **Lokalizacja:** `.github/workflows/docker.yml:30`, `:45`
- **Problem:** `push: false` — obrazy są budowane i cache'owane, ale nigdzie nie trafiają.
- **Dlaczego to problem:** Jeśli celem jest weryfikacja buildu — OK. Ale jeśli planujesz deploy przez CI, brakuje kroku push do rejestru (GHCR, Docker Hub).
- **Sugestia (bez implementacji):** Zdefiniować strategię deploy. Jeśli obrazy mają być publikowane, dodać login do GHCR + push na tag/merge do main.


================================================================================
# SOURCE: audit/discordbot/findings.md
================================================================================

# Discord Bot — findings

## Podsumowanie

Bot jest prosty i zwięzły, z dobrą obsługą podstawowych błędów (defer + followup, walidacja wejścia). Kilka istotnych problemów: każdy request HTTP tworzy nowego klienta httpx (brak connection pooling), brak obsługi rate-limitów Discorda, kontener Docker działa jako root. Testy pokrywają happy-path i podstawowe edge-case, ale brakuje testów timeoutów sieciowych i failure path w handlerach komend. Kod jest czytelny i łatwy do utrzymania, ale wymaga wzmocnienia w obszarze resilience i security.

## Findings

### 🟠 Nowy httpx.AsyncClient per request — brak connection pooling
- **Lokalizacja:** `cogs/prices.py:52` i `cogs/prices.py:98`
- **Problem:** Każde wywołanie `lookup_item` i `post_price` tworzy nowego `httpx.AsyncClient` w kontekście `async with`. Oznacza to nowe TCP handshake per request, brak keep-alive, brak connection pooling.
- **Dlaczego to problem:** Przy większym ruchu (kilku userów jednocześnie) bot będzie otwierał i zamykał dziesiątki socketów. Może doprowadzić do wyczerpania file descriptors na hoście. Dodatkowo — każdy request płaci koszt TLS handshake jeśli backend jest za HTTPS.
- **Sugestia (bez implementacji):** Stwórz jednego `httpx.AsyncClient` w `setup_hook` lub w `__init__` coga i zamknij go w `cog_unload`. Przekazuj go do helperów zamiast tworzyć nowego.

### 🟠 Brak obsługi Discord rate limits (HTTP 429)
- **Lokalizacja:** `cogs/prices.py:131`, `cogs/prices.py:193` (oba commandy)
- **Problem:** Bot nie sprawdza czy Discord API zwróciło 429 (rate limit). `interaction.followup.send` może zwrócić 429 przy natężeniu — bot tego nie obsługuje.
- **Dlaczego to problem:** Discord nakłada rate limity na interaction followup (5 na 5 sekund per webhook). Przy wielu userach jednocześnie bot może tracić wiadomości bez informowania usera.
- **Sugestia (bez implementacji):** Dodaj retry z exponential backoff na 429, lub przynajmniej złap `discord.HTTPException` z kodem 429 i poinformuj usera o throttlingu.

### 🟠 Kontener Docker działa jako root
- **Lokalizacja:** `Dockerfile:1-11`
- **Problem:** Brak `USER` directive — proces bota działa jako root w kontenerze. Jeśli attacker uzyska RCE przez exploit w discord.py lub httpx, ma uprawnienia roota.
- **Dlaczego to problem:** Zasada least privilege. Root w kontenerze = dostęp do wszystkich plików, możliwość eskalacji jeśli kontener ma dodatkowe capabilities.
- **Sugestia (bez implementacji):** Dodaj `RUN useradd -m botuser` i `USER botuser` przed `CMD`.

### 🟡 Brak testów failure path w handlerach komend
- **Lokalizacja:** `tests/test_prices.py`
- **Problem:** Brakuje testów dla:
  - `lookup_item` rzucający `httpx.HTTPError` w `/addprice` i `/price`
  - `post_price` rzucający `httpx.HTTPError` w `/addprice` (backend unreachable)
  - `post_price` rzucający `ValueError` (backend rejected) w `/addprice`
  - Timeout sieciowy (mock `httpx.TimeoutException`) — czy user dostaje czytelny komunikat
- **Dlaczego to problem:** Jeśli backend padnie lub nie odpowie — jedyny "test" to log z produkcji. Brak safety net na regressions w error handling.
- **Sugestia (bez implementacji):** Dodaj testy z `respx` mockującymi timeout (via side_effect) i connection refused. Zweryfikuj treść wiadomości do usera.

### 🟡 Brak rozróżnienia timeout vs HTTP error w logach
- **Lokalizacja:** `cogs/prices.py:147`, `cogs/prices.py:197`
- **Problem:** Blok `except (httpx.HTTPError, KeyError, ValueError)` łapie też `httpx.TimeoutException` (dziedziczy z `httpx.HTTPError`), ale user dostaje ten sam komunikat "Backend connection error" — nie wiadomo czy backend padł czy po prostu nie odpowiada w 10s.
- **Dlaczego to problem:** Utrudnia diagnostykę. Timeout sugeruje problem z wydajnością backendu, HTTP 500 — bug w backendzie, connection refused — backend down.
- **Sugestia (bez implementacji):** Rozważ osobne excepty dla `httpx.TimeoutException` i `httpx.HTTPStatusError` z dedykowanymi komunikatami ("Backend timed out" vs "Backend error"). Lub dodaj context do logów (exception type + URL).

### 🟡 Brak graceful shutdown / cog_unload
- **Lokalizacja:** `cogs/prices.py:109-110`
- **Problem:** Klasa `PricesCog` nie definiuje `cog_unload()`. Jeśli httpx.AsyncClient zostanie przeniesiony na poziom coga (zgodnie z findingiem wyżej), nie będzie miał jak się zamknąć.
- **Dlaczego to problem:** Resource leak przy restarcie bota lub przeładowaniu extension. Dziś to nie jest aktywny bug (bo client jest w context manager), ale stanie się problemem po refactorze connection pooling.
- **Sugestia (bez implementacji):** Dodaj `async def cog_unload(self)` zamykający klienta httpx.

### 🟡 Brak testu na silver > 99 / copper > 99
- **Lokalizacja:** `cogs/prices.py:133-143`
- **Problem:** Walidacja sprawdza tylko `gold < 0 or silver < 0 or copper < 0` i `total > 999_999 * 10000`, ale nie sprawdza czy silver <= 99 i copper <= 99. User może podać `silver=150` co w grze jest niemożliwe (150s = 1g 50s).
- **Dlaczego to problem:** Zapis do bazy zniekształconej ceny. Nie jest to security issue, ale data integrity — ceny w DB będą niepoprawne.
- **Sugestia (bez implementacji):** Dodaj walidację `silver >= 100` lub `copper >= 100` z ostrzeżeniem o konwersji, albo po prostu zablokuj wartości > 99.

### 🟡 Testy omijają Discord dispatch (callback bypass)
- **Lokalizacja:** `tests/test_prices.py:260` i inne
- **Problem:** Testy wywołują `cog.addprice.callback(cog, interaction, ...)` zamiast symulować dispatch przez `bot.tree`. To omija checki Discorda (permissions, cooldowns, type conversion).
- **Dlaczego to problem:** Testy nie weryfikują czy command jest poprawnie zarejestrowany w drzewie, czy parametry mają dobre type hints, czy choices działają.
- **Sugestia (bez implementacji):** Rozważ dodanie integracyjnego testu z `bot.tree.fetch_commands()` lub użycie `Interaction` mocka z bardziej realistycznymi atrybutami.

### 🟡 Brak testów dla `format_price` z ujemnymi wartościami
- **Lokalizacja:** `cogs/prices.py:29-41`, `tests/test_prices.py:17-34`
- **Problem:** `format_price(-500)` zwróci `-1g 50s` (Python integer division z ujemną). Walidacja w handlerze to łapie, ale funkcja jest publiczna i może być importowana.
- **Dlaczego to problem:** Jeśli `format_price` zostanie użyty gdzie indziej bez walidacji wejścia — bug w UI.
- **Sugestia (bez implementacji):** Dodaj `assert copper >= 0` lub test na ujemne.

### 🟢 Brak HEALTHCHECK w Dockerfile
- **Lokalizacja:** `Dockerfile:1-11`
- **Problem:** Docker/Compose nie wie czy proces bota żyje poza PID 1.
- **Dlaczego to problem:** Orchestrator (Docker Compose, K8s) nie zrestartuje martwego kontenera automatycznie bez healthcheck.
- **Sugestia (bez implementacji):** Dodaj `HEALTHCHECK CMD python -c "import discord; ..."` lub endpoint HTTP.

### 🟢 Brak graceful error message przy braku DISCORD_TOKEN
- **Lokalizacja:** `bot.py:20`
- **Problem:** `Settings()` rzuci `pydantic.ValidationError` przy braku env var. Stack trace jest czytelny, ale nie ma custom message.
- **Dlaczego to problem:** Minor — developer zobaczy surowy traceback zamiast "Set DISCORD_TOKEN env var".
- **Sugestia (bez implementacji):** Opcjonalnie opakuj w try/except z `sys.exit("Missing DISCORD_TOKEN")`.

### 💡 Rozróżniaj komunikaty błędów dla usera
- **Lokalizacja:** `cogs/prices.py:147-152`, `cogs/prices.py:164-169`, `cogs/prices.py:197-202`
- **Problem:** Wszystkie błędy HTTP/connection dają ten sam komunikat "Backend connection error — try again later." User nie wie czy to timeout, 500, czy connection refused.
- **Dlaczego to problem:** Utrudnia diagnostykę po stronie usera i deva. Timeout wymaga retry, 500 wymaga zgłoszenia buga.
- **Sugestia (bez implementacji):** Rozważ osobne excepty dla `httpx.TimeoutException` (dziedziczy z `httpx.HTTPError`) i `httpx.HTTPStatusError` z dedykowanymi komunikatami. Lub dodaj exception type do logów.

### 💡 Dodaj `app_commands.rename` dla lepszego UX
- **Lokalizacja:** `cogs/prices.py:113`, `cogs/prices.py:181`
- **Problem:** Parametr `name` jest słowem kluczowym w Python. Discord go wyświetli poprawnie, ale wewnątrz kodu koliduje z wbudowanym `name`.
- **Dlaczego to problem:** Minor — ale `item_name` byłby bardziej czytelny w kodzie i logach.
- **Sugestia (bez implementacji):** Użyj `@app_commands.describe(item_name="Item name")` z `rename="item_name"` lub zmień nazwę parametru.


================================================================================
# SOURCE: audit/integration/findings.md
================================================================================

# Integration — findings

## Podsumowanie

Addon Lua zapisuje wszystkie przedmioty z twardym kodem `grade:1` (Grand), co powoduje tworzenie zduplikowanych rekordów w DB zamiast aktualizacji istniejących. Schemat OpenAPI (`api.d.ts`) nie zgadza się z rzeczywistą odpowiedzią backendu dla `UserRead` — serializer usuwa pola, których schema nadal deklaruje. Frontend konsekwentnie używa `credentials: 'include'` na endpointach autoryzowanych, ale kilka wywołań publicznych endpointów pomija ten parametr (nie powoduje błędu, ale jest niekonsekwentne). CORS jest poprawnie skonfigurowany dla dev i prod. Bot Discord poprawnie komunikuje się z `/api/ingest/prices` — ten sam kontrakt co addon.

## Findings

### [🔴] Addon zapisuje wszystkie ceny z `grade:1` (Grand) — błędne dane w DB
- **Lokalizacja:** `addon/pricetracker_folio/pricetracker.lua:307`
- **Problem:** Funkcja `SavePrices()` hardkoduje `grade:1` w formacie JSONL: `{"name":"%s","grade":1,...}`. Wszystkie przedmioty z WATCHLIST (Iron Ore, Lumber, Leather, Fabric) są zapisywane jako grade=1 (Grand), niezależnie od ich rzeczywistego grade.
- **Dlaczego to problem:** Backend tworzy nowy rekord Item z `grade=Grand` zamiast aktualizować istniejący z poprawnym grade. Constraint `uq_item_name_grade` zapobiega duplikatom dla tego samego grade, ale tworzy nowe rekordy z nieprawidłowym grade. Frontend wyświetla ceny z przypisaniem do złego grade. `match_or_create_item` w `ingest/services.py:20` tworzy Item z `category=OTHER` i nieprawidłowym grade.
- **Sugestia (bez implementacji):** Dodaj pole `grade` do WATCHLIST w Lua lub stwórz mapę `name → grade` w addonie. Odczytaj grade z informacji o przedmiocie w grze (`X2Auction:GetSearchedItemInfo`).
- **Powiązane:** `backend/app/ingest/services.py:20-56`, `backend/app/ingest/grade_map.py`

### [🟠] OpenAPI schema `UserRead` nie zgadza się z rzeczywistą odpowiedzią backendu
- **Lokalizacja:** `backend/app/auth/schemas.py:8-15`, `frontend/src/lib/api.d.ts:687-714`
- **Problem:** `UserRead` ma `@model_serializer(mode="wrap")` który usuwa `is_superuser`, `is_active`, `is_verified` z odpowiedzi JSON. Ale OpenAPI schema (wygenerowana wcześniej) nadal deklaruje te pola jako obecne i wymagane. Frontendowe typy `UserRead` z `api.d.ts` zawierają te pola, mimo że backend ich nie zwraca.
- **Dlaczego to problem:** TypeScript nie zgłosi błędu, jeśli frontend odczyta `user.data?.is_superuser` — dostanie `undefined` zamiast oczekiwanej wartości. Gdyby ktoś polegał na tych polach (np. do warunkowego renderowania panelu admina), dostałby fałszywy wynik. Generowanie `api.d.ts` z żywego serwera nadpisze obecną wersję i usunie te pola — ale wtedy frontendowe typy będą poprawne.
- **Sugestia (bez implementacji):** Zregeneruj `api.d.ts` po uruchomieniu backendu (`npm run gen:types`), lub dodaj `is_superuser`/`is_active`/`is_verified` do serializer'a jeśli frontend ich potrzebuje.
- **Powiązane:** `frontend/src/lib/types.ts:21`

### [🟠] Frontend pomija `credentials: 'include'` na publicznych endpointach — niekonsekwencja
- **Lokalizacja:** `frontend/src/routes/items/[id]/+page.svelte:102,120,133`
- **Problem:** Wywołania `fetch` dla `/items/{id}`, `/items/{id}/price-history` i `/crafting/{id}/calculate` nie zawierają `credentials: 'include'`. Tymczasem wywołania dla `/inventory/` i `/inventory/for-recipe/{id}` w tym samym pliku zawierają. W `ItemTable.svelte:97-98` wywołanie `/items/` zawiera `credentials: 'include'`.
- **Dlaczego to problem:** Endpointy `/items/*` i `/crafting/*` są publiczne, więc brak `credentials` nie powoduje błędu. Ale jest to niekonsekwencja — jeśli w przyszłości te endpointy wymagałyby auth, część wywołań przestanie działać. Dodatkowo, brak cookie w requestach publicznych oznacza, że serwer nie może logować działań zalogowanego użytkownika.
- **Sugestia (bez implementacji):** Dodaj `credentials: 'include'` do wszystkich wywołań fetch w spójny sposób, lub stwórz helper `apiFetch()` który dodaje to automatycznie.

### [🟡] Frontendowa GRADES lista zawiera "All", które nie jest rzeczywistym grade Item
- **Lokalizacja:** `frontend/src/lib/components/ItemTable.svelte:41`, `frontend/src/routes/inventory/+page.svelte:15-17`
- **Problem:** `GRADES` w `ItemTable.svelte` zawiera `'All'` jako pierwszy element. `ItemGrade` w backendzie definiuje `"All"` jako enum value, ale żaden Item w DB nie ma `grade=All` — to wartość filtrująca. Problem: `ItemTable` wysyła `grade=All` jako parametr query do backendu, a `ItemGrade.ALL = "All"` jest poprawnym enum value, więc backend go przyjmie ale nie zwróci wyników (bo żaden Item nie ma tego grade). W `inventory/+page.svelte` lista GRADES nie zawiera "All", co jest poprawne.
- **Dlaczego to problem:** Filtr "All" w `ItemTable` wysyła `grade=All` do API, ale backend traktuje to jako filtr po `grade="All"` — co nie pasuje do żadnego Item. W praktyce frontend nie wysyła "All" bo ma warunek `if (selectedGrade && selectedGrade !== 'All')`. Ale obecność "All" w GRADES jest myląca i polega na ukrytym warunku w kodzie.
- **Sugestia (bez implementacji):** Rozdziel typ filtra (z "All") od typu API (bez "All"), lub dodaj obsługę `grade=All` w backendzie jako "bez filtra".

### [🟡] Ingest endpoint nie ma autoryzacji — tylko rate limiting
- **Lokalizacja:** `backend/app/ingest/router.py:12-19`
- **Problem:** `POST /api/ingest/prices` jest publiczny — nie wymaga tokena ani cookie. Zabezpieczeniem jest tylko rate limit 60/minute per IP. Bot i addon korzystają z tego endpointu bez auth, co jest zgodne z architekturą.
- **Dlaczego to problem:** Każdy kto pozna URL endpointu może wysyłać fałszywe ceny. Rate limit 60/min per IP jest jedyną ochroną. W środowisku produkcyjnym, atakujący z wielu IP mógłby zalać DB fałszywymi danymi. Bot wysyła requesty z wewnętrznej sieci Docker, więc jego IP jest stałe i rate limit nie blokuje go.
- **Sugestia (bez implementacji):** Rozważ dodanie prostego API key (header `X-Ingest-Key`) shared między addonem/botem, lub limituj ingest do requestów z wewnętrznej sieci Docker w produkcji.

### [🟡] `openapi-typescript` generowanie typów — brak automatyzacji w CI
- **Lokalizacja:** `frontend/package.json:13`, `frontend/src/lib/api.d.ts`
- **Problem:** `npm run gen:types` generuje `api.d.ts` z `http://localhost:8000/openapi.json`. Plik jest commitowany do repo. Jeśli backend doda nowy endpoint lub zmieni schema, `api.d.ts` nie zaktualizuje się automatycznie — trzeba ręcznie uruchomić komendę.
- **Dlaczego to problem:** `api.d.ts` jest już nieaktualne (patrz finding o `UserRead`). Brak CI stepa który weryfikuje synchronizację. Deweloper może zapomnieć o regeneracji po zmianie backend schema.
- **Sugestia (bez implementacji):** Dodaj CI step porównujący wygenerowane typy z commitowanymi, lub przenieś generowanie do pre-commit hook.

### [🟢] Bot Discord poprawnie używa tego samego kontraktu co addon/frontend
- **Lokalizacja:** `discord_bot/cogs/prices.py:80-106`
- **Problem:** Brak — to pozytywne spostrzeżenie. Bot wysyła `{rows: [{name, grade, price, ts, source}]}` do `/api/ingest/prices`, co jest zgodne z `IngestRequest` schema. `source="ah"` jest spójny. Bot mapuje grade 0-11 tak samo jak `grade_map.py`. Odpowiedź `IngestResponse` jest poprawnie obsługiwana — bot sprawdza `accepted` i wyciąga `errors[0].reason`.
- **Dlaczego to problem:** N/A — spójny kontrakt.
- **Sugestia (bez implementacji):** N/A

### [🟢] CORS poprawnie skonfigurowany dla dev i prod
- **Lokalizacja:** `backend/app/main.py:32-38`, `backend/app/config/settings.py:20-22`, `infra/compose/docker-compose.dev.yml:32`, `infra/compose/docker-compose.prod.yml:30`
- **Problem:** Brak. Dev: `CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]`. Prod: `CORS_ORIGINS=["https://${APP_DOMAIN}","https://${APP_WWW_DOMAIN}"]`. `allow_credentials=True` jest wymagany dla cookie-based auth. `allow_methods=["*"]` i `allow_headers=["*"]` są szerokie ale akceptowalne.
- **Dlaczego to problem:** N/A
- **Sugestia (bez implementacji):** N/A

### [🟢] Cookie/JWT flow jest spójny między frontendem a backendem
- **Lokalizacja:** `backend/app/auth/backend.py:9-16`, `frontend/src/lib/auth.svelte.ts:56-61`
- **Problem:** Brak. Backend używa `CookieTransport(cookie_max_age=3600, cookie_secure=settings.cookie_secure)` z `JWTStrategy(lifetime_seconds=3600)`. Dev: `cookie_secure=False`. Prod: `cookie_secure=True` (z compose). Frontend używa `credentials: 'include'` na wszystkich endpointach auth. Login wysyła `application/x-www-form-urlencoded` (wymagane przez fastapi-users OAuth2 password flow).
- **Dlaczego to problem:** N/A
- **Sugestia (bez implementacji):** N/A

### [💡] Helper `apiFetch()` centralizujący konfigurację fetch
- **Lokalizacja:** `frontend/src/lib/` (wzorzec, wiele miejsc)
- **Problem:** Fetch calls w komponentach powtarzają `API_BASE_URL`, `credentials: 'include'`, headers, error handling. Brak centralnego helpera.
- **Dlaczego to problem:** Duplikacja kodu, ryzyko niekonsekwencji (jak zauważono w findingach powyżej). Łatwo zapomnieć o `credentials` lub `Content-Type`.
- **Sugestia (bez implementacji):** Stwórz `apiFetch(path, options)` w `src/lib/api.ts` który automatycznie dodaje base URL, credentials, i standardowy error handling. Używaj go wszędzie zamiast bezpośredniego `fetch()`.


================================================================================
# SOURCE: audit/security/findings.md
================================================================================

# Security — findings

## Podsumowanie

Projekt ArcheRage Market Tracker ma solidne fundamenty bezpieczeństwa: .env pliki nie są trackowane w git, input validation jest konsekwentna przez Pydantic, SQLModel/SQLAlchemy chroni przed SQL injection, a Svelte automatycznie escapuje output (brak `{@html}`). Kluczowe problemy to: brak rate limitingu na endpointach logowania/rejestracji (podatność na brute-force), `cookie_secure=False` jako domyślne ustawienie (JWT cookie wysyłane przez HTTP), brak walidacji `display_name` w Pydantic schema (choć model ma `max_length`), oraz CORS `allow_methods=["*"]` i `allow_headers=["*"]` które są zbyt liberalne. Overall projekt jest dobrze zabezpieczony na poziomie architektury, ale wymaga kilku poprawek hardeningowych.

## Findings

### 🟠 Brak rate limitingu na endpointach auth (login/register)
- **Lokalizacja:** `backend/app/auth/router.py:8-22` (wzorzec — fastapi-users router bez limitów)
- **Problem:** Endpointy `/api/auth/login`, `/api/auth/register` nie mają żadnego rate limitingu. Tylko `/api/ingest/prices` i `POST /api/items/{id}/prices` mają `@limiter.limit("60/minute")`.
- **Dlaczego to problem:** Atakujący może wykonywać nieograniczoną liczbę prób logowania (brute-force credentials) i rejestracji (spam kont). Brak ochrony przed credential stuffing i automated account creation.
- **Sugestia (bez implementacji):** Dodać `@limiter.limit("5/minute")` na login i `@limiter.limit("3/minute")` na register. Wymaga podpięcia dekoratorów do fastapi-users router lub napisania customowego endpoint wrapper.

### 🟠 `cookie_secure=False` jako domyślne — JWT cookie przez HTTP
- **Lokalizacja:** `backend/app/config/settings.py:16`, `backend/app/auth/backend.py:9-12`
- **Problem:** `cookie_secure` domyślnie `False`. `CookieTransport` z fastapi-users wysyła JWT cookie bez flagi `Secure`. W dev compose brak ustawienia `COOKIE_SECURE`.
- **Dlaczego to problem:** Cookie z tokenem JWT jest transmitowane cleartext po HTTP. W środowisku produkcyjnym (docker-compose.prod.yml) jest ustawione `COOKIE_SECURE: "true"`, ale jeśli ktoś uruchomi poza compose lub zapomni, cookie będzie niezabezpieczone. Dodatkowo `CookieTransport` z fastapi-users nie ustawia domyślnie `httponly` — trzeba to zweryfikować.
- **Sugestia (bez implementacji):** Zmienić domyślną wartość `cookie_secure` na `True` (wymusić HTTPS w produkcji). Rozważyć explicit `httponly=True` i `samesite="lax"` w konfiguracji cookie transportu.

### 🟡 CORS `allow_methods=["*"]` i `allow_headers=["*"]` — zbyt liberalne
- **Lokalizacja:** `backend/app/main.py:32-38`
- **Problem:** CORS middleware akceptuje wszystkie metody HTTP (`*`) i wszystkie nagłówki (`*`). `allow_credentials=True` jest włączone.
- **Dlaczego to problem:** Zasada least privilege — backend używa tylko GET, POST, PUT, PATCH, DELETE. Akceptowanie wszystkich metod (w tym OPTIONS, HEAD, TRACE) i wszystkich nagłówków zwiększa powierzchnię ataku. Z `allow_credentials=True` i wildcard, atakujący z cross-origin mógłby wykonywać credentialed requests do API.
- **Sugestia (bez implementacji):** Zawęzić do `allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"]` i `allow_headers=["Content-Type", "Authorization"]` (lub inne faktycznie używane).

### 🟡 Brak walidacji `max_length` w Pydantic schema dla `display_name` i `avatar_url`
- **Lokalizacja:** `backend/app/profiles/schemas.py:19-22` (`ProfileUpdate`)
- **Problem:** `ProfileUpdate` schema nie ma walidacji `max_length` dla `display_name` i `avatar_url`. Model DB (`profiles/models.py:15`) ma `max_length=80` dla `display_name`, ale `avatar_url` nie ma żadnego limitu.
- **Dlaczego to problem:** Pydantic nie ogranicza długości inputu — dopiero DB rzuci błąd przy insercie. To nie jest krytyczne (DB ochroni), ale lepiej walidować wcześniej. Brak limitu na `avatar_url` pozwala na wstrzyknięcie bardzo długiego stringa.
- **Sugestia (bez implementacji):** Dodać `Field(max_length=80)` do `display_name` i `Field(max_length=2000)` do `avatar_url` w `ProfileUpdate`. Rozważyć walidację URL dla `avatar_url`.

### 🟡 Brak CSRF protection — JWT w cookie bez explicit CSRF token
- **Lokalizacja:** `backend/app/auth/backend.py:9-12` (CookieTransport), `frontend/src/lib/auth.svelte.ts` (credentials: 'include')
- **Problem:** Autoryzacja opiera się na JWT cookie wysyłanym z `credentials: 'include'`. FastAPI nie ma domyślnej ochrony CSRF. CORS partially chroni (tylko dozwolone origins mogą robić credentialed requests), ale CORS nie jest pełną ochroną CSRF.
- **Dlaczego to problem:** Jeśli atakujący znajdzie sposób na wywołanie cross-origin request (np. przez form submission — POST z form nie jest blokowany przez CORS preflight), może wykonać akcje w imieniu zalogowanego użytkownika. `SameSite=Lax` na cookie (domyślne w nowoczesnych przeglądarkach) partially chroni, ale nie jest to guarantee.
- **Sugestia (bez implementacji):** Rozważyć dodanie CSRF token pattern lub upewnienie się że cookie ma `SameSite=Strict`. Alternatywnie, użyć header-based auth (Bearer token) zamiast cookie.

### 🟡 Brak Content-Security-Policy i innych security headers
- **Lokalizacja:** `infra/caddy/Caddyfile` (brak security headers)
- **Problem:** Caddyfile nie konfiguruje żadnych security headers: CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Strict-Transport-Security.
- **Dlaczego to problem:** Brak CSP pozwala na inline script injection jeśli XSS zostanie znalezione. Brak X-Frame-Options pozwala na clickjacking. Brak HSTS pozwala na downgrade attacks.
- **Sugestia (bez implementacji):** Dodać w Caddyfile blok `header` z `X-Content-Type-Options "nosniff"`, `X-Frame-Options "DENY"`, `Referrer-Policy "strict-origin-when-cross-origin"`, `Strict-Transport-Security "max-age=31536000"`, oraz odpowiednie CSP.

### 🟡 Rate limiter oparty na IP — bypass za proxy
- **Lokalizacja:** `backend/app/config/rate_limit.py:4`
- **Problem:** `get_remote_address` z slowapi czyta bezpośrednio z connection IP. Za reverse proxy (Caddy), wszystkie requesty mają IP proxy jako source.
- **Dlaczego to problem:** W produkcji za Caddy, rate limiter będzie limitował per IP proxy (czyli effectively per serwer), nie per rzeczywisty klient. Wszyscy użytkownicy sharingują ten sam limit.
- **Sugestia (bez implementacji):** Skonfigurować slowapi do czytania z `X-Forwarded-For` header (z zaufanym proxy). Np. custom key_func: `request.headers.get("X-Forwarded-For", request.client.host)`.

### 🟡 Brak limitu rozmiaru batch ingest — potencjalny DoS
- **Lokalizacja:** `backend/app/ingest/schemas.py:14-15` (`IngestRequest`)
- **Problem:** `IngestRequest` ma `max_length=100` na rows, ale każda iteracja wykonuje osobny DB query (SELECT + INSERT/UPSERT). Przy 100 rowach to 200+ DB operations per request.
- **Dlaczego to problem:** Przy 60 req/min rate limit, atakujący może generować 6000 DB operations/min. To może obciążyć bazę danych. Dodatkowo, brak timeout na poszczególne operacje w batch.
- **Sugestia (bez implementacji):** Rozważyć zmniejszenie `max_length` do np. 50 lub dodanie timeout per-row. Lub dodać rate limit per-user (nie per-IP) dla ingest.

### 🟢 `UserRead` serializer ukrywa pola ale nie chroni przed wyciekiem w innych kontekstach
- **Lokalizacja:** `backend/app/auth/schemas.py:8-15`
- **Problem:** `UserRead` serializer usuwa `is_superuser`, `is_active`, `is_verified` z response. To dobre praktyki, ale `UserRead` jest używany tylko w auth router.
- **Dlaczego to problem:** Niskie ryzyko — jeśli nowy endpoint zostanie dodany i użyje `User` model bezpośrednio (nie `UserRead`), pola wyciekną. Ale obecnie jest OK.
- **Sugestia (bez implementacji):** Upewnić się, że wszystkie endpointy zwracające user data używają `UserRead` schema.

### 🟢 Brak walidacji `source` field — potential data pollution
- **Lokalizacja:** `backend/app/ingest/schemas.py:11`, `backend/app/prices/schemas.py:23`
- **Problem:** `source` field akceptuje dowolny string do 40 znaków. Oczekiwane wartości to `"ah"` (auction house), ale nic nie ogranicza do tych wartości.
- **Dlaczego to problem:** Użytkownik może ingestować ceny z dowolnym source (np. `"fake"`, `"test"`), co zanieczyści dane. Frontend filtruje po `source='ah'`, ale inne source'y mogą być użyte do manipulacji.
- **Sugestia (bez implementacji):** Rozważyć walidację source do dozwolonych wartości (enum lub whitelist) lub dodać constraint w DB.

### 💡 Rozdzielenie `auth_secret` i `reset_password_token_secret`
- **Lokalizacja:** `backend/app/auth/manager.py:15-16`
- **Problem:** `reset_password_token_secret` i `verification_token_secret` używają tego samego `settings.auth_secret` co JWT strategy.
- **Dlaczego to problem:** Jeśli jeden secret zostanie skompromitowany, wszystkie tokeny (JWT, reset password, verification) są zagrożone. Best practice to separacja secretów.
- **Sugestia (bez implementacji):** Dodać osobne secrete w settings dla reset password i verification (np. `reset_password_secret`, `verification_secret`).

### 💡 Brak audit log dla zmian admina
- **Lokalizacja:** `backend/app/admin.py`, `backend/app/admin_auth.py`
- **Problem:** Panel admina (sqladmin) nie loguje żadnych operacji. Zmiany w itemach, cenach, userach są wykonywane bez trail.
- **Dlaczego to problem:** Brak możliwości śledzenia kto co zmienił w panelu admina. W przypadku incydentu bezpieczeństwa, brak dowodów.
- **Sugestia (bez implementacji):** Rozważyć dodanie audit log middleware dla admin operacji lub włączenie SQL echo w logach dla admin requests.

### 💡 Frontend nie weryfikuje struktury API response
- **Lokalizacja:** `frontend/src/lib/auth.svelte.ts`, `frontend/src/routes/items/[id]/+page.svelte`
- **Problem:** Frontend aszuje, że API response ma oczekiwaną strukturę (`await response.json()` bez walidacji). Użyte są TypeScript type assertions (`as ItemListItem[]`).
- **Dlaczego to problem:** TypeScript types istnieją tylko w compile-time. Jeśli API zwróci unexpected data shape, frontend może crashować lub wyświetlać undefined wartości. Niskie ryzyko security, ale potencjalny DoS na frontend.
- **Sugestia (bez implementacji):** Rozważyć runtime validation (np. zod) dla critical API responses lub graceful fallback.


================================================================================
# SOURCE: audit/dependencies/findings.md
================================================================================

# Dependencies — findings

## Podsumowanie

Projekt używa nowoczesnych wersji większości zależności (FastAPI 0.136, SvelteKit 2.57, SQLAlchemy 2.0.49). Lock file'y backendu i discord_bota są spójne z pyproject.toml. Frontend ma 6 pakietów ekstraneous w package-lock.json oraz znaną podatność LOW na `cookie<0.7.0` (pośrednio przez `@sveltejs/kit`). `svelte-echarts` blokuje upgrade `echarts` do wersji 6.x. Python 3.13 i Node 22 LTS są wspierane, ale projekt nie deklaruje engines w `package.json`.

## Findings

### [🟠] Znana podatność w `cookie` (GHSA-pxg6-pf52-xh8x)
- **Lokalizacja:** `frontend/package-lock.json` (cookie 0.6.0 via @sveltejs/kit 2.57.1)
- **Problem:** `cookie<0.7.0` akceptuje nazwy, path i domain ze znakami poza zakresem. Advisory: GHSA-pxg6-pf52-xh8x.
- **Dlaczego to problem:** Niska podatność (severity: low), ale zależność jest pośrednia — kontroluje ją `@sveltejs/kit`. Nowsze wersje Kit-a (≥2.60) mogą już zależeć od poprawionej wersji.
- **Sugestia (bez implementacji):** Zaktualizować `@sveltejs/kit` do ^2.60.1 i zweryfikować, czy cookie ≥0.7.0 jest rozwiązywane. Alternatywnie poczekać na upstream fix.

### [🟡] `svelte-echarts` blokuje upgrade `echarts` do 6.x
- **Lokalizacja:** `frontend/package.json:29` (echarts ^5.6.0), `frontend/node_modules/svelte-echarts/package.json` (peerDep: echarts ^5.0.0)
- **Problem:** `svelte-echarts@1.0.0` deklaruje `peerDependencies: { echarts: "^5.0.0" }`. Najnowszy echarts to 6.1.0 (major breaking changes).
- **Dlaczego to problem:** Nie można zaktualizować echarts do 6.x bez naruszenia peer dependency. Brak aktualizacji oznacza brak nowych funkcji i potencjalnych poprawek z echarts 6.
- **Sugestia (bez implementacji):** Monitorować `svelte-echarts` pod kątem wersji kompatybilnej z echarts 6.x, lub rozważyć alternatywne wrappery (np. własny komponent Svelte + echarts).

### [🟡] 6 pakietów ekstraneous w `frontend/package-lock.json`
- **Lokalizacja:** `frontend/package-lock.json` + `frontend/node_modules/`
- **Problem:** Pakiety `@emnapi/core`, `@emnapi/runtime`, `@emnapi/wasi-threads`, `@napi-rs/wasm-runtime`, `@tybys/wasm-util`, `tslib` są w lockfile/node_modules, ale nie są zadeklarowane w `package.json`. To zależności build-time (rolldown/rollup WASM bindings), które wyciekły do runtime lockfile.
- **Dlaczego to problem:** Zwiększa rozmiar `node_modules`, utrudnia audyt, może powodować niekonsekwencje między środowiskami. `npm ls` raportuje je jako extraneous.
- **Sugestia (bez implementacji):** Wykonać `rm -rf node_modules && npm install` lub `npm ci` aby wyczyścić. Sprawdzić, czy `package-lock.json` nie jest generowany z dodatkowymi flagami. Rozważyć dodanie `.npmrc` z `omit=optional` jeśli te pakiety nie są potrzebne w runtime.

### [🟡] Frontend: `package.json` nie deklaruje `engines`
- **Lokalizacja:** `frontend/package.json`
- **Problem:** Brak pola `engines` określającego wymagane wersje Node/npm. Dockerfile używa `node:22-alpine`, ale nie ma gwarancji kompatybilności z innymi wersjami.
- **Dlaczego to problem:** Deweloper z inną wersją Node (np. 20 lub 24) może napotkać niekompatybilności bez ostrzeżenia. Brak formalnego pinnowania wersji.
- **Sugestia (bez implementacji):** Dodać `"engines": { "node": ">=22" }` do `package.json`. Rozważyć `.nvmrc` lub `.node-version` dla automatycznego przełączania wersji.

### [🟡] Wiele zależności frontend nieaktualnych (minor/patch)
- **Lokalizacja:** `frontend/package.json`, `frontend/package-lock.json`
- **Problem:** `npm outdated` pokazuje: @sveltejs/kit 2.57.1→2.60.1, @sveltejs/vite-plugin-svelte 7.0.0→7.1.2, @tailwindcss/vite 4.2.2→4.3.0, daisyui 5.5.19→5.5.20, svelte 5.55.7→5.55.9, svelte-check 4.4.6→4.4.8, tailwindcss 4.2.2→4.3.0, typescript 6.0.2→6.0.3, vite 8.0.8→8.0.13.
- **Dlaczego to problem:** Brak poprawek bezpieczeństwa i bugfixów zawartych w nowszych wersjach. Różnice są niewielkie (minor/patch), ale kumulują się.
- **Sugestia (bez implementacji):** Zaktualizować `^` ranges i wykonać `npm update`. Priorytet: @sveltejs/kit (wiąże się z poprawką cookie) i vite (security patches).

### [🟢] Python 3.13 — wspierany, ale nie najnowszy
- **Lokalizacja:** `backend/.python-version`, `backend/Dockerfile`, `discord_bot/Dockerfile`, `backend/pyproject.toml:6`, `discord_bot/pyproject.toml:5`
- **Problem:** Projekt wymaga Python ≥3.13. Python 3.14 jest już wydany (system używa 3.14.3). Python 3.13 ma wsparcie do października 2029.
- **Dlaczego to problem:** Brak ryzyka bezpieczeństwa (3.13 jest wspierany), ale projekt nie korzysta z nowości 3.14 (np. improved error messages, performance). Niska priorytetowość.
- **Sugestia (bez implementacji):** Rozważyć upgrade do 3.14 po stabilizacji, ale nie jest pilne.

### [🟢] Node 22 LTS — wspierany
- **Lokalizacja:** `frontend/Dockerfile`, `infra/compose/docker-compose.dev.yml:44`
- **Problem:** Node 22 jest w fazie Active LTS do października 2025, potem Maintenance LTS do kwietnia 2027. Dockerfile używa `node:22-alpine`.
- **Dlaczego to problem:** Brak bieżącego ryzyka. Po kwietniu 2027 będzie wymagany upgrade do Node 24 (LTS od października 2025) lub nowszego.
- **Sugestia (bez implementacji):** Monitorować datę przejścia na Maintenance LTS. Rozważyć dodanie `.node-version` lub `.nvmrc`.

### [🟢] Lock file'y backendu i discord_bota spójne
- **Lokalizacja:** `backend/uv.lock`, `discord_bot/uv.lock`
- **Problem:** `uv lock --check` przechodzi pomyślnie dla obu projektów. Wersje w lock file'ach są zgodne z deklaracjami w pyproject.toml.
- **Dlaczego to problem:** Brak — to pozytywny wynik. Brak drifting dependencies.
- **Sugestia (bez implementacji)::** Utrzymywać regularne `uv lock --upgrade` w ramach rutynowego utrzymania.

### [🟢] Brak znanych CVE w zależnościach backendu (weryfikacja manualna)
- **Lokalizacja:** `backend/uv.lock`
- **Problem:** Kluczowe pakiety (cryptography 48.0.0, starlette 1.0.0, sqlalchemy 2.0.49, jinja2 3.1.6, fastapi 0.136.1, pydantic 2.13.4) — brak publicznie znanych CVE dla tych wersji w dniu audytu (2026-05-20).
- **Dlaczego to problem:** Brak — pozytywny wynik. Należy monitorować w przyszłości.
- **Sugestia (bez implementacji):** Dodać `uv pip audit` (gdy uv doda obsługę) lub `pip-audit` do CI pipeline.

### [💡] `slowapi` — mała społeczność, potencjalne ryzyko utrzymania
- **Lokalizacja:** `backend/pyproject.toml:17` (slowapi>=0.1.9)
- **Problem:** `slowapi` (0.1.9) to mały projekt z niewielką społecznością. Alternatywa: wbudowane rate limiting w Starlette/FastAPI lub dedykowane rozwiązanie (np. `fastapi-limiter`).
- **Dlaczego to problem:** Długoterminowe ryzyko: brak aktualizacji, niekompatybilność z nowymi wersjami Starlette. Obecnie działa poprawnie.
- **Sugestia (bez implementacji):** Monitorować aktywność projektu. Jeśli stanie się nieaktywny, rozważyć migrację do `fastapi-limiter` lub własnej implementacji.

### [💡] Brak `pip-audit` / `npm audit` w CI
- **Lokalizacja:** brak (dotyczy pipeline CI)
- **Problem:** Projekt nie ma zautomatyzowanego skanowania podatności w zależnościach. `npm audit` znalazł podatność cookie, ale tylko dlatego że ręcznie uruchomiono audyt.
- **Dlaczego to problem:** Nowe CVE w zależnościach nie będą wykryte automatycznie. Ryzyko: deploy z podatnymi pakietami.
- **Sugestia (bez implementacji):** Dodać `npm audit --audit-level=moderate` do CI frontendu. Dla backendu: `pip-audit` lub `safety check` w kontenerze. Rozważyć Dependabot/Renovate dla automatycznych PR-ów z aktualizacjami.


================================================================================
# SOURCE: audit/code-quality/findings.md
================================================================================

# Code Quality — findings

## Podsumowanie

Kod jest generalnie dobrze zorganizowany — modularna struktura backendu, spójne wzorce serwis/router, dobre pokrycie testami integracyjnymi. Głównym problemem jest **znacząca duplikacja kodu** w trzech obszarach: helper `utcnow()` powtórzony w 4 modelach, funkcja `computeNodeCost()` skopiowana między 3 komponentami Svelte, oraz fixture'y testowe (`db_session`, `_email()`, `auth_client`) powtórzone w każdym pliku testowym zamiast w `conftest.py`. Istnieje też martwy kod po niekompletnym refaktoringu (`admin_auth.py`), brak scentralizowania stałych frontendowych (CATEGORIES, GRADES), oraz brak testów dla logiki bucketowania cen i frontendu jako całości.

## Findings

### [🟠] Potrójna duplikacja `computeNodeCost()` w frontend
- **Lokalizacja:** `frontend/src/routes/items/[id]/+page.svelte:36-53`, `frontend/src/lib/components/crafting/RecipeTree.svelte:19-33`, `frontend/src/lib/components/crafting/RecipeCard.svelte:35-54` (`sumLabour` — ten sam wzorzec)
- **Problem:** Identyczna rekurencyjna logika obliczania kosztu węzła craftingu jest skopiowana w 3 plikach. `sumLabour` w `RecipeCard.svelte` ma ten sam szkielet co `computeNodeCost` — iteracja po dzieciach z obliczaniem `childScale`.
- **Dlaczego to problem:** Zmiana algorytmu (np. obsługa nowego typu węzła) wymaga edycji 3 plików. Ryzyko rozjechania się logik — już teraz `RecipeCard` ma `sumLabour` jako osobną funkcję zamiast używać wspólnej.
- **Sugestia:** Wyekstrahuj `computeNodeCost` do `$lib/crafting.ts` jako modułową funkcję. `sumLabour` może przyjmować dodatkowy parametr (predykat co sumować) lub korzystać z tego samego drzewa.

### [🟠] Czwórna duplikacja `utcnow()` w modelach backend
- **Lokalizacja:** `backend/app/items/models.py:7-8`, `backend/app/prices/models.py:6-7`, `backend/app/user_items/models.py:7-8`, `backend/app/profiles/models.py:7-8`
- **Problem:** Identyczna funkcja `utcnow()` zdefiniowana w 4 osobnych plikach:
  ```python
  def utcnow() -> datetime:
      return datetime.now(timezone.utc).replace(tzinfo=None)
  ```
- **Dlaczego to problem:** Zmiana zasada "naive UTC" wymaga edycji 4 plików. Ryzyko وحتi jednego miejsca. CLAUDE.md mówi "Naive UTC everywhere" ale implementacja jest rozproszona.
- **Sugestia:** Umieść `utcnow()` w `app/config/utils.py` lub `app/config/db.py` i importuj wszędzie.

### [🟠] Duplikacja fixture'ów testowych — `db_session`, `_email()`, `auth_client`
- **Lokalizacja:** `backend/tests/test_ingest.py:19-27`, `backend/tests/test_crafting.py:15-23`, `backend/tests/test_items.py:13-21`, `backend/tests/test_user_items.py:18-26`, `backend/tests/test_prices.py:14-22`, `backend/tests/test_inventory.py:20-30` + `_email()` w 5 plikach
- **Problem:** Ten sam fixture `db_session` (create_async_engine + NullPool + async_sessionmaker) jest kopiowany do każdego pliku testowego. Funkcja `_email()` powtórzona w 5 plikach. Fixture `auth_client` (register + login) powtórzony w 4 plikach.
- **Dlaczego to problem:** Zmiana sposobu tworzenia sesji testowej wymaga edycji 6+ plików. Łatwo pominąć jeden. Kod jest zbędnie długi.
- **Sugestia:** Przenieś `db_session`, `_email()` i `auth_client` do `conftest.py` (już istnieje na poziomie `tests/`). Każdy test importuje automatycznie.

### [🟠] Duplikacja stałych CATEGORIES/GRADES w frontend
- **Lokalizacja:** `frontend/src/lib/components/ItemTable.svelte:34-43`, `frontend/src/routes/inventory/+page.svelte:10-18`
- **Problem:** Listy kategorii i stopni (grades) są hardcodowane w dwóch komponentach. `ItemTable` ma `GRADES` bez `'Basic'`, `inventory/+page.svelte` ma pełną listę z `'Basic'`.
- **Dlaczego to problem:** Niespójność — `ItemTable` nie pokazuje `Basic` w filtrze grade, ale inventory pokazuje. Dodanie nowej kategorii/stopnia wymaga edycji wielu miejsc. Backend ma `ItemCategory` i `ItemGrade` jako single source of truth, ale frontend go nie importuje.
- **Sugestia:** Stwórz `$lib/constants.ts` z `CATEGORIES` i `GRADES` (lub eksportuj z `$lib/types.ts`), importuj w komponentach.

### [🟡] Martwy kod: podwójne nadpisanie `authentication_backend` w `admin_auth.py`
- **Lokalizacja:** `backend/app/admin_auth.py:46-68`
- **Problem:** Zmienna `authentication_backend` jest przypisana dwukrotnie — raz na linii 46 (`AdminAuth`), a potem nadpisana na linii 67 (`SecureAdminAuth`). Klasa `AdminAuth` na linii 46 jest tworzona i natychmiast porzucona. Dodatkowo `SecureAdminAuth` dziedziczy po `AdminAuth` i tworzy middleware, ale `AdminAuth` (rodzic) ma swoje `login`/`authenticate` które nie korzystają z tych middleware.
- **Dlaczego to problem:** Kod jest mylący — wygląda na niekompletny refaktoring. Linia 46 to dead code. `SecureAdminAuth.middlewares` nie jest nigdzie używane (sqladmin nie korzysta z tego atrybutu w ten sposób).
- **Sugestia:** Usuń pierwsze przypisanie (linia 46). Przejrzyj czy `SecureAdminAuth` rzeczywiście działa poprawnie z sqladmin — jeśli nie, uprość do jednej klasy.

### [🟡] Martwy kod: `ItemFilter` schema nigdzie nie użyta
- **Lokalizacja:** `backend/app/items/schemas.py:34-36`
- **Problem:** Klasa `ItemFilter(BaseModel)` z polami `category` i `grade` nie jest importowana ani używana w żadnym innym pliku.
- **Dlaczego to problem:** Zbędny kod, który może mylić deweloperów (wygląda jak coś co powinno być użyte w routerze).
- **Sugestia:** Usuń lub zastąp inline'owe parametry w routerze.

### [🟡] Martwy kod: `col` import w `items/services.py`
- **Lokalizacja:** `backend/app/items/services.py:1`
- **Problem:** `col` jest importowane z sqlmodel i używane w `col(Item.name).ilike(...)`, ale `Item.name` ma `index=True` — sqlmodel powinien obsługiwać to bez `col()`. Sam `col` jest użyty, ale `func` (również importowany) nie jest potrzebny w `items/services.py` poza `count`.
- **Dlaczego to problem:** `func` jest importowane ale użyte tylko raz. Nie jest to krytyczne, ale `col()` jest zbędne — `Item.name.ilike(...)` działa bezpośrednio.
- **Sugestia:** Usuń `col` z importu, użyj `Item.name.ilike(...)` bezpośrednio.

### [🟡] Brak scentralizowania helpera `format_price` — duplikacja logiki walutowej
- **Lokalizacja:** `discord_bot/cogs/prices.py:29-41`, `frontend/src/lib/currency.ts:1-21`, `frontend/src/lib/components/ItemTable.svelte:279-311` (inline formatting)
- **Problem:** Trzy niezależne implementacje formatowania ceny (gold/silver/copper): Python w bocie, TypeScript w `currency.ts`, i inline w `ItemTable.svelte`. Bot używa `"3g 20s"`, frontend używa `"3g 20s 00b"` z HTML.
- **Dlaczego to problem:** Zmiana systemu walutowego (np. inny podział) wymaga edycji 3 miejsc. Ryzyko niespójności wizualnej.
- **Sugestia:** Zaakceptuj jako naturalny podział (Python vs TS), ale przynajmniej frontend powinien wszędzie używać `formatCurrency`/`splitCurrency` z `$lib/currency.ts` zamiast inline formatowania.

### [🟡] Brak testów dla logiki bucketowania cen (interval aggregation)
- **Lokalizacja:** `backend/app/prices/services.py:48-92`, `backend/tests/test_prices.py:144-198`
- **Problem:** Testy `test_get_price_history_1h_buckets` i `test_get_price_history_1d_buckets` istnieją, ale brakuje testów dla: edge case'u `5m` interval, pustych bucketów w środku zakresu, bucketowania z timezone-aware datetime, oraz zachowania gdy `interval` jest nieznany (brak walidacji — `INTERVAL_SECONDS[interval]` rzuci `KeyError`).
- **Dlaczego to problem:** Nieznany interval powoduje 500 zamiast 422. Brak testu dla tego scenariusza.
- **Sugestia:** Dodaj test dla nieznanego intervalu (oczekiwane 422 lub domyślne zachowanie). Rozważ walidację intervalu w routerze (już masz `Interval` enum ale serwis przyjmuje `str`).

### [🟡] Brak testów jednostkowych dla `grade_map.py`
- **Lokalizacja:** `backend/app/ingest/grade_map.py`
- **Problem:** `map_grade()` jest testowane pośrednio przez testy ingestu (grade=0, grade=1, grade=2), ale brakuje testu jednostkowego pokrywającego wszystkie 12 grade'ów + nieprawidłowe wejście.
- **Dlaczego to problem:** Pośrednie testy nie pokrywają edge case'ów (np. grade=-1, grade=12). Jeśli ktoś zmieni mapę, testy ingestu mogą przejść mimo błędu.
- **Sugestia:** Dodaj `test_grade_map.py` z testem dla każdego grade'u + `None` dla nieprawidłowych.

### [🟡] Niespójne nazewnictwo modułów: `user_inventory` vs `user_items`
- **Lokalizacja:** `backend/app/user_inventory/`, `backend/app/user_items/`
- **Problem:** Jeden moduł używa podkreślenia (`user_inventory`), drugi nie (`user_items`). API prefixy: `/inventory/` vs `/user-items/` — też niespójne.
- **Dlaczego to problem:** Konwencja nazewnicza nie jest jednolita. `/inventory/` sugeruje zasób globalny, ale jest per-user. `/user-items/` jawnie mówi "user".
- **Sugestia:** Ujednolicenie nazewnictwa (obydwa z `_` lub obydwa bez). Nie zmieniaj API prefixów bez potrzeby (breaking change), ale rozważ aliasy.

### [🟡] `load_all_items` i `load_all_recipes` ładują całą bazę bez limitu
- **Lokalizacja:** `backend/app/crafting/services.py:12-25`
- **Problem:** `load_all_recipes()` i `load_all_items()` robią `SELECT *` bez limitu. Używane w `calculate()` i `list_summaries()`. Przy dużej liczbie itemów (tysiące) to N+1 problem i zużycie pamięci.
- **Dlaczego to problem:** `list_summaries()` iteruje WSZYSTKIE recipes i buduje drzewo dla każdej — O(n * depth). Przy 1000 recipes to może być wolne.
- **Sugestia:** Na razie akceptowalne (gra ma ograniczoną liczbę itemów), ale dodaj paginację lub lazy loading gdy baza urośnie. Rozważ cache'owanie drzewa craftingowego.

### [🟢] `asyncio` import w `test_user_items.py` ale nie w innych testach concurrency
- **Lokalizacja:** `backend/tests/test_user_items.py:1`, `backend/tests/test_profiles.py:1`
- **Problem:** Testy concurrency (`test_follow_concurrent_is_idempotent`, `test_get_or_create_profile_concurrent`) importują `asyncio.gather`, ale robią to w odmienny sposób — `test_user_items` tworzy nowy engine w teście, `test_profiles` też. Brak spójnego wzorca.
- **Dlaczego to problem:** Drobna niespójność, ale testy działają poprawnie.
- **Sugestia:** Ewentualnie wyekstrahuj helper do `conftest.py` dla testów concurrency.

### [🟢] Brak `admin.py` dla modułów `user_inventory` i `user_items`
- **Lokalizacja:** `backend/app/user_inventory/`, `backend/app/user_items/`
- **Problem:** Te moduły nie mają plików `admin.py` — ich modele nie są widoczne w panelu admina sqladmin.
- **Dlaczego to problem:** Admin nie może zarządzać inventory użytkowników ani listą obserwowanych items przez panel.
- **Sugestia:** Dodaj `admin.py` z `ModelView` dla `UserInventory` i `UserItem` jeśli admin potrzebuje dostępu.

### [🟢] Synchroniczny engine w `db.py` użyty tylko przez admin
- **Lokalizacja:** `backend/app/config/db.py:12`
- **Problem:** `engine = create_engine(DATABASE_URL, ...)` tworzy synchroniczny engine, importowany tylko przez `app/admin.py`. Wszystkie serwisy i testy używają `async_engine`.
- **Dlaczego to problem:** sqladmin wymaga synchronicznego engine — to uzasadnione. Ale zbędny import w kontekście aplikacji w pełni async.
- **Sugestia:** OK jako workaround dla sqladmin. Dodaj komentarz wyjaśniający czemu sync engine istnieje.

### [💡] Eksport `CATEGORIES` i `GRADES` z backendu jako API endpoint
- **Lokalizacja:** `backend/app/items/models.py` (enumy), frontend (hardcoded listy)
- **Problem:** Frontend hardcoduje listy kategorii i stopni, które powinny być zsynchronizowane z backendowymi enumami.
- **Dlaczego to problem:** Dodanie nowej kategorii/stopnia wymaga zmiany zarówno backendu jak i frontendu w wielu miejscach.
- **Sugestia:** Rozważ endpoint `GET /api/items/categories` i `GET /api/items/grades` zwracające listy z enumów. Frontend pobiera raz i cache'uje.

### [💡] Brak testów frontendowych
- **Lokalizacja:** `frontend/` (brak katalogu `tests/` lub `__tests__/`)
- **Problem:** Żaden komponent Svelte ani strona nie ma testów jednostkowych ani integracyjnych.
- **Dlaczego to problem:** Logika `computeNodeCost`, `splitCurrency`, `formatCurrency`, filtrowanie w `ItemTable` — wszystko bez testów. Regresje w UI są wykrywane tylko ręcznie.
- **Sugestia:** Dodaj testy dla `$lib/currency.ts` (czyste funkcje, łatwe do testowania). Rozważ Playwright/Cypress dla krytycznych ścieżek.

### [💡] `ItemTable.svelte` — inline formatowanie zamiast `splitCurrency`
- **Lokalizacja:** `frontend/src/lib/components/ItemTable.svelte:279-311`
- **Problem:** Komponent importuje `splitCurrency` ale renderowanie gold/silver/bronze jest inline z powtarzanym wzorcem (`.toString().padStart(2, '0')`). Ten sam wzorzec jest w `items/[id]/+page.svelte:288-292`.
- **Dlaczego to problem:** Drobne, ale powtarzalny kod template'owy.
- **Sugestia:** Rozważ komponent `CurrencyDisplay.svelte` przyjmujący `copper: number`.

### [💡] `test_ingest.py` importuje `datetime, timezone` wewnątrz funkcji
- **Lokalizacja:** `backend/tests/test_ingest.py:320-321`, `backend/tests/test_ingest.py:362-363`
- **Problem:** Dwa testy (`test_ingest_price_appears_in_price_history`, `test_ingest_source_ah_does_not_appear_under_wrong_source`) importują `datetime, timezone` wewnątrz ciała funkcji, mimo że są już importowane na górze pliku (linia 3).
- **Dlaczego to problem:** Redundantny import, zbędny kod.
- **Sugestia:** Usuń lokalne importy, użyj globalnych z linii 3.


================================================================================
# SOURCE: audit/tester-evaluator/findings.md
================================================================================

# Test Evaluator — findings

## Podsumowanie

Backend ma solidne pokrycie testowe domeny (auth, items, prices, inventory, crafting, ingest) z sensownymi asercjami i testami edge-case. Discord bot jest dobrze przetestowany z mockingiem HTTP. Natomiast frontend nie ma **żadnych** testów — brak nawet konfiguracji test runnera. Kilka fixture'ów jest duplikowanych zamiast współdzielonych z conftest, test współbieżności w user_items ma za słabe asercje, a brakuje testów dla rate limiting, admin panelu i obsługi błędów.

## Findings

### [🔴] Frontend完全没有测试 — zero test coverage
- **Lokalizacja:** `frontend/package.json` (brak vitest/jest/playwright w devDependencies)
- **Problem:** Frontend SvelteKit 5 nie ma żadnych testów: ani unit, ani component, ani e2e. Brak konfiguracji test runnera w package.json.
- **Dlaczego to problem:** Każda zmiana w logice frontendowej (formatCurrency, store'y, routing, warunkowe renderowanie) może być zweryfikowana tylko ręcznie. Regresje UI są niewykrywalne przed deployem.
- **Sugestia (bez implementacji):** Dodać vitest + @testing-library/svelte dla unit/component testów. Minimum: testy dla `src/lib/` (shared utils, stores). Rozważyć Playwright dla krytycznych ścieżek (login, nawigacja, wykres cen).

### [🟠] Brak testów rate limiting
- **Lokalizacja:** `backend/app/config/rate_limit.py:4`, `backend/app/ingest/router.py:13`
- **Problem:** Slowapi limiter jest singletonem i dekoruje endpointy (`60/minute` na ingest), ale żaden test nie weryfikuje, że rate limiting działa (zwraca 429 po przekroczeniu limitu).
- **Dlaczego to problem:** Rate limiting to zabezpieczenie przed abuse. Jeśli limiter się zepsuje (np. przez zmianę konfiguracji), nie ma testu który to wykryje. CLAUDE.md explicitly warns about singleton limiter.
- **Sugestia (bez implementacji):** Dodać test który wysyła >60 requestów w krótkim czasie i sprawdza 429. Użyć `freezegun` lub manipulować limiterem w teście.

### [🟠] Brak testów admin panelu
- **Lokalizacja:** `backend/app/admin.py`, `backend/app/*/admin.py` (5 plików admin)
- **Problem:** sqladmin views (ItemAdmin, PricePointAdmin, RecipeAdmin, RecipeIngredientAdmin, UserAdmin) + authentication_backend nie mają żadnych testów.
- **Dlaczego to problem:** Admin panel to interfejs do zarządzania danymi produkcyjnymi. Brak testów auth backendu oznacza że np. niesprawdzony dostęp do admina nie zostanie wykryty.
- **Sugestia (bez implementacji):** Dodać testy integracyjne dla `/admin` endpoints — przynajmniej auth guard (niezalogowany → redirect do loginu) i dostępność CRUD dla każdego modelu.

### [🟠] Duplikacja fixture'ów `db_session` i `auth_client` — brak współdzielenia z conftest
- **Lokalizacja:** `backend/tests/test_prices.py:14-22`, `backend/tests/test_inventory.py:20-30`, `backend/tests/test_items.py:13-21`, `backend/tests/test_user_items.py:18-26`, `backend/tests/test_crafting.py:15-23`, `backend/tests/test_ingest.py:19-27`
- **Problem:** `db_session` fixture jest copy-paste'owany w 6 plikach testowych. `auth_client` jest duplikowany w 4 plikach (test_prices, test_inventory, test_profiles, test_user_items). Identyczna implementacja za każdym razem.
- **Dlaczego to problem:** Maintenance burden — zmiana sposobu tworzenia sesji wymaga edycji 6 plików. Ryzyko niezamierzonych rozbieżności między kopiami.
- **Sugestia (bez implementacji):** Przenieść `db_session` i `auth_client` do `conftest.py`. Wystarczy jeden wspólny fixture.

### [🟡] Session-scoped `setup_database` — shared state between tests
- **Lokalizacja:** `backend/tests/conftest.py:33-43`
- **Problem:** `setup_database` jest `scope="session"` — tabele tworzone raz na cały proces testowy. Dane z jednego testu widoczne w kolejnych. UUID-suffixy w nazwach itemów łagodzą problem UniqueConstraint, ale nie chronią przed np. `test_get_items_returns_list` które sprawdza `total >= 1` — widzi też dane z poprzednich testów.
- **Dlaczego to problem:** Testy nie są w pełni izolowane. `test_get_items_filter_by_grade` tworzy 2 itemy, ale `total` w odpowiedzi może zawierać też itemy z innych testów. Asercje na liczbę rekordów mogą być flaky przy zmianie kolejności testów.
- **Sugestia (bez implementacji):** Rozważyć `scope="function"` z rollback po każdym teście (savepoint pattern) lub truncate tabele w fixture. Alternatywnie: zaakceptować obecną strategię ale doprecyzować asercje (np. sprawdzać czy nasz item jest w wynikach, nie ile jest total).

### [🟡] Słabe asercje w `test_follow_concurrent_is_idempotent`
- **Lokalizacja:** `backend/tests/test_user_items.py:100-127`
- **Problem:** Test sprawdza tylko `r1 is not None` i `r2 is not None` — łapie Exception ale nie weryfikuje co faktycznie się stało. Nie sprawdza czy w DB jest dokładnie 1 rekord (co jest istotą idempotencji). Dodatkowo `except Exception: return None` maskujeпотенjalne błędy.
- **Dlaczego to problem:** Test przejdzie nawet jeśli concurrent follow stworzy 2 rekordy (double insert) — bo oba zwrócą `True`/`False`, nie `None`. Nie wykryje broken idempotencji.
- **Sugestia (bez implementacji):** Dodać asercję na count rekordów w DB po gather (analogicznie do `test_get_or_create_profile_concurrent`). Usunąć broad `except Exception`.

### [🟡] Brak testów walidacji inputu w auth
- **Lokalizacja:** `backend/tests/test_auth.py`
- **Problem:** Testy auth sprawdzają happy path (rejestracja, login, logout) i duplicate email, ale brakuje testów dla: pustego hasła, zbyt krótkiego hasła, nieprawidłowego formatu email, pustego emaila.
- **Dlaczego to problem:** Jeśli walidacja hasła/email się zmieni lub zniknie, nie ma testu który to wykryje. FastAPI validation (422) nie jest testowane dla auth endpoints.
- **Sugestia (bez implementacji):** Dodać testy dla edge-case'ów walidacji: `{"email": "", "password": "x"}`, `{"email": "not-an-email", "password": "123"}`, `{"email": "a@b.com", "password": ""}`.

### [🟡] Brak testów dla CORS i exception handlerów
- **Lokalizacja:** `backend/app/main.py:32-38`, `backend/app/config/exceptions.py:17-20`
- **Problem:** CORS middleware i custom `AppError` handler nie mają dedykowanych testów. `register_exception_handlers` rejestruje handler który zwraja JSON z detail — nie ma testu weryfikującego format odpowiedzi błędu.
- **Dlaczego to problem:** Zmiana formatu błędu (np. z `{"detail": "..."}` na `{"error": "..."}`) złamie frontend. CORS misconfiguration zablokuje requests z przeglądarki.
- **Sugestia (bez implementacji):** Dodać test sprawdzający strukturę odpowiedzi AppError (status_code + detail field). CORS test opcjonalny — łatwiej zweryfikować ręcznie.

### [🟡] Fragile string-matching w testach consistency
- **Lokalizacja:** `backend/tests/test_consistency.py:14-30`
- **Problem:** `test_seed_does_not_use_market_source` i `test_frontend_chart_uses_ah_source` szukają dokładnych stringów w plikach źródłowych. Zmiana formatowania (np. `'ah'` → `"ah"` lub przeniesienie do stałej) złamie test bez realnej regresji.
- **Dlaczego to problem:** Testy które failują przy refaktoringu (bez zmiany logiki) są fałszywie alarmujące i obniżają zaufanie do testów.
- **Sugestia (bez implementacji):** Zamiast string matching, rozważyć test importujący stałą/enum z kodu źródłowego i sprawdzający wartość. Lub zaakceptować fragility i dodać komentarz wyjaśniający intencję.

### [🟢] MagicMock bez spec w discord bot tests
- **Lokalizacja:** `discord_bot/tests/test_prices.py:236-241`
- **Problem:** `make_interaction()` tworzy `MagicMock()` bez `spec=discord.Interaction`. Dodawanie nowych atrybutów w handlerze (np. `interaction.user`) nie zostanie wykryte jako błąd — MagicMock zwróci kolejny MagicMock zamiast AttributeError.
- **Dlaczego to problem:** Testy mogą przechodzić mimo że kod używa nieistniejących atrybutów mocka. Niskie ryzyko w praktyce, ale obniża wartość testów.
- **Sugestia (bez implementacji):** Dodać `spec=discord.Interaction` lub przynajmniej `spec=MagicMock` z listą oczekiwanych atrybutów.

### [🟢] Brak testów negatywnych dla `test_calculate_with_inventory`
- **Lokalizacja:** `backend/tests/test_crafting.py:108-117`
- **Problem:** Test sprawdza `crafts_possible == 4` dla `inventory: {ingot.id: 22}` z `qty=5`. Brak testu dla `inventory: {ingot.id: 3}` (za mało na 1 craft — oczekiwane `crafts_possible == 0`).
- **Dlaczego to problem:** Edge case "za mało materiałów na ani jeden craft" nie jest pokryty.
- **Sugestia (bez implementacji):** Dodać test z inventory < required quantity.

### [💡] Brak testów dla `test_get_items_returns_list` — brak asercji na strukturę itemu
- **Lokalizacja:** `backend/tests/test_items.py:38-44`
- **Problem:** Test sprawdza `total >= 1` i `"items" in data`, ale nie weryfikuje struktury poszczególnych itemów (np. obecność `id`, `name`, `category`, `grade`).
- **Dlaczego to problem:** Zmiana schematu odpowiedzi (usunięcie pola) nie zostanie wykryta. Inne testy (filter_by_category) pośrednio weryfikują pola, ale ten test mógłby być bardziej kompletny.
- **Sugestia (bez implementacji):** Dodać asercje na klucze w pierwszym itemie: `assert {"id", "name", "category", "grade", "current_price"} <= data["items"][0].keys()`.

### [💡] Brak testów dla Discord bota poza `cogs/prices.py`
- **Lokalizacja:** `discord_bot/bot.py`, `discord_bot/cogs/` (tylko `prices.py`)
- **Problem:** Bot ma tylko 1 cog (prices). Jeśli dodane zostaną kolejne cogs, nie ma wzorca testowego dla nich. `bot.py` (setup, event handlers) nie jest testowane.
- **Dlaczego to problem:** Niskie ryzyko obecnie (1 cog), ale jeśli projekt się rozrośnie, brak wzorca może prowadzić do pomijania testów.
- **Sugestia (bez implementacji):** Zaakceptować obecny stan (1 cog = 1 test file) ale rozważyć test dla `bot.py` startup sequence.


================================================================================
# SOURCE: audit/visionary/findings.md
================================================================================

# Visionary — findings

## Podsumowanie

ArcheRage Market Tracker to solidny projekt z czystą architekturą monolityczną, ale istnieje kilka strategicznych kierunków rozwoju, które mogą znacząco zwiększyć wartość produktu. Kluczowe obszary to: przejście na event-driven architecture dla real-time updates, wprowadzenie cache'owania i optymalizacji zapytań dla skalowania, rozszerzenie analityki o predykcje cenowe, oraz rozważenie mikroserwisów dla niezależnego skalowania komponentów. Projekt ma też potencjał do stania się platformą społecznościową dla graczy z funkcjami społecznościowymi.

## Findings

### [💡] Event-Driven Architecture dla Real-Time Updates
- **Lokalizacja:** `backend/app/ingest/services.py`, `backend/app/prices/services.py`
- **Problem:** Aktualna architektura jest request-response — frontend musi pollować lub odświeżać stronę, żeby zobaczyć nowe ceny. Brak mechanizmu push updates.
- **Dlaczego to problem:** Użytkownicy nie widzą aktualnych cen w czasie rzeczywistym. Polling generuje niepotrzebny ruch i obciążenie serwera. Konkurencyjne trackery oferują live updates.
- **Sugestia (bez implementacji):** Wdrożyć WebSocket lub Server-Sent Events (SSE) dla real-time price updates. Po dodaniu nowego punktu cenowego przez ingest, opublikować event do channelu (np. Redis Pub/Sub lub NATS). Frontend subskrybuje WebSocket i aktualizuje wykres natychmiast. Alternatywnie: SvelteKit z `load` functions + `invalidate()` po SSE event.
- **Powiązane:** [🟠] Brak cache'owania warstwy

### [💡] CQRS dla Optymalizacji Zapytań
- **Lokalizacja:** `backend/app/prices/services.py:11-92`, `backend/app/crafting/services.py:39-55`
- **Problem:** Zapytania o historię cen i kalkulacje craftingu czytają z tej samej bazy co zapisy. Złożone agregacje (bucketing) i rekurencyjne kalkulacje obciążają DB.
- **Dlaczego to problem:** Przy wzroście danych (tysiące punktów cenowych dziennie) zapytania analityczne będą spowalniać operacje write. Brak separacji read/write models.
- **Sugestia (bez implementacji):** Rozważyć CQRS (Command Query Responsibility Segregation) — osobny model write (normalizowany) i read (denormalizowany, zoptymalizowany pod zapytania). Materialized views dla agregacji cenowych. Oddzielna baza read-replica dla zapytań analitycznych. Alternatywnie: Redis cache dla frequently accessed data.
- **Powiązane:** [💡] Event-Driven Architecture dla Real-Time Updates

### [💡] Predykcja Cenowa z Machine Learning
- **Lokalizacja:** `backend/app/prices/`, `frontend/src/lib/components/charts/`
- **Problem:** System pokazuje tylko historyczne ceny. Brak jakiejkolwiek predykcji trendów, anomalii cenowych, czy rekomendacji kupna/sprzedaży.
- **Dlaczego to problem:** Użytkownicy muszą sami analizować trendy. Brak alertów o nietypowych ruchach cenowych. Utrata wartości z zebranych danych historycznych.
- **Sugestia (bez implementacji):** Wdrożyć prosty model predykcyjny (np. Prophet, ARIMA, lub LSTM) trenowany na historycznych danych. Endpoint `/api/predictions/{item_id}` zwracający prognozę na 24h/7d/30d. Alerty cenowe (webhook/email gdy cena przekroczy próg). Wykres z przedziałem ufności. Backend jako osobny serwis ML (FastAPI + scikit-learn/TensorFlow).
- **Powiązane:** [💡] Event-Driven Architecture dla Real-Time Updates

### [🟠] Brak Cache'owania Warstwy
- **Lokalizacja:** `backend/app/items/services.py`, `backend/app/prices/services.py`
- **Problem:** Każde zapytanie trafia bezpośrednio do bazy. Brak cache'owania dla frequently accessed data (lista items, ostatnie ceny, kalkulacje craftingu).
- **Dlaczego to problem:** Niepotrzebne obciążenie bazy. Wolniejsze odpowiedzi dla popularnych endpointów. Przy wzroście ruchu — bottleneck.
- **Sugestia (bez implementacji):** Wdrożyć Redis jako cache layer. Cache'ować: listę items (TTL 5min), historię cen (TTL 1min), kalkulacje craftingu (TTL 30s). Użyć `@cache` decorator z `fastapi-cache2`. Invalidation po ingest. Alternatywnie: CDN cache dla static data.

### [💡] Mikroserwasy dla Niezależnego Skalowania
- **Lokalizacja:** `backend/app/`, `infra/compose/`
- **Problem:** Monolityczna architektura ogranicza skalowanie — cały backend musi być skaloawany jako jednostka. Ingest (high-throughput) i crafting calculations (CPU-intensive) mają różne wymagania.
- **Dlaczego to problem:** Nie można niezależnie skalować komponentów o różnych profilach obciążenia. Deploy jednego modułu wymaga deployu całego monolitu.
- **Sugestia (bez implementacji):** Wydzielić 3 serwisy: 1) Ingest Service (high-throughput, stateless), 2) Analytics Service (CPU-intensive calculations), 3) API Gateway (routing, auth). Komunikacja przez message queue (RabbitMQ/NATS). Każdy serwis z własną bazą (database per service). Kubernetes dla orchestration. Alternatywnie: modular monolith z clear boundaries i feature flags.

### [💡] GraphQL zamiast REST dla Elastycznych Zapytań
- **Lokalizacja:** `backend/app/*/router.py`, `frontend/src/lib/api.d.ts`
- **Problem:** REST endpoints mają fixed response structures. Frontend musi robić multiple requests żeby zebrać dane z różnych modułów (items + prices + crafting).
- **Dlaczego to problem:** Over-fetching (pobieranie niepotrzebnych pól) lub under-fetching (brak potrzebnych danych w jednym requescie). Nieelastyczne dla różnych klientów (web, mobile, bot).
- **Sugestia (bez implementacji):** Rozważyć GraphQL (Strawberry dla Pythona) zamiast REST. Single endpoint, klient określa jakie dane potrzebuje. Schema stitching dla modułów. DataLoader N+1 problem. Alternatywnie: REST z field selection (`?fields=name,price`) lub JSON:API specification.

### [💡] Progressive Web App (PWA) dla Mobile Experience
- **Lokalizacja:** `frontend/src/app.html`, `frontend/src/routes/+layout.svelte`
- **Problem:** Brak natywnego doświadczenia mobile. Użytkownicy mobilni muszą otwierać przeglądarkę, wpisywać URL. Brak offline access do ostatnio przeglądanych cen.
- **Dlaczego to problem:** Utrata użytkowników mobilnych. Brak push notifications dla alertów cenowych. Brak dostępu offline.
- **Sugestia (bez implementacji):** Przekształcić frontend w PWA — Service Worker dla offline caching, manifest.json dla installability, Push API dla notyfikacji. SvelteKit ma adapter do PWA. Cache ostatnich 100 items offline. Background sync dla ingest gdy brak połączenia.

### [💡] Social Features i Community Tools
- **Lokalizacja:** `backend/app/users/`, `backend/app/profiles/`, `frontend/src/routes/`
- **Problem:** System jest indywidualny — brak społecznościowego aspektu. Użytkownicy nie mogą dzielić się analizami, strategiami craftingu, czy alertami.
- **Dlaczego to problem:** Niska retencja użytkowników. Brak network effects. Utrata potencjału community-driven content.
- **Sugestia (bez implementacji):** Dodać: 1) Public profiles z stats (items tracked, craft profit made), 2) Shared watchlists (public/private), 3) Comments/discussion na item pages, 4) Guild system (wspólne inventory tracking), 5) Leaderboard (top crafters, best traders). Alternatywnie: integracja z Discord guild channels.

### [💡] Multi-Game Support i Plugin Architecture
- **Lokalizacja:** `backend/app/items/models.py`, `backend/app/prices/models.py`
- **Problem:** System jest hardcodeowany dla ArcheRage. Dodanie wsparcia dla innej gry wymagałoby kopania kodu.
- **Dlaczego to problem:** Ograniczona skala rynku. Brak możliwości monetyzacji dla innych społeczności MMO.
- **Sugestia (bez implementacji):** Wdrożyć plugin architecture — `game` field w Item/PricePoint, game-specific adapters dla ingest, configurable category/grade enums. Multi-tenant architecture z game_id jako tenant. API versioning per game. Marketplace dla addon-ów.

### [💡] Real-Time Market Analytics Dashboard
- **Lokalizacja:** `frontend/src/routes/items/`, `frontend/src/lib/components/charts/`
- **Problem:** Aktualny dashboard pokazuje tylko basic price history. Brak zaawansowanej analityki — volume, spread, volatility, correlation między itemami.
- **Dlaczego to problem:** Użytkownicy nie mogą podejmować świadomych decyzji handlowych. Brak insights z danych.
- **Sugestia (bez implementacji):** Zbudować analytics dashboard z: 1) Heatmapa korelacji cen między itemami, 2) Volume profile (jeśli dodamy quantity data), 3) Volatility index per item, 4) Market summary (top movers, most traded), 5) Portfolio tracker (łączna wartość inventory). Użyć Apache ECharts extensions lub D3.js dla wizualizacji.

### [💡] Automated Trading Bot Integration
- **Lokalizacja:** `backend/app/ingest/`, `discord_bot/cogs/`
- **Problem:** Aktualnie ceny są dodawane ręcznie (Discord bot) lub przez addon. Brak automatyzacji handlu.
- **Dlaczego to problem:** Użytkownicy muszą ręcznie monitorować okazje. Brak automatycznego buy/sell na podstawie progów cenowych.
- **Sugestia (bez implementacji):** Stworzyć trading bot service: 1) Alerty cenowe (webhook/email/Discord), 2) Auto-buy gdy cena spadnie poniżej progu, 3) Auto-sell gdy cena wzrośnie, 4) Portfolio rebalancing, 5) Integration z game API (jeśli istnieje). Wymagałoby to autoryzacji w grze — potencjalnie ryzykowne.

### [💡] Data Pipeline dla Historical Analysis
- **Lokalizacja:** `backend/app/prices/models.py`, `backend/app/prices/services.py`
- **Problem:** Dane cenowe są przechowywane w OLTP database. Brak separation dla analityki historycznej. Agregacje w runtime są kosztowne.
- **Dlaczego to problem:** Przy milionach punktów cenowych zapytania analityczne będą spowalniać. Brak możliwości batch processing dla ML.
- **Sugestia (bez implementacji):** Wdrożyć data pipeline: 1) ETL z PostgreSQL do data warehouse (ClickHouse/TimescaleDB), 2) Apache Airflow/Prefect dla orchestration, 3) dbt dla transformations, 4) Materialized views dla frequently accessed aggregations. Alternatywnie: TimescaleDB extension dla PostgreSQL (hypertables dla time-series).

### [💡] Multi-Tenant SaaS Architecture
- **Lokalizacja:** `backend/app/config/settings.py`, `backend/app/auth/`
- **Problem:** System jest single-tenant. Każda instancja jest niezależna. Brak centralnego zarządzania wieloma serwerami/gildiami.
- **Dlaczego to problem:** Ograniczona skalowalność biznesowa. Brak możliwości oferowania jako usługi dla wielu społeczności.
- **Sugestia (bez implementacji):** Przekształcić w multi-tenant SaaS: 1) `tenant_id` w każdej tabeli, 2) Row-level security w PostgreSQL, 3) Subdomain routing (`gildia.archerage-tracker.com`), 4) Per-tenant configuration (categories, grades, currencies), 5) Billing system (Stripe integration). Alternatywnie: database-per-tenant dla isolation.

### [💡] GraphQL Federation dla Distributed Architecture
- **Lokalizacja:** `backend/app/main.py`, `infra/compose/`
- **Problem:** Monolityczny GraphQL schema przy wzroście modułów stanie się nieporęczny. Brak niezależnego deployu.
- **Dlaczego to problem:** Schema staje się bottleneck. Zmiany w jednym module wymagają deployu całego API.
- **Sugestia (bez implementacji):** Rozważyć Apollo Federation lub GraphQL Mesh: 1) Każdy moduł jako subgraph, 2) Gateway composition, 3) Niezależne schema evolution, 4) Cross-module references przez federation directives. Wymagałoby to jednak GraphQL migration first.

### [💡] Edge Computing dla Low-Latency
- **Lokalizacja:** `infra/caddy/`, `backend/app/`
- **Problem:** Centralny serwer generuje latency dla użytkowników z dalekich regionów. Brak edge presence.
- **Dlaczego to problem:** Użytkownicy z Azji/Ameryki Południowej mają wysokie opóźnienia. Poor experience dla globalnej bazy graczy.
- **Sugestia (bez implementacji):** Wdrożyć edge computing: 1) Cloudflare Workers/CDN dla static assets, 2) Edge functions dla auth/rate limiting, 3) Regional read replicas, 4) GeoDNS routing. Alternatywnie: multi-region deployment z Kubernetes.


================================================================================
# SOURCE: audit/second-opinion/findings.md
================================================================================

# Second Opinion — findings

## Podsumowanie (3–5 zdań)

Przeczytałem 10 raportów audytorskich (skeptic był pusty). Projekt jest solidny — architektura czysta, testy backendu sensowne, kontrakt API spójny. Najważniejsze potwierdzone problemy to: **addon hardkodujący grade:1** (dane zanieczyszczone u źródła), **brak rate limitingu na auth** (realne ryzyko brute-force), **kontenery jako root** (łatwy fix, duży impact bezpieczeństwa), oraz **kompletny brak testów frontendu**. Kilka findingów jest przesadzonych: SQL injection przez ILIKE to nie jest SQL injection w klasycznym sensie (parametr jest bezpiecznie interpolowany przez SQLAlchemy, to jedynie wildcard abuse), visionary proponuje mikroserwisy/CQRS/ML dla projektu który ma ~1000 itemów w grze MMO, a "race condition" w ItemTable ma już działający guard. Brakuje kilku ważnych kontekstów: `SecureAdminAuth` tworzy `Middleware` ale sqladmin ich nie używa — to nie tylko martwy kod, to fałszywe poczucie bezpieczeństwa, rate limiter za proxy jest faktycznie bezwartościowy (wszyscy sharingują limit), a `add_price_point` commituje wewnętrznie co łamie atomiczność batch ingestu.

## Potwierdzone findings (najważniejsze)

- **[🔴] Addon zapisuje wszystkie ceny z `grade:1` (Grand)** — from: integration — to jest NAJWAŻNIEJSZY finding w całym audycie. Dane wejściowe są zanieczyszczone u źródła — żadna ilość poprawek backendu/frontendu tego nie naprawi. `pricetracker.lua:307` hardkoduje `"grade":1` dla każdego itemu. Backend tworzy nowe Item z nieprawidłowym grade zamiast aktualizować istniejące.

- **[🔴] Kontenery backend i discord_bot działają jako root** — from: infra, discordbot — potwierdzam. Oba Dockerfile (`backend/Dockerfile:1`, `discord_bot/Dockerfile:1`) nie mają `USER` directive. Łatwy fix, duży impact: RCE w kontenerze = root access.

- **[🟠] Brak rate limitingu na endpointach auth** — from: security — potwierdzam. `/api/auth/login` i `/api/auth/register` nie mają żadnego limitera. FastAPI-users router jest wstrzykiwany z `fastapi_users.get_auth_router()` — dekoratory slowapi trzeba dodać na poziomie routera lub jako dependency.

- **[🟠] Brak obsługi błędów sieciowych w login/register** — from: frontend — potwierdzam. `auth.svelte.ts:56` i `74` robią `fetch()` bez `try-catch`. Jeśli backend jest niedostępny, użytkownik zobaczy nieobsłużony exception w konsoli.

- **[🟠] Brak testów frontendowych** — from: tester-evaluator, frontend, code-quality — potwierdzam. Zero plików testowych, zero konfiguracji test runnera. To realne ryzyko regresji w logice craftingu i formatowaniu cen.

- **[🟠] Czwórna duplikacja `utcnow()`** — from: backend, code-quality — potwierdzam. Identyczna funkcja w 4 modelach. Łatwy refactor do `app/config/utils.py`.

- **[🟠] Duplikacja fixture'ów testowych** — from: code-quality, tester-evaluator — potwierdzam. `db_session` i `auth_client` skopiowane w 6 plikach zamiast współdzielone w `conftest.py`.

- **[🟠] Brak obsługi 401 na większości endpointów** — from: frontend — potwierdzam. Tylko `inventory/+page.svelte` sprawdza 401. Reszta stron wyświetla błąd lub puste dane po wygaśnięciu sesji.

- **[🟠] Frontend Dockerfile kopiuje pełne node_modules** — from: infra, frontend — potwierdzam. `npm install` (nie `npm ci`) + brak `prune --production`. Obraz produkcyjny zawiera vite, eslint, svelte-check.

- **[🟠] Nowy httpx.AsyncClient per request w bocie** — from: discordbot — potwierdzam. `cogs/prices.py:52` i `98` tworzą nowego klienta w każdym `async with`. Brak connection pooling, nowy TLS handshake per request.

## Podważone findings (przesadzone)

- **[🟠] SQL injection przez nieescaped znaki specjalne w ILIKE** — from: backend — **PRZESADZONY**. Backend poprawnie nazywa to "ILIKE wildcard abuse", ale security auditor używa terminu "SQL injection" co jest mylące. SQLAlchemy parametryzuje zapytanie — `%` i `_` nie są SQL injection, to jedynie pattern matching wildcards. Użytkownik może dopasować więcej rekordów niż zamierzono, ale NIE może wykonać dowolnego SQL. To jest max 🟡 (low), nie 🟠. Sugestia escapowania jest słuszna, ale severity jest zawyżone.

- **[🟠] Potencjalna rekursja nieskończona w drzewie craftingu** — from: frontend — **PRZESADZONY**. Backend definiuje przepisy jako DAG (Recipe → RecipeIngredient → Item → Recipe). Cykliczne przepisy wymagałyby błędu w danych seed lub ręcznego dodania przez admina. Backend nie waliduje cykli, ale dane wejściowe (seed.py) są acykliczne. To jest raczej 💡 (idea) niż 🟠 — ryzyko jest teoretyczne dopóki nie ma cyklicznych przepisów w grze.

- **[💡] Event-Driven Architecture, CQRS, ML Predictions, Microservices, GraphQL, PWA, Social Features, Multi-Game, Multi-Tenant SaaS** — from: visionary — **ZNACZNIE PRZESADZONE**. Projekt trackuje ceny w grze MMO z ~1000 itemów. Proponowanie CQRS, Kafka/NATS, Kubernetes, ML (Prophet/LSTM), GraphQL Federation, edge computing, multi-tenant SaaS z billingiem Stripe to over-engineering na poziomie kosmicznym. Projekt używa monolitu z FastAPI + SvelteKit — to jest właściwa architektura dla tego skalu. Mikroserwisy byłyby uzasadnione przy >100k requestów/dzień, nie przy obecnym ruchu. Propozycje visionary powinny być traktowane jako "ciekawe pomysły na przyszłość" a nie findings audytowe.

- **[🟡] Race condition w infinite scroll ItemTable** — from: frontend — **LEKKO PRZESADZONY**. `ItemTable.svelte:206-213` ma `$effect` z guard `if (loading) return` wewnątrz `loadItems()`. W Svelte 5 runes, `$effect` jest synchroniczny w stosunku do state changes. Okno między sprawdzeniem warunku a ustawieniem `loading = true` jest minimalne (microtask boundary). Podwójne fetchowanie jest teoretycznie możliwe ale mało prawdopodobne w praktyce. 🟡 jest OK, ale "race condition" to za mocne określenie — to bardziej "potential duplicate fetch".

- **[🟡] Brak CSRF protection** — from: security, frontend — **PRZESADZONY**. FastAPI + JWT cookie + CORS z `allow_credentials=True` i explicit origins jest zasadniczo bezpieczne przeciwko CSRF. Nowoczesne przeglądarki domyślnie ustawiają `SameSite=Lax` na cookie, co blokuje cross-origin POST z form submission. FastAPI-users CookieTransport ustawia `samesite="lax"` domyślnie. To nie jest zero-risk, ale ryzyko jest niskie i dobrze mitigowane.

## Dodany kontekst (inni mogli nie widzieć)

### 🔴 `SecureAdminAuth` tworzy middleware, ale sqladmin ich nie używa
- **Lokalizacja:** `backend/app/admin_auth.py:51-68`
- **Problem:** `SecureAdminAuth.__init__()` tworzy `self.middlewares` z `SessionMiddleware(https_only=secure)`, ale sqladmin `AuthenticationBackend` nie ma mechanizmu do wstrzykiwania middleware'ów. `Admin.__init__()` z sqladmin przyjmuje `authentication_backend` ale nie korzysta z jego `middlewares` atrybutu. `SessionMiddleware` musi być dodany do FastAPI app, nie do auth backend.
- **Dlaczego to problem:** To nie jest tylko martwy kod — to fałszywe poczucie bezpieczeństwa. Ktoś mógłby pomyśleć że `secure=True` w `SecureAdminAuth` aktywuje secure cookie, ale w rzeczywistości `SessionMiddleware` z `https_only=True` nigdy nie jest dodany do pipeline'u requestów. Cookie admina jest ustawiane przez `SessionMiddleware` dodany gdzie indziej (lub wcale).
- **Sugestia:** Usuń `SecureAdminAuth`. Dodaj `SessionMiddleware` bezpośrednio do FastAPI app w `main.py` z `https_only=settings.cookie_secure`.

### 🟠 Rate limiter za proxy jest bezwartościowy
- **Lokalizacja:** `backend/app/config/rate_limit.py:4`
- **Problem:** `get_remote_address` czyta `request.client.host`. Za reverse proxy (Caddy), to zawsze jest IP proxy (np. `172.18.0.1`), nie rzeczywisty klient. Wszyscy użytkownicy sharingują ten sam limit 60/min na ingest.
- **Dlaczego to problem:** Security auditor zauważył to (finding 🟡), ale severity powinno być 🟠. Rate limiter jest jedyną ochroną przed abuse na ingest — jeśli nie działa poprawnie za proxy, ochrona jest iluzoryczna. W produkcji z Caddy, atakujący z jednego IP może wysyłać 60 req/min, ale tak samo może każdy inny użytkownik — limit jest per-serwer, nie per-klient.
- **Sugestia:** Skonfiguruj slowapi z custom `key_func` czytającym `X-Forwarded-For` z zaufanym proxy. Np.: `key_func=lambda request: request.headers.get("X-Forwarded-For", request.client.host).split(",")[0].strip()`.

### 🟠 `add_price_point` commituje wewnętrznie — łamie atomiczność batch ingestu
- **Lokalizacja:** `backend/app/prices/services.py:123`, `backend/app/ingest/services.py:96-100`
- **Problem:** `add_price_point()` robi `await session.commit()` wewnątrz (linia 123). W `bulk_ingest`, każda iteracja pętli (linia 118-127) wywołuje `_process_row` → `add_price_point` → commit. Jeśli wiersz 3 z 100 się nie powiedzie, wiersze 1-2 są już skommitowane.
- **Dlaczego to problem:** Backend auditor zauważył to, ale nie podkreślił konsekwencji. `match_or_create_item` też commituje wewnętrznie (linia 46). Oznacza to, że batch ingest NIE jest atomiczny — partial commits są możliwe. To jest akceptowalne dla ingestu (izolacja błędów per-wiersz), ale powinno być explicit udokumentowane.
- **Sugestia:** Dodaj docstring do `bulk_ingest` wyjaśniający że partial commit jest zamierzony. Lub jeśli atomiczność jest wymagana, refactor na zewnętrzny commit.

### 🟡 `INTERVAL_SECONDS[interval]` rzuci `KeyError` dla nieznanego interwału
- **Lokalizacja:** `backend/app/prices/services.py:55`
- **Problem:** `seconds = INTERVAL_SECONDS[interval]` — jeśli `interval` nie jest w dict (`5m`, `1h`, `1d`), Python rzuci `KeyError`. FastAPI nie złapie tego jako 422 — zwróci 500 z tracebackiem.
- **Dlaczego to problem:** Router (`prices/router.py`) ma `Interval` enum, ale serwis przyjmuje `str`. Jeśli ktoś wywoła serwis bezpośrednio (np. z innego modułu lub testu) z nieprawidłowym interwałem, dostanie nieoczekiwany 500.
- **Sugestia:** Dodaj walidację w serwisie: `if interval not in INTERVAL_SECONDS: raise ValueError(...)` lub zmień typ parametru na `Interval` enum.

### 🟡 Seed nie ustawia `last_price_at` — ale to niskie ryzyko
- **Lokalizacja:** `backend/seed.py:265-269`
- **Problem:** Backend auditor zauważył że seed nie ustawia `last_price_at`. Potwierdzam — po seedowaniu `last_price_at` jest `None`. Ale logika w `prices/services.py:117` (`if item.last_price_at is None or captured_at >= item.last_price_at`) poprawnie obsługuje `None` — aktualizuje `current_price` przy pierwszym price point po seedzie.
- **Dlaczego to problem:** Niskie ryzyko — jedyny problem to brak spójności (seed ustawia `current_price` ale nie `last_price_at`). Po pierwszym realnym price poincie, oba pola będą poprawne.
- **Sugestia:** Fix jest trywialny (dodać `db_item.last_price_at = ts` w seed) ale nie jest pilny.

### 🟡 `cookie_secure=False` jako domyślne — ale to jest OK dla dev
- **Lokalizacja:** `backend/app/config/settings.py:16`
- **Problem:** Security auditor zauważył `cookie_secure=False`. To jest poprawne zachowanie dla dev — `docker-compose.dev.yml` nie ustawia `COOKIE_SECURE`, więc domyślne `False` jest właściwe. Produkcja (`docker-compose.prod.yml`) ustawia `COOKIE_SECURE: "true"`.
- **Dlaczego to problem:** Jedyny problem to brak dokumentacji — ktoś mógłby uruchomić produkcję bez compose i zapomnieć o `COOKIE_SECURE`. Ale to nie jest bug w kodzie — to kwestia dokumentacji.
- **Sugestia:** Dodaj komentarz w settings.py: `# Must be True in production (set COOKIE_SECURE=true in .env)`.

## Konflikty między subagentami

### 1. SQL injection vs ILIKE wildcard abuse
- **Backend auditor:** 🟠 "SQL injection przez nieescaped znaki specjalne w ILIKE"
- **Security auditor:** Nie wspomina o SQL injection
- **Kto ma rację:** Backend auditor przesadza z terminem. SQLAlchemy parametryzuje zapytanie — to NIE jest SQL injection. To jest ILIKE wildcard abuse (użytkownik może dopasować `%` wszystkie rekordy). Severity powinno być 🟡, nie 🟠. Security auditor słusznie to pomija.

### 2. CSRF protection
- **Frontend auditor:** 🟡 "Brak CSRF protection"
- **Security auditor:** 🟡 "Brak CSRF protection — JWT w cookie bez explicit CSRF token"
- **Kto ma rację:** Obaj mają rację częściowo, ale obaj przesadzają. FastAPI-users CookieTransport domyślnie ustawia `samesite="lax"` na cookie. Nowoczesne przeglądarki blokują cross-origin POST z form submission przy `SameSite=Lax`. CORS z explicit origins dodaje dodatkową warstwę. Ryzyko jest niskie, nie średnie.

### 3. Severity braku testów frontendowych
- **Tester evaluator:** 🔴 "Frontend完全没有测试 — zero test coverage"
- **Frontend auditor:** 🟢 "Brak testów frontendowych"
- **Code quality auditor:** 💡 "Brak testów frontendowych"
- **Kto ma rację:** Tester evaluator ma rację z severity. Brak JAKICHKOLWIEK testów frontendowych w projekcie z logiką craftingu, formatowaniem cen i auth flow to realne ryzyko. 🟢 jest zbyt niskie. Powinno być 🟠 (wysokie) — nie 🔴 (krytyczne, bo backend ma testy), ale zdecydowanie nie 🟢.

### 4. Severity root w kontenerach
- **Infra auditor:** 🔴 "Kontenery backend i discord_bot działają jako root"
- **Discord bot auditor:** 🟠 "Kontener Docker działa jako root"
- **Kto ma rację:** Infra auditor ma rację — to powinno być 🔴. Root w kontenerze z publicznie dostępnym API to realne ryzyko. Discord bot auditor daje 🟠, ale bota nie jest publicznie dostępny (tylko przez Discord API), więc 🟠 jest OK dla bota. Dla backendu 🔴 jest właściwe.

### 5. Priorytetyzacja: addon grade:1 vs reszta
- **Integration auditor:** 🔴 "Addon zapisuje wszystkie ceny z grade:1"
- **Backend auditor:** Nie wspomina (to poza scope backendu)
- **Kto ma rację:** Integration auditor trafił w sedno. To jest NAJWAŻNIEJSZY finding — dane są zanieczyszczone u źródła. Żadna optymalizacja backendu, cache, czy indeks nie pomoże jeśli dane są błędne. Reszta audytorów powinna to podkreślić jako priorytet.

## Co dodatkowego warto wskazać

### 🟡 Brak walidacji cykliczności w drzewie craftingu (backend)
Backend nie sprawdza czy przepisy tworzą cykle. `load_all_recipes()` ładuje wszystko i buduje drzewo rekurencyjnie. Gdyby admin dodał cykliczny przepis (A→B→A), `calculate()` i `list_summaries()` wpadłyby w nieskończoną rekurencję. Frontend auditor zauważył to po stronie frontendu, ale backend powinien mieć walidację przy dodawaniu przepisów.

### 🟡 `match_or_create_item` commituje wewnętrznie — drugi commit w batch ingestu
`ingest/services.py:46` robi `await session.commit()` po `on_conflict_do_nothing`. To jest osobny commit od `add_price_point` (linia 123 w prices/services.py). W jednym `_process_row` są DWA commity — jeden w `match_or_create_item`, drugi w `add_price_point`. Jeśli drugi się nie powiedzie, pierwszy jest już skommitowany (item stworzony, ale bez price point).

### 🟢 Brak `engines` w `frontend/package.json`
Dependencies auditor zauważył brak `engines` w package.json. Dodam że brakuje też `.nvmrc` lub `.node-version` — developer z inną wersją Node nie dostanie ostrzeżenia.

### 🟢 Pozytyw: spójny kontrakt API
Integration auditor potwierdził że bot, addon i frontend używają tego samego kontraktu (`/api/ingest/prices`). CORS jest poprawnie skonfigurowany. Cookie/JWT flow jest spójny. To jest dobrze zaprojektowane.

### 🟢 Pozytyw: dobre testy backendu
Backend ma solidne pokrycie integracyjne z prawdziwą PostgreSQL (nie SQLite in-memory). UUID-suffix w nazwach itemów zapobiega kolizjom. Testy crafting, ingest, prices, inventory są sensowne. Brakuje testów rate limiting i admin panelu, ale core domain jest dobrze przetestowana.

### 💡 Priorytet napraw (od najważniejszego)

| # | Finding | Severity | Koszt fixa | Impact |
|---|---------|----------|------------|--------|
| 1 | Addon grade:1 | 🔴 | Średni (Lua + seed) | Dane zanieczyszczone |
| 2 | Root w kontenerach | 🔴 | Niski (3 linie Dockerfile) | Bezpieczeństwo |
| 3 | Rate limiter za proxy | 🟠 | Niski (custom key_func) | Ochrona przed abuse |
| 4 | Brak rate limitingu na auth | 🟠 | Średni (dekoratory) | Brute-force |
| 5 | Brak testów frontendu | 🟠 | Średni (vitest setup) | Regresje |
| 6 | try-catch w login/register | 🟠 | Niski (try-catch) | UX |
| 7 | fetchApi() wrapper | 🟠 | Niski (helper) | 401 redirect, DRY |
| 8 | Frontend Dockerfile (npm ci + prune) | 🟠 | Niski | Rozmiar obrazu |
| 9 | SecureAdminAuth martwy kod | 🟡 | Niski (usuń klasę) | Fałszywe bezpieczeństwo |
| 10 | Caddy security headers | 🟡 | Niski | Hardening |


================================================================================
# SOURCE: audit/synthesis.md
================================================================================

# Audit Synthesis — ArcheRage Market Tracker

**Data:** 2026-05-20 | **Model:** opencode | **Subagentów:** 12 (11 + second opinion)

---

## TL;DR — Top 10 (posortowane po severity)

| # | Severity | Finding | Source |
|---|----------|---------|--------|
| 1 | 🔴 | **Addon hardkoduje `grade:1`** — wszystkie ceny w DB mają nieprawidłowy grade | integration |
| 2 | 🔴 | **Kontenery backend/bot działają jako root** — RCE = root access | infra, discordbot |
| 3 | 🔴 | **DB port (5432) wystawiony na 0.0.0.0 z domyślnymi hasłami** | infra |
| 4 | 🟠 | **Brak rate limitingu na `/api/auth/*`** — brute-force login | security |
| 5 | 🟠 | **Rate limiter za proxy jest bezwartościowy** — `get_remote_address` czyta IP proxy | security, second-opinion |
| 6 | 🟠 | **Brak try-catch w login/register/logout** — crash przy braku sieci | frontend |
| 7 | 🟠 | **Frontend: zero testów** — brak vitest, brak unit/integration/e2e | tester-evaluator |
| 8 | 🟠 | **Frontend Dockerfile kopiuje pełne node_modules** — vite, eslint w produkcji | infra, frontend |
| 9 | 🟠 | **Brak security headers w Caddy** — clickjacking, MIME-sniffing, brak HSTS | infra, security |
| 10 | 🟠 | **Czwórna duplikacja `utcnow()`** + potrójna `computeNodeCost` | code-quality |

---

## Krytyczne — natychmiastowa akcja (🔴)

### 1. Addon hardkoduje `grade:1`
- **Lokalizacja:** `addon/pricetracker_folio/pricetracker.lua:307`
- **Problem:** `SavePrices()` zapisuje `"grade":1` dla każdego przedmiotu. Backend tworzy nowe Item z nieprawidłowym grade zamiast aktualizować istniejące.
- **Impact:** Dane wejściowe są zanieczyszczone u źródła — żadna optymalizacja backendu tego nie naprawi.
- **Fix:** Dodaj pole `grade` do WATCHLIST w Lua lub mapę `name → grade`.

### 2. Kontenery jako root
- **Lokalizacja:** `backend/Dockerfile`, `discord_bot/Dockerfile`
- **Problem:** Brak `USER` directive. RCE w kontenerze = root access.
- **Fix:** `RUN useradd -r -s /usr/sbin/nologin appuser && USER appuser` (3 linie).

### 3. DB port wystawiony publicznie
- **Lokalizacja:** `infra/compose/docker-compose.dev.yml:12-13`
- **Problem:** `0.0.0.0:5432:5432` z hasłem `postgres/postgres`.
- **Fix:** Zmień na `127.0.0.1:5432:5432`.

---

## Wzorce powtarzające się (≥2 subagentów)

| Wzorzec | Subagenci | Priorytet |
|---------|-----------|-----------|
| Brak testów frontendu | tester-evaluator, frontend, code-quality, second-opinion | 🟠 |
| Root w kontenerach | infra, discordbot, second-opinion | 🔴 |
| Rate limiter nie działa za proxy | security, second-opinion | 🟠 |
| Brak rate limitingu na auth | security, second-opinion | 🟠 |
| Duplikacja kodu (`utcnow`, `computeNodeCost`, fixtures) | backend, code-quality, second-opinion | 🟠 |
| Frontend Dockerfile z devDeps | infra, frontend, second-opinion | 🟠 |
| Brak security headers | infra, security | 🟠 |
| Brak 401 handling w frontendzie | frontend, second-opinion | 🟠 |
| `@ts-nocheck` w wykresie | frontend | 🟠 |

---

## Konflikty opinii

### 1. SQL injection vs ILIKE wildcard abuse
- **Backend auditor:** 🟠 "SQL injection"
- **Second opinion:** 🟡 "To NIE jest SQL injection — SQLAlchemy parametryzuje zapytanie. To wildcard abuse."
- **Rozstrzygnięcie:** Second opinion ma rację. Severity powinno być 🟡.

### 2. CSRF protection
- **Frontend/Security:** 🟡 "Brak CSRF"
- **Second opinion:** "Przesadzone — `SameSite=Lax` + CORS z explicit origins mitiguje ryzyko"
- **Rozstrzygnięcie:** Second opinion ma rację. Ryzyko niskie, nie średnie.

### 3. Brak testów frontendu
- **Tester evaluator:** 🔴
- **Frontend/Code quality:** 🟢/💡
- **Second opinion:** 🟠
- **Rozstrzygnięcie:** 🟠 jest właściwe — nie 🔴 (backend ma testy), ale zdecydowanie nie 🟢.

### 4. Visionary — CQRS/Microservices/ML
- **Visionary:** 13 propozycji (CQRS, Kafka, ML, GraphQL, PWA, SaaS...)
- **Second opinion:** "Znacznie przesadzone dla projektu z ~1000 itemów w grze MMO"
- **Rozstrzygnięcie:** Second opinion ma rację. Monolit FastAPI+SvelteKit to właściwa architektura. Propozycje visionary to "ciekawe pomysły na przyszłość", nie findings audytowe.

---

## Top 3 Quick Wins (low effort, high impact)

| # | Finding | Koszt | Impact |
|---|---------|-------|--------|
| 1 | `USER appuser` w Dockerfile backend/bot | 3 linie | 🔴→🟢 bezpieczeństwo |
| 2 | `127.0.0.1` zamiast `0.0.0.0` dla DB port | 1 znak | 🔴→🟢 sieć |
| 3 | try-catch w login/register/logout | ~20 linii | 🟠→🟢 UX |

---

## Long-term Roadmap

### Bezpieczeństwo (priorytet 1)
1. Rate limiter: custom `key_func` z `X-Forwarded-For` + rate limit na `/api/auth/*`
2. Security headers w Caddy (CSP, HSTS, X-Frame-Options)
3. Zablokuj `/docs`, `/redoc`, `/openapi.json` w produkcji
4. Walidacja `display_name` max_length w Pydantic schema

### Dane (priorytet 2)
5. Fix addon — poprawne grade z gry
6. Walidacja `source` field (enum/whitelist)
7. Composite index `(item_id, source, captured_at)` na PricePoint

### Frontend (priorytet 3)
8. `fetchApi()` wrapper (401 redirect, credentials, error handling)
9. Vitest — testy dla auth store, currency, computeNodeCost
10. Usuń `@ts-nocheck` z EChartsLineChart
11. Wyodrębnij `computeNodeCost` do shared lib
12. AbortController w onMount

### Backend (priorytet 4)
13. Wyodrębnij `utcnow()` do `app/config/datetime_utils.py`
14. Rate limit na crafting endpoints
15. Cache dla `load_all_recipes`/`load_all_items`
16. Usuń martwy `SecureAdminAuth` — dodaj SessionMiddleware do main.py
17. Dodaj `session.rollback()` po nieudanym `match_or_create_item`

### Infra (priorytet 5)
18. Frontend Dockerfile: `npm ci` + `npm prune --omit=dev`
19. Healthchecki dla backend/frontend w prod compose
20. CI: concurrency groups, discord bot docker build
21. `engines` w frontend `package.json` + `.nvmrc`

---

## Pozytywy (co jest dobrze)

- ✅ Czysta modularna architektura backendu (models/schemas/services/router per domain)
- ✅ Solidne testy integracyjne na prawdziwej PostgreSQL (nie mocki)
- ✅ Spójny kontrakt API — bot, addon i frontend używają tego samego endpointu
- ✅ UUID-suffix w testach zapobiega kolizjom
- ✅ `.env` nie jest trackowany w git
- ✅ Pydantic validation po obu stronach
- ✅ Svelte auto-escaping (brak XSS)
- ✅ `SameSite=Lax` na JWT cookie
- ✅ OpenAPI-typescript generuje typy automatycznie
- ✅ Partial success response dla ingest (nie fail-fast)

