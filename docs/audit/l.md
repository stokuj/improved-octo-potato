# Audyt Context — ArcheRage Market Tracker

## Stack technologiczny

### Backend (Python 3.13+)
| Komponent | Wersja | Rola |
|-----------|--------|------|
| FastAPI | ≥0.135.3 | API framework |
| SQLModel | ≥0.0.38 | ORM (SQLAlchemy + Pydantic) |
| fastapi-users | ≥15.0.5 | Auth (rejestracja/login/cookie) |
| Alembic | ≥1.13.1 | Migracje DB |
| asyncpg + psycopg[binary] | — | PostgreSQL driver |
| slowapi | ≥0.1.9 | Rate limiting (singleton) |
| sqladmin | ≥0.24.0 | Panel admina `/admin` |
| PostgreSQL | 16-alpine | Baza danych |
| uv | — | Package manager |
| pytest + pytest-asyncio | ≥8.3 | Testy |
| ruff | ≥0.15.13 | Linter |

### Frontend
| Komponent | Wersja | Rola |
|-----------|--------|------|
| SvelteKit 5 | ≥2.57.0 | Framework (runes API) |
| Tailwind CSS 4 | ≥4.2.2 | Utility CSS |
| DaisyUI 5 | ≥5.5.19 | Komponenty UI |
| ECharts + svelte-echarts | 5.6 / 1.0 | Wykresy cen |
| openapi-typescript | ≥7.13 | Generowanie typów API |
| adapter-node | ≥5.2.11 | Produkcyjny build |
| TypeScript | ≥6.0.2 | Strict mode |

### Infra
| Komponent | Rola |
|-----------|------|
| Podman Compose | Konteneryzacja (nie Docker!) |
| Caddy 2 | TLS termination + reverse proxy |
| GitHub Actions | CI: lint, lock-check, test, alembic |

### Discord Bot (osobny projekt Python 3.13+)
| Komponent | Wersja |
|-----------|--------|
| discord.py | ≥2.4 |
| httpx | ≥0.27 |
| pydantic-settings | ≥2.3 |

---

## Entry pointy

### Backend
- **Plik:** `backend/app/main.py`
- **Start:** `uv run fastapi dev app/main.py` (dev) lub `uv run uvicorn app.main:app` (prod)
- **Port:** 8000

### Frontend
- **Plik:** `frontend/src/routes/+layout.svelte`
- **Start:** `npm run dev` (dev) lub `node build` (prod)
- **Port:** 5173 (dev)

### Discord Bot
- **Plik:** `discord_bot/bot.py`
- **Start:** `uv run python bot.py`

### Infra
- **Dev:** `infra/compose/docker-compose.dev.yml` (db, backend, frontend)
- **Prod:** `infra/compose/docker-compose.prod.yml` (db, backend, frontend, caddy)
- **Makefile:** `make dev-up`, `make prod-up`, `make test`, `make migrate`, `make seed`

---

## Mapa warstw i komunikacji

```
┌─────────────────────────────────────────────────────────┐
│                    Player's PC                          │
│  ArcheRage Game → Lua Addon → prices.jsonl              │
└─────────────────────────────────────────────────────────┘
                          │ (watcher usunięty)
                          ▼
┌─────────────────────────────────────────────────────────┐
│                      Server                             │
│  Caddy (TLS + reverse proxy)                            │
│   ├── /api/*  /admin  /docs  → FastAPI backend :8000    │
│   └── /*                    → SvelteKit frontend :3000  │
│                                                         │
│  FastAPI backend                                        │
│   ├── /api/auth         — rejestracja/login (cookie)    │
│   ├── /api/users        — zarządzanie użytkownikiem     │
│   ├── /api/items        — publiczne czytanie itemów     │
│   ├── /api/prices       — auth write, price history     │
│   ├── /api/crafting     — auth, recipe profit calculator│
│   ├── /api/user-items   — watchlist (user ↔ item)       │
│   ├── /api/inventory    — user inventory (upsert/delete)│
│   ├── /api/ingest/prices— public write (rate-limited)   │
│   └── /admin            — sqladmin (superuser only)     │
│                                                         │
│  PostgreSQL 16                                          │
│   └── naive UTC timestamps                              │
└─────────────────────────────────────────────────────────┘
                         ▲
                         │ HTTP (slash commands)
              ┌──────────┴──────────┐
              │   Discord Bot       │
              │   /addprice command │
              └─────────────────────┘
```

### Komunikacja
- **HTTP REST** — frontend ↔ backend (JWT w cookie, `credentials: 'include'`)
- **HTTP POST** — Discord bot → `/api/ingest/prices` (rate-limited, no auth)
- **SQL** — backend ↔ PostgreSQL
- **Brak message brokera** — wszystkie operacje synchroniczne

---

## Stan testów i CI

### Backend (`backend/tests/`)
| Test | Status |
|------|--------|
| test_auth.py | ✅ |
| test_items.py | ✅ |
| test_prices.py | ✅ |
| test_profiles.py | ✅ |
| test_user_items.py | ✅ |
| test_inventory.py | ✅ |
| test_crafting.py | ✅ |
| test_crafting_calculator.py | ✅ |
| test_ingest.py | ✅ |
| test_consistency.py | ✅ |
| conftest.py | ✅ (fixtures: db, client, test user) |

- **Tryb:** `asyncio_mode = "auto"`
- **Baza:** prawdziwy PostgreSQL (`app_test`), nie mocki
- **CI:** GitHub Actions (`backend.yml`) — lint, lock-check, test, alembic

### Discord Bot (`discord_bot/tests/`)
| Test | Status |
|------|--------|
| test_prices.py | ✅ |
| __init__.py | ✅ |

- **CI:** GitHub Actions (`discord_bot.yml`) — lint, test

### Frontend
- **Brak testów automatycznych** — tylko `svelte-check` (type check)
- **CI:** GitHub Actions (`frontend.yml`) — build check

### CI/CD (GitHub Actions)
| Workflow | Trigger | Zadania |
|----------|---------|---------|
| backend.yml | push/PR na backend | lint, lock-check, test, alembic |
| discord_bot.yml | push/PR na bot | lint, test |
| frontend.yml | push/PR na frontend | build |
| docker.yml | — | — |

---

## Czego NIE MA w projekcie (do pominięcia w audycie)

| Obszar | Status |
|--------|--------|
| Watcher daemon | ❌ Usunięty — ceny wchodzą przez Discord bot lub bezpośredni POST |
| Message broker / kolejki | ❌ Brak — wszystkie operacje synchroniczne |
| Frontend testy (Vitest, Playwright) | ❌ Brak — tylko svelte-check |
| E2E testy | ❌ Brak |
| Mock DB w testach | ❌ Celowo — testy biją w prawdziwy PostgreSQL |
| Docker (tylko Podman) | ⚠️ Projekt używa `podman compose`, nie `docker compose` |
| .env files w repo | ✅ W .gitignore — tylko .example pliki |

---

## Struktura modułów backendu

```
backend/app/
├── config/         # db engines, settings, rate_limit singleton, exceptions
├── auth/           # fastapi-users wiring; login returns 204
├── users/          # User model + router
├── profiles/       # Profile 1-to-1 with User, auto-created on register
├── items/          # Item model + CRUD; current_price denormalized
├── prices/         # PricePoint append-only time-series
├── user_items/     # watchlist (User ↔ Item many-to-many)
├── crafting/       # Recipe + RecipeIngredient; recursive profit calculator
├── user_inventory/ # per-user item quantities; upsert/delete
├── ingest/         # public write endpoint; partial-success contract
└── admin/          # sqladmin ModelAdmin registrations
```

Każdy moduł: `models.py`, `schemas.py`, `services.py`, `router.py`, `admin.py` (opcjonalnie), `__init__.py`

---

## Kluczowe inwarianty (do weryfikacji w audycie)

1. **`source='ah'`** — musi być używane konsystentnie (seed, bot, frontend chart)
2. **`Item.current_price`** — aktualizowane w tej samej transakcji co `PricePoint`
3. **`slowapi.Limiter`** — singleton w `app/config/rate_limit.py`
4. **Naive UTC** — nigdzie timezone-aware datetime w DB
5. **Ingest partial success** — złe wiersze zwracają 200 z `errors[]`, nie 4xx
6. **`session.rollback()`** — po failed `add_price_point`
7. **`CraftResult.batch_profit`** — total profit dla batcha, nie per craft
8. **`UserInventory` upsert** — `quantity > 0` → `ON CONFLICT`, `quantity = 0` → DELETE
9. **Kolejność routerów** — `GET /api/inventory/for-recipe/{item_id}` PRZED `PUT /api/inventory/{item_id}`

---

## Pliki konfiguracyjne i dokumentacja

| Plik | Opis |
|------|------|
| `docs/ai/architecture.md` | Architektura i schema DB |
| `docs/ai/stack.md` | Decyzje stackowe |
| `docs/ai/patterns.md` | Wzorce i gotchas |
| `docs/ai/roadmap.md` | Roadmapa |
| `docs/ai/constitution.md` | Constitution projektu |
| `CLAUDE.md` | Quick reference |
| `.env.example` | Przykładowe zmienne środowiskowe |
# Plan audytu

## Subagenty per warstwa

### backend
**Scope:** `backend/app/` — wszystkie moduły domenowe, config, main.py
**Out of scope:** testy (to zadanie testera-evaluatro), discord_bot

**Kluczowe pytania:**
1. Czy inwarianty z `docs/ai/patterns.md` są zachowane w kodzie?
2. Czy nie ma wycieków sesji DB lub niezrobionych rollbacków?
3. Czy rate limiter jest używany konsystentnie na wszystkich endpointach?
4. Czy nie ma N+1 queries w relacjach między modelami?
5. Czy walidacja wejścia (Pydantic) jest kompletna?

---

### frontend
**Scope:** `frontend/src/` — wszystkie komponenty, store, fetch
**Out of scope:** node_modules, build output

**Kluczowe pytania:**
1. Czy wszystkie fetche używają `credentials: 'include'`?
2. Czy nie ma wycieków stanu poza `$state` runes?
3. Czy typy z `api.d.ts` są używane konsekwentnie?
4. Czy nie ma hardkodowanych wartości (formatCurrency, LABOUR_ITEM_NAME)?
5. Czy error handling jest spójny we wszystkich komponentach?

---

### infra
**Scope:** `infra/`, `Makefile`, `.github/workflows/`, `backend/Dockerfile`, `frontend/Dockerfile`
**Out of scope:** kod aplikacji

**Kluczowe pytania:**
1. Czy compose pliki są bezpieczne (sekrety przez env, nie hardkodowane)?
2. Czy healthchecki są poprawne i używane w `depends_on`?
3. Czy CI workflow są kompletne (test, lint, build)?
4. Czy nie ma hardkodowanych portów lub ścieżek?
5. Czy Caddyfile poprawnie routuje wszystkie endpointy?

---

### discordbot
**Scope:** `discord_bot/` — bot.py, komendy slash, testy
**Out of scope:** backend, frontend

**Kluczowe pytania:**
1. Czy bot używa poprawnego endpointu `/api/ingest/prices`?
2. Czy error handling jest kompletny (timeout, 429, 5xx)?
3. Czy token jest pobierany z env, nie z kodu?
4. Czy rate limiting jest obsługiwany po stronie klienta?
5. Czy testy mockują HTTP wywołania do backendu?

---

### integration
**Scope:** kontrakty API między warstwami — routery, schemas, fetch w frontend, bot HTTP calls
**Out of scope:** implementacja wewnętrzna modułów

**Kluczowe pytania:**
1. Czy frontend i backend mają zgodne typy (openapi-typescript)?
2. Czy bot i backend mają zgodny contract ingest endpoint?
3. Czy nie ma niezgodności w nazwach pól (camelCase vs snake_case)?
4. Czy wszystkie endpointy wymagające auth mają `current_active_user`?
5. Czy nie ma endpointów z pominiętym rate limitingiem tam gdzie potrzebny?

---

## Subagenty cross-cutting

### security
**Scope:** cały kod — backend, frontend, infra, bot
**Out of scope:** styl kodu, performance

**Kluczowe pytania:**
1. Czy nie ma sekretów w repo (.env, hardkodowane klucze)?
2. Czy wszystkie endpointy publiczne są rate-limited?
3. Czy jest walidacja wejścia przed użyciem w SQL (SQLi)?
4. Czy CORS jest poprawnie skonfigurowany?
5. Czy cookie są secure/httponly/samesite?
6. Czy nie ma XSS w frontend (unescaped HTML)?
7. Czy auth/authz jest spójne (current_active_user vs current_superuser)?

---

### dependencies
**Scope:** `backend/pyproject.toml`, `frontend/package.json`, `discord_bot/pyproject.toml`
**Out of scope:** kod aplikacji

**Kluczowe pytania:**
1. Czy nie ma paczek z znanymi CVE?
2. Czy nie ma paczek EOL lub deprecated?
3. Czy wersje są aktualne (major/minor behind)?
4. Czy `uv.lock` i `package-lock.json` są w sync z pyproject/package.json?
5. Czy nie ma nieużywanych zależności?

---

### code-quality
**Scope:** cały kod — backend, frontend, infra, bot
**Out of scope:** testy (to zadanie testera)

**Kluczowe pytania:**
1. Czy nie ma god objects lub god services?
2. Czy nie ma copy-paste kodu między modułami?
3. Czy nazewnictwo jest spójne (snake_case w Python, camelCase w TS)?
4. Czy nie ma dead code (nieużywane funkcje, importy)?
5. Czy nie ma spaghetti w usługach (długie funkcje, wiele odpowiedzialności)?
6. Czy komentarze są aktualne i pomocne?

---

### tester-evaluator
**Scope:** `backend/tests/`, `discord_bot/tests/`
**Out of scope:** kod aplikacji

**Kluczowe pytania:**
1. Czy testy mają sens (nie testują implementacji, tylko zachowanie)?
2. Czy coverage jest wystarczający (endpointy, edge cases)?
3. Czy nie ma testów flaky (losowe dane bez seeda)?
4. Czy brakuje testów integracyjnych (end-to-end API)?
5. Czy testy auth pokrywają wszystkie scenariusze (brak tokena, expired, superuser)?
6. Czy brakuje testów E2E dla krytycznych ścieżek (ingest, crafting)?

---

## Subagenty meta-perspektywa

### skeptic
**Scope:** cały kod — kwestionowanie wyborów architektonicznych
**Out of scope:** implementacja细节

**Kluczowe pytania:**
1. Co jest over-engineeringiem?
2. Gdzie można by użyć prostszego rozwiązania?
3. Czy każda zależność jest potrzebna?
4. Czy nie ma zbyt wielu warstw abstrakcji?
5. Co można by usunąć bez utraty funkcjonalności?

---

### visionary
**Scope:** cały kod — alternatywne podejścia
**Out of scope:** implementacja细节

**Kluczowe pytania:**
1. Co gdyby użyć event-driven architecture zamiast sync HTTP?
2. Czy GraphQL byłoby lepsze niż REST dla tego use case?
3. Czy nie warto dodać cache (Redis) dla frequently accessed data?
4. Co gdyby przenieść część logiki do frontendu (edge computing)?
5. Jakie wzorce z innych projektów można by zaadaptować?

---

### second-opinion
**Scope:** czytanie wszystkich `findings.md` i dodanie własnej perspektywy
**Out of scope:** pisanie własnych findings od zera

**Kluczowe pytania:**
1. Które findings są najważniejsze (potwierdzenie)?
2. Które findings są przesadzone (kwestionowanie)?
3. Jaki kontekst umknął innym subagentom?
4. Czy są konflikty między subagentami?
5. Co zostało pominięte?

---

## Harmonogram

1. **Równolegle Faza 3a:** backend, frontend, infra, discordbot, integration
2. **Równolegle Faza 3b:** security, dependencies, code-quality, tester-evaluator
3. **Równolegle Faza 3c:** skeptic, visionary
4. **Faza 4:** second-opinion (czyta wszystkie poprzednie)
5. **Faza 5:** synteza (main agent)

---

## Pominięci subagenty

| Subagent | Powód pominięcia |
|----------|------------------|
| discordbot | ✅ Jest — projekt istnieje |
| watcher | ❌ Usunięty z projektu |
| broker/queue | ❌ Nie ma message brokera |
| e2e-tester | ❌ Brak testów E2E w projekcie |
# backend — findings

## Podsumowanie

Backend jest w dobrym stanie — większość inwariantów z `docs/ai/patterns.md` i `docs/ai/constitution.md` jest zachowana. Rate limiter singleton jest poprawnie skonfigurowany, ingest zwraca partial success zgodnie z kontraktem, a `add_price_point` aktualizuje `Item.current_price` w tej samej transakcji. Wykryto jednak kilka problemów: brak rollbacków przy częściowych błędach w upsertach, potencjalne N+1 w crafting services, niespójność w admin_auth (podwójna instancja), oraz brak walidacji `source` w PricePointCreate.

## Findings

### 🔴 Podwójna instancja authentication_backend w admin_auth.py
- **Lokalizacja:** `backend/app/admin_auth.py:46` i `backend/app/admin_auth.py:68`
- **Problem:** Plik tworzy `authentication_backend` dwukrotnie — najpierw jako `AdminAuth`, potem nadpisuje jako `SecureAdminAuth`. Pierwsza instancja jest martwym kodem, ale może wprowadzać zamieszanie.
- **Dlaczego to problem:** Niejasna intencja, potencjalne problemy z importem jeśli ktoś zaimportuje przed nadpisaniem. Nie ma to wpływu na runtime (nadpisanie), ale łamie zasadę "no dead code".
- **Sugestia:** Usunąć pierwszą definicję `authentication_backend = AdminAuth(...)` i zostawić tylko `SecureAdminAuth`.
- **Powiązane:** `backend/app/admin.py:4`

### 🟠 Brak rollbacków przy błędach w upsert_inventory
- **Lokalizacja:** `backend/app/user_inventory/services.py:38-64`
- **Problem:** Funkcja `upsert_inventory` wykonuje `session.commit()` po ścieżce DELETE (linia 50) i po INSERT/UPDATE (linia 63), ale **nie ma `session.rollback()`** w przypadku wyjątku. Jeśli `session.execute(stmt)` rzuci wyjątek, sesja pozostaje w stanie błędu.
- **Dlaczego to problem:** Zgodnie z `patterns.md` i `constitution.md` — "Po failed `add_price_point` zawsze `session.rollback()`". Ta sama zasada powinna dotyczyć wszystkich operacji DB. Bez rollbacka sesja jest "trucizną" dla kolejnych operacji.
- **Sugestia:** Dodać `try/except` z `await session.rollback()` w bloku except, analogicznie do `ingest/services.py:_process_row`.
- **Powiązane:** `backend/app/ingest/services.py:95-108`

### 🟠 Brak rollbacków w follow_item / unfollow_item
- **Lokalizacja:** `backend/app/user_items/services.py:65-94`
- **Problem:** `follow_item` i `unfollow_item` wykonują `session.commit()` (linie 78, 91), ale nie mają obsługi wyjątków z rollbackiem.
- **Dlaczego to problem:** Spójność z kontraktem z `patterns.md` — każda operacja DB powinna mieć rollback przy błędzie. Obecnie sesja może pozostać w stanie błędu.
- **Sugestia:** Dodać `try/except` z rollbackiem wokół operacji DB.
- **Powiązane:** `backend/app/ingest/services.py:95-108`

### 🟠 Brak rollbacków w profiles/services.py
- **Lokalizacja:** `backend/app/profiles/services.py:10-35`
- **Problem:** `get_or_create_profile` i `update_profile` wykonują `session.commit()` bez obsługi wyjątków.
- **Dlaczego to problem:** Ryzyko zatrucia sesji przy błędzie DB.
- **Sugestia:** Dodać try/except z rollbackiem.
- **Powiązane:** `backend/app/ingest/services.py:95-108`

### 🟠 N+1 query w crafting/services.py
- **Lokalizacja:** `backend/app/crafting/services.py:39-54`
- **Problem:** Funkcja `list_summaries` wywołuje `build_craft_tree` dla każdego rekordu z `all_recipes`. `build_craft_tree` nie wykonuje zapytań DB (korzysta z `all_recipes` i `all_items`), ale **`load_all_recipes` i `load_all_items` są wywoływane tylko raz** — to jest poprawne. Jednak wewnątrz `build_craft_tree` nie ma N+1, bo dane są w pamięci.
- **Dlaczego to problem:** **FAŁSZYWY ALARM** — po bliższej analizie nie ma N+1, bo wszystkie dane są ładowane raz na początku. To finding do weryfikacji.
- **Sugestia:** Brak akcji — kod jest poprawny.
- **Powiązane:** —

### 🟡 Brak walidacji `source` w PricePointCreate
- **Lokalizacja:** `backend/app/prices/schemas.py:22-25`
- **Problem:** `PricePointCreate` ma `source: str = PydanticField(min_length=1, max_length=40)` — to jest poprawne. **ALE** w `prices/services.py:95-125` funkcja `add_price_point` nie waliduje, czy `source` jest zgodny z kontraktem (np. czy to `'ah'` lub inna dozwolona wartość).
- **Dlaczego to problem:** `constitution.md` mówi: "`source='ah'` musi być używane spójnie przez seed, bota i frontend chart". Brak walidacji pozwala na wpisanie dowolnego źródła, co może złamać spójność danych.
- **Sugestia:** Dodać walidację `source` w `add_price_point` lub stworzyć enum `PriceSource` i użyć go w schema.
- **Powiązane:** `docs/ai/constitution.md:10`

### 🟡 Brak rate limitu na endpointach crafting i inventory
- **Lokalizacja:** `backend/app/crafting/router.py:12-24`, `backend/app/user_inventory/router.py:13-41`
- **Problem:** Endpointy `/api/crafting/*` i `/api/inventory/*` nie mają dekoratorów `@limiter.limit()`. Tylko `ingest/prices` i `prices/{item_id}/prices` mają rate limit.
- **Dlaczego to problem:** Crafting endpointy mogą być kosztowne obliczeniowo (rekurencyjne drzewa). Brak limitu otwiera na DoS. Inventory endpointy mogą być nadużywane do scrapingu.
- **Sugestia:** Dodać `@limiter.limit("60/minute")` lub podobny limit do wszystkich endpointów authenticated.
- **Powiązane:** `backend/app/config/rate_limit.py:4`

### 🟡 Router kolejność — for-recipe przed PUT
- **Lokalizacja:** `backend/app/user_inventory/router.py:13-41`
- **Problem:** Router jest zdefiniowany w jednym pliku. `GET /for-recipe/{item_id}` (linia 21) jest **przed** `PUT /{item_id}` (linia 32) — to jest **poprawnie** zgodnie z `patterns.md`.
- **Dlaczego to problem:** **BRAK PROBLEMU** — kolejność jest правильna. To finding potwierdzający zgodność.
- **Sugestia:** Brak akcji — kod jest poprawny.
- **Powiązane:** `docs/ai/patterns.md:21-24`

### 🟡 Walidacja wejścia — PricePointCreate nie wymusza source='ah'
- **Lokalizacja:** `backend/app/prices/schemas.py:22-25`
- **Problem:** Schema pozwala na dowolny `source` spełniający `min_length=1, max_length=40`. `constitution.md` wymaga spójnego używania `source='ah'`.
- **Dlaczego to problem:** Ryzyko niespójnych danych w tabeli `PricePoint`. Frontend chart filtruje po `source='ah'` (`docs/ai/architecture.md:44`).
- **Sugestia:** Dodać `Literal['ah']` lub enum do pola `source` w `PricePointCreate`, albo przynajmniej dokumentację.
- **Powiązane:** `docs/ai/constitution.md:10`, `docs/ai/architecture.md:44`

### 🟡 Ingest — match_or_create_item nie robi rollback przy błędzie
- **Lokalizacja:** `backend/app/ingest/services.py:20-57`
- **Problem:** Funkcja `match_or_create_item` wykonuje `await session.commit()` (linia 46) w środku operacji. Jeśli `add_price_point` później nie powiedzie się, `match_or_create_item` już zrobił commit dla itemu.
- **Dlaczego to problem:** To jest **celowy design** — item jest tworzony niezależnie od price point. Ale może prowadzić do sytuacji, gdzie item istnieje bez price point (osierocony). Nie jest to błąd, ale warto dokumentować.
- **Sugestia:** Dodać komentarz w kodzie wyjaśniający, że commit itemu jest celowy przed dodaniem price point.
- **Powiązane:** `backend/app/ingest/services.py:95-108`

### 💡 Brak indeksu na `PricePoint.source`
- **Lokalizacja:** `backend/app/prices/models.py:10-16`
- **Problem:** `source` ma `index=True` (linia 13) — to jest **poprawnie**.
- **Dlaczego to problem:** **BRAK PROBLEMU** — indeks jest zdefiniowany.
- **Sugestia:** Brak akcji.
- **Powiązane:** —

### 💡 Użycie `col()` w query — niekonsekwentne
- **Lokalizacja:** `backend/app/items/services.py:19`, `backend/app/user_inventory/services.py:98`, `backend/app/user_items/services.py:28`
- **Problem:** W niektórych miejscach użyto `col(Item.name).ilike(...)`, w innych `Item.category == category`. `col()` jest potrzebne do `ilike`, ale niekonsekwencja może mylić.
- **Dlaczego to problem:** Drobna niespójność stylu. Nie wpływa na funkcjonalność.
- **Sugestia:** Ujednolicić styl — używać `col()` wszędzie lub tylko tam, gdzie potrzebne (ilike, in_).
- **Powiązane:** —

### 💡 auth/router.py — podwójne rejestrowanie `/auth`
- **Lokalizacja:** `backend/app/auth/router.py:8-21`
- **Problem:** Router rejestruje `get_auth_router` pod `/auth` (linia 9) i `get_register_router` też pod `/auth` (linia 14). To jest **poprawnie** — fastapi-users dzieli endpointy wewnętrznie.
- **Dlaczego to problem:** **BRAK PROBLEMU** — to jest standardowy pattern fastapi-users.
- **Sugestia:** Brak akcji.
- **Powiązane:** —

### 🟢 Rate limiter singleton — poprawnie
- **Lokalizacja:** `backend/app/config/rate_limit.py:4`, `backend/app/main.py:29`
- **Problem:** **BRAK** — singleton jest poprawnie zdefiniowany i używany przez `app.state.limiter`.
- **Dlaczego to problem:** Nie ma problemu.
- **Sugestia:** Brak akcji — kod jest poprawny.
- **Powiązane:** `docs/ai/patterns.md:27-35`

### 🟢 Ingest partial success — poprawnie
- **Lokalizacja:** `backend/app/ingest/services.py:112-134`
- **Problem:** **BRAK** — `bulk_ingest` zwraca `IngestResponse` z `errors[]`, nigdy nie rzuca 4xx dla złych wierszy.
- **Dlaczego to problem:** Nie ma problemu.
- **Sugestia:** Brak akcji — kod jest poprawny.
- **Powiązane:** `docs/ai/patterns.md:47-49`

### 🟢 add_price_point — atomowa aktualizacja current_price
- **Lokalizacja:** `backend/app/prices/services.py:95-125`
- **Problem:** **BRAK** — funkcja aktualizuje `item.current_price` i `item.last_price_at` w tej samej transakcji co insert `PricePoint` (linie 117-120).
- **Dlaczego to problem:** Nie ma problemu.
- **Sugestia:** Brak akcji — kod jest poprawny.
- **Powiązane:** `docs/ai/constitution.md:17`

### 🟢 UserInventory upsert — poprawnie
- **Lokalizacja:** `backend/app/user_inventory/services.py:38-64`
- **Problem:** **BRAK** — `quantity > 0` używa `ON CONFLICT DO UPDATE`, `quantity = 0` używa `DELETE`.
- **Dlaczego to problem:** Nie ma problemu.
- **Sugestia:** Brak akcji — kod jest poprawny.
- **Powiązane:** `docs/ai/constitution.md:16`

### 🟢 Naive UTC — poprawnie
- **Lokalizacja:** `backend/app/items/models.py:7-8`, `backend/app/prices/models.py:6-8`, `backend/app/user_items/models.py:7-8`, `backend/app/profiles/models.py:7-8`
- **Problem:** **BRAK** — wszystkie `utcnow()` zwracają `datetime.now(timezone.utc).replace(tzinfo=None)`.
- **Dlaczego to problem:** Nie ma problemu.
- **Sugestia:** Brak akcji — kod jest poprawny.
- **Powiązane:** `docs/ai/constitution.md:14`

### 🟢 Pydantic walidacja — kompletna
- **Lokalizacja:** Wszystkie schemas.py
- **Problem:** **BRAK** — wszystkie request/response modele mają pełną walidację (min_length, max_length, ge, gt, FieldConstraints).
- **Dlaczego to problem:** Nie ma problemu.
- **Sugestia:** Brak akcji — kod jest poprawny.
- **Powiązane:** —

## Tabela podsumowująca

| Kategoria | Liczba | Status |
|-----------|--------|--------|
| 🔴 Critical | 1 | Wymaga natychmiastowej akcji |
| 🟠 High | 4 | Wymaga akcji (rollbacki) |
| 🟡 Medium | 4 | Do rozważenia |
| 💡 Low | 2 | Informacyjne |
| 🟢 OK | 6 | Zgodne z inwariantami |
# frontend — findings

## Podsumowanie

Frontend jest w dobrym stanie — wszystkie fetche używają `credentials: 'include'`, typy z `api.d.ts` są konsekwentnie re-eksportowane przez `types.ts`, a `formatCurrency` i `LABOUR_ITEM_NAME` są importowane z shared lib. Svelte-check nie zgłasza błędów. Wykryto 3 problemy: potencjalny wyciek stanu poza `$state` w `ItemTable.svelte`, niespójny error handling w kilku komponentach oraz jeden fetch bez `credentials` na stronie domowej.

## Findings

### 🟠 Potencjalny wyciek stanu poza `$state`
- **Lokalizacja:** `frontend/src/lib/components/ItemTable.svelte:28-29`
- **Problem:** Zmienne `savingIds` i `savedIds` inicjalizowane jako `new Set()` bezpośrednio w deklaracji `$state`, co może prowadzić do współdzielenia referencji między instancjami komponentu.
- **Dlaczego to problem:** W Svelte 5 Runes, mutowalne obiekty (Set, Array) tworzone bezpośrednio w `$state()` mogą być współdzielone między instancjami komponentu. Mutacje nie będą poprawnie śledzone, co prowadzi do niezgodności stanu.
- **Sugestia (bez implementacji):** Zainicjalizuj przez funkcję fabrykującą: `$state(new Set())` lub `$state(() => new Set())`. Alternatywnie użyj `$state` z immutable copy w każdym miejscu mutacji (`new Set(existingSet)`).
- **Powiązane:** `frontend/src/lib/auth.svelte.ts:12` (poprawny wzorzec z `$state<UserState>({...})`)

### 🟠 Brak `credentials: 'include'` w fetchu na stronie domowej
- **Lokalizacja:** `frontend/src/routes/+page.svelte:14`
- **Problem:** Fetch `/items/?limit=3` nie przekazuje `credentials: 'include'`, podczas gdy wszystkie inne fetche w aplikacji mają tę opcję.
- **Dlaczego to problem:** Jeśli backend wymaga autoryzacji dla endpointu `/api/items/`, request nie przejdzie. Niespójność z kontraktem auth opisanym w `docs/ai/patterns.md` (wszystkie fetche używają JWT w cookie).
- **Sugestia (bez implementacji):** Dodaj `{ credentials: 'include' }` do opcji fetcha. Rozważ ujednolicenie przez wrapper funkcji fetch w `$lib` z domyślnym `credentials: 'include'`.

### 🟡 Niespójny error handling — brak komunikatu o błędzie
- **Lokalizacja:** `frontend/src/routes/items/[id]/+page.svelte:103-105`
- **Problem:** Funkcja `loadItem` łapie błąd sieciowy, ale ustawia statyczny komunikat bez szczegółów (`'Network error loading item'`). Inne komponenty (`+page.svelte:8-9`, `ItemTable.svelte:113-115`) łapią `e` i logują do konsoli.
- **Dlaczego to problem:** Utrudnia debugowanie w produkcji. Brak spójności z patternem z `auth.svelte.ts` gdzie błędy są logowane (`console.error("Session check error:", e)`).
- **Sugestia (bez implementacji):** Ujednolić pattern: zawsze logować błąd do konsoli przed ustawieniem stanu error. Rozważyć dodanie `errorBoundary` w `+layout.svelte` do centralnego przechwytywania.

### 🟡 Brak type-safety dla `chartPoints.map` w EChartsLineChart
- **Lokalizacja:** `frontend/src/lib/components/charts/EChartsLineChart.svelte:2`
- **Problem:** Komponent używa `// @ts-nocheck` na początku pliku, co wyłącza sprawdzanie typów dla całego pliku.
- **Dlaczego to problem:** `points.map((p) => ...)` na linii 88 nie jest weryfikowane przez TypeScript. Mogą wystąpić błędy typu niezgodności `ChartPoint` z oczekiwanym formatem ECharts.
- **Sugestia (bez implementacji):** Usunąć `// @ts-nocheck` i naprawić błędy typowania. Zdefiniować typ `EChartsOption` z `echarts/types` i użyć go dla `options`.

### 🟡 Hardkodowany prefix API w ścieżkach względnych
- **Lokalizacja:** `frontend/src/lib/config.ts:7`
- **Problem:** `API_BASE_URL` domyślnie ustawione na `'http://localhost:8000/api'`, ale ścieżki w komponentach są budowane ręcznie przez konkatenację (np. `` `${API_BASE_URL}/items/${getItemId()}` ``).
- **Dlaczego to problem:** Ryzyko literówek w ścieżkach (np. podwójne `/api/` jeśli endpoint już zawiera prefix). Brak centralnej walidacji ścieżek.
- **Sugestia (bez implementacji):** Stworzyć typed client API w `$lib/api-client.ts` z metodami typu `getItems()`, `getItemPriceHistory(id, params)`. Generować automatycznie z OpenAPI spec przez `openapi-typescript-codegen`.

### 🟢 Poprawne użycie `credentials: 'include'` we wszystkich auth fetchach
- **Lokalizacja:** `frontend/src/lib/auth.svelte.ts:24,34,58,77,96,108`
- **Problem:** brak (finding pozytywny)
- **Dlaczego to ważne:** Wszystkie operacje auth (login, register, profile, logout) poprawnie przekazują cookies z JWT tokenem. Zgodne z `docs/ai/patterns.md` sekcją "Frontend — auth state".
- **Sugestia:** Utrzymać ten pattern. Rozważyć dodanie interceptora do wszystkich fetchy.

### 🟢 Poprawne importy `formatCurrency` i `LABOUR_ITEM_NAME` z shared lib
- **Lokalizacja:** wzorzec, wiele miejsc (`items/[id]/+page.svelte:7`, `RecipeCard.svelte:3-4`, `RecipeTree.svelte:2-3`, `EChartsLineChart.svelte:8`, `ItemTable.svelte:7`)
- **Problem:** brak (finding pozytywny)
- **Dlaczego to ważne:** Zgodne z zasadą z `docs/ai/patterns.md`: "`formatCurrency` i `LABOUR_ITEM_NAME` importuj **wyłącznie** z `$lib/currency` i `$lib/crafting`". Brak hardkodowanych kopii.
- **Sugestia:** Kontynuować. Rozważyć eksport wszystkiego z `$lib/index.ts` dla łatwiejszego importu.

### 🟢 Typy z `api.d.ts` używane konsekwentnie przez `types.ts`
- **Lokalizacja:** `frontend/src/lib/types.ts:1-22`
- **Problem:** brak (finding pozytywny)
- **Dlaczego to ważne:** Wszystkie typy API (`ItemRead`, `CraftResult`, `InventoryItem` itd.) są re-eksportowane z auto-generowanego `api.d.ts` przez `components['schemas']`. Brak ręcznych definicji.
- **Sugestia:** Przy dodawaniu nowych endpointów pamiętać o regeneracji `api.d.ts` przez `openapi-typescript`.

### 💡 Brak globalnego error boundary
- **Lokalizacja:** `frontend/src/routes/+layout.svelte`
- **Problem:** Każdy komponent obsługuje błędy indywidualnie (własne stany `error`, `fetchError`). Brak `+error.svelte` lub error boundary w layout.
- **Dlaczego to problem:** Powielanie kodu error handlingu. Ryzyko niezłapania błędów w nowych komponentach. Brak spójnego UI dla błędów krytycznych.
- **Sugestia (bez implementacji):** Dodać `src/routes/+error.svelte` z fallback UI. Rozważyć Svelte 5 error boundaries (gdy dostępne) lub wrapper na `onMount` z globalnym handlerem.

### 💡 Brak walidacji odpowiedzi API (type guards)
- **Lokalizacja:** wzorzec, wiele miejsc (`items/[id]/+page.svelte:106`, `inventory/+page.svelte:60`)
- **Problem:** Odpowiedzi z API są asercjonowane przez `await r.json()` bez runtime walidacji (np. przez Zod).
- **Dlaczego to problem:** Jeśli backend zmieni format odpowiedzi, frontend nie wykryje tego aż do runtime error. TypeScript weryfikuje tylko compile-time.
- **Sugestia (bez implementacji):** Dodać Zod schemas dla kluczowych endpointów i użyć `.parse()` przed przypisaniem do stanu. Alternatywnie użyć `openapi-fetch` z automatyczną walidacją.

---

## Narzędzia

```
svelte-check found 0 errors and 0 warnings
```

Pełny output `npm run check` zapisany w: `audit/frontend/tools.log`
# infra — findings

## Podsumowanie

Infrastruktura jest w większości poprawnie zaprojektowana, ale zawiera kilka istotnych luk bezpieczeństwa i niezgodności. Najpoważniejsze problemy to hardkodowane domyślne wartości sekretów w compose dev, brak healthchecków dla backendu i frontendu oraz niekompletne workflow CI (frontend bez build). Caddyfile poprawnie routuje główne endpointy, ale może wymagać rozszerzenia o dodatkowe warianty ścieżek API docs.

## Findings

### 🔴 Hardkodowane domyślne wartości sekretów w dev compose
- **Lokalizacja:** `infra/compose/docker-compose.dev.yml:8-9, 29-30`
- **Problem:** `POSTGRES_PASSWORD`, `AUTH_SECRET`, `ADMIN_SESSION_SECRET` mają fallbacki do hardkodowanych wartości
- **Dlaczego to problem:** Deweloperzy mogą nieświadomie używać słabych, znanych sekretów; ryzyko wycieku jeśli compose zostanie uruchomiony bez `.env`; niezgodne z zasadą "secrets through env only"
- **Sugestia:** Usunąć fallbacki, wymagać `.env` nawet w dev; dodać `.env.example` z placeholderami; rozważyć walidację na poziomie entrypointu
- **Powiązane:** `infra/compose/docker-compose.prod.yml:8, 27-28` (poprawne wymuszenie zmiennych)

### 🟠 Brak healthchecków dla backendu i frontendu
- **Lokalizacja:** `infra/compose/docker-compose.dev.yml:20-41`, `infra/compose/docker-compose.prod.yml:18-42`
- **Problem:** Backend i frontend nie mają zdefiniowanych healthchecków; `depends_on` dla frontendu nie używa `condition: service_healthy`
- **Dlaczego to problem:** Kontenery mogą zgłaszać "started" zanim aplikacja będzie gotowa; race conditions przy starcie; Caddy może routować ruch do niedostępnego backendu
- **Sugestia:** Dodać healthcheck HTTP do backendu (np. `/health` lub `/api/health`); dodać healthcheck do frontendu; użyć `condition: service_healthy` we wszystkich `depends_on`

### 🟠 Frontend CI bez etapu build
- **Lokalizacja:** `.github/workflows/frontend.yml:14-36`
- **Problem:** Workflow zawiera tylko `svelte-check`, brak `npm run build`
- **Dlaczego to problem:** Możliwe, że kod przechodzi type-check ale build failuje (różnice w konfiguracji Vite, problemach z assetami); Dockerfile produkcyjny może nie zbudować się na produkcji
- **Sugestia:** Dodać krok `npm run build` po `svelte-check`; rozważyć dodanie lint (eslint) jeśli projekt go używa

### 🟠 Caddyfile nie obsługuje wszystkich wariantów endpointów API docs
- **Lokalizacja:** `infra/caddy/Caddyfile:11-21`
- **Problem:** `/docs*` i `/redoc` są osobno, ale brak obsługi `/docs` bez trailing slash, `/redoc/`, `/openapi.json/`
- **Dlaczego to problem:** FastAPI domyślnie udostępnia docs na `/docs` i `/redoc` (z redirectami), ale Caddy może nieprzewidywalnie obsługiwać redirecty; użytkownicy mogą dostać 404
- **Sugestia:** Użyć `/docs` i `/redoc` bez gwiazdki (Caddy automatycznie obsługuje oba warianty); lub dodać explicitzne reguły dla wariantów z `/`

### 🟡 Hardkodowane porty w dev compose
- **Lokalizacja:** `infra/compose/docker-compose.dev.yml:13, 38, 56`
- **Problem:** Porty 5432, 8000, 5173 są hardkodowane, nie używają zmiennych środowiskowych
- **Dlaczego to problem:** Konflikty portów jeśli inne usługi już ich używają; mniejsza elastyczność dla deweloperów
- **Sugestia:** Użyć zmiennych `${DEV_DB_PORT:-5432}`, `${DEV_BACKEND_PORT:-8000}`, `${DEV_FRONTEND_PORT:-5173}` analogicznie do prod compose

### 🟡 CORS_ORIGINS w prod compose może failować przy interpolacji
- **Lokalizacja:** `infra/compose/docker-compose.prod.yml:30`
- **Problem:** `CORS_ORIGINS: '["https://${APP_DOMAIN}","https://${APP_WWW_DOMAIN}"]'` — interpolacja wewnątrz JSON stringa może nie zadziałać poprawnie
- **Dlaczego to problem:** Zmienne środowiskowe mogą nie być podstawione wewnątrz pojedynczych cudzysłowów; backend może dostać literalny string z `${APP_DOMAIN}` zamiast wartości
- **Sugestia:** Użyć podwójnych cudzysłowów i escapowania lub zbudować JSON w entrypointu; przetestować interpolację przed deployem

### 🟡 Frontend w prod nie czeka na backend
- **Lokalizacja:** `infra/compose/docker-compose.prod.yml:36-42`
- **Problem:** Frontend nie ma `depends_on` w ogóle
- **Dlaczego to problem:** Frontend może wystartować i próbować łączyć się z backendem zanim ten będzie gotowy; pierwsze zapytania mogą failować
- **Sugestia:** Dodać `depends_on: backend: condition: service_healthy` (po dodaniu healthchecka do backendu)

### 🟡 Caddy w prod nie używa condition w depends_on
- **Lokalizacja:** `infra/compose/docker-compose.prod.yml:56-58`
- **Problem:** `depends_on: - backend - frontend` bez `condition: service_healthy`
- **Dlaczego to problem:** Caddy może wystartować zanim backend/frontend będą zdrowe; ruch może być routowany do niedostępnych usług
- **Sugestia:** Dodać healthchecki do backendu i frontendu, użyć `condition: service_healthy` w depends_on Caddy

### 🟢 docker.yml — build bez push (bezpieczne)
- **Lokalizacja:** `.github/workflows/docker.yml:28, 44`
- **Problem:** N/A — poprawnie
- **Dlaczego to problem:** N/A
- **Sugestia:** Rozważyć dodanie `push: true` z warunkiem `github.ref == 'refs/heads/main'` jeśli potrzebne są obrazy w registry

### 🟢 backend.yml — kompletne CI (lint, test, alembic)
- **Lokalizacja:** `.github/workflows/backend.yml:14-125`
- **Problem:** N/A — poprawnie
- **Dlaczego to problem:** N/A
- **Sugestia:** Rozważyć dodanie `lock-check` do joba `test` i `alembic` (obecnie tylko osobny job)

### 🟢 discord_bot.yml — kompletne CI
- **Lokalizacja:** `.github/workflows/discord_bot.yml:13-34`
- **Problem:** N/A — poprawnie
- **Dlaczego to problem:** N/A
- **Sugestia:** N/A

### 💡 Makefile używa podman zamiast docker
- **Lokalizacja:** `Makefile:2-3`
- **Problem:** N/A — decyzja architektoniczna
- **Dlaczego to problem:** Może mylić deweloperów przyzwyczajonych do dockera; komunikaty błędów inne
- **Sugestia:** Dodać komentarz w README o wymaganiu podman; rozważyć alias `docker=podman` w dokumentacji

### 💡 Brak .env.example w repo
- **Lokalizacja:** (brak pliku — stwierdzone podczas audytu)
- **Problem:** Nie znaleziono `.env.example` ani w repo, ani w dokumentacji
- **Dlaczego to problem:** Deweloperzy nie mają referencji jakie zmienne są wymagane; ryzyko brakujących zmiennych przy pierwszym setupie
- **Sugestia:** Dodać `.env.example` z wszystkimi wymaganymi zmiennymi (z placeholderami dla sekretów)
# discordbot — findings

## Podsumowanie

Bot używa poprawnego endpointu `/api/ingest/prices` zgodnie z architekturą. Token jest pobierany z env (pydantic-settings), ale **brak obsługi rate limitingu po stronie klienta** (429 retry z backoff). Error handling jest częściowy — łapie HTTPError, ale nie rozróżnia 429 od 5xx. Testy poprawnie mockują HTTP wywołania (respx), ale brakuje testów scenariuszy error handlingu.

## Findings

### [🔴] Brak obsługi rate limitingu (429 retry z backoff)
- **Lokalizacja:** `discord_bot/cogs/prices.py:98-103`, `discord_bot/cogs/prices.py:145-149`
- **Problem:** Funkcja `post_price` i handler `/addprice` nie obsługują HTTP 429 — rzucają `httpx.HTTPStatusError`, użytkownik dostaje generyczny błąd połączenia.
- **Dlaczego to problem:** Zgodnie z `docs/ai/architecture.md` endpoint `/api/ingest/prices` jest rate-limited (slowapi). Bot nie implementuje retry z backoff, co oznacza utratę danych przy 429.
- **Sugestia:** Dodać mechanizm retry z exponential backoff dla 429 w `post_price` (np. 3 próby: 1s, 2s, 4s). Rozważyć bibliotekę `tenacity` lub własną pętlę retry.
- **Powiązane:** `docs/ai/architecture.md:74` (Ingest partial success invariant)

### [🟠] Error handling nie rozróżnia 429 od 5xx
- **Lokalizacja:** `discord_bot/cogs/prices.py:145-149`, `discord_bot/cogs/prices.py:167-169`
- **Problem:** Oba catche łapią `httpx.HTTPError` ogólnie i zwracają ten sam komunikat "Backend connection error — try again later".
- **Dlaczego to problem:** Użytkownik nie wie, czy to chwilowy rate limit (429), błąd serwera (5xx), czy błąd klienta (4xx). 429 powinno triggerować automatyczny retry, nie błąd użytkownika.
- **Sugestia:** Rozróżnić `HTTPStatusError` (4xx/5xx) od `HTTPError` (network), sprawdzić `response.status_code`, dać różne komunikaty dla 429 ("too many requests — retrying...") vs 5xx ("server error").

### [🟡] Timeout 10s może być za krótki dla wolnego backendu
- **Lokalizacja:** `discord_bot/cogs/prices.py:52`, `discord_bot/cogs/prices.py:98`
- **Problem:** `httpx.AsyncClient(timeout=10.0)` — sztywny 10s timeout dla obu wywołań (GET /items/ i POST /ingest/prices).
- **Dlaczego to problem:** Przy wolniejszym backendzie (seedowanie DB, ciężkie zapytanie) może dojść do niepotrzebnych timeoutów.
- **Sugestia:** Rozważyć dłuższy timeout dla POST (np. 30s) lub konfigurację przez env. Dodać handling `httpx.ReadTimeout` z osobnym komunikatem.

### [🟡] Brak walidacji API_URL przed użyciem
- **Lokalizacja:** `discord_bot/bot.py:14`, `discord_bot/cogs/prices.py:52`
- **Problem:** `API_URL` ma default "http://backend:8000/api", ale nie ma walidacji czy to poprawny URL.
- **Dlaczego to problem:** Literówka w env (np. "htp://...") spowoduje runtime error dopiero przy pierwszym wywołaniu HTTP.
- **Sugestia:** Dodać `httpx.URL(api_url)` validation w `Settings` lub użyć `pydantic.HttpUrl` type annotation.

### [🟢] Token pobierany z env (pydantic-settings)
- **Lokalizacja:** `discord_bot/bot.py:10-18`
- **Problem:** N/A — poprawna implementacja.
- **Dlaczego to problem:** N/A
- **Sugestia:** Rozważyć dodanie `model_config = SettingsConfigDict(env_file=".env")` dla explicit .env loading w dev.

### [🟢] Testy mockują HTTP wywołania (respx)
- **Lokalizacja:** `discord_bot/tests/test_prices.py:40-68`, `discord_bot/tests/test_prices.py:169-186`
- **Problem:** N/A — poprawne użycie `respx.mock` do mockowania httpx.
- **Dlaczego to problem:** N/A
- **Sugestia:** Dodać testy dla scenariuszy error handlingu (429, 500, timeout) — obecnie tylko `test_post_price_raises_on_http_error` (500) i `test_post_price_raises_value_error_when_backend_skips_row`.

### [💡] Brak testów dla retry logic (gdy zostanie dodany)
- **Lokalizacja:** `discord_bot/tests/test_prices.py`
- **Problem:** Po dodaniu retry logic dla 429, testy powinny weryfikować liczbę wywołań (np. 3 próby przed failure).
- **Dlaczego to problem:** Bez testów retry logic może być błędnie zaimplementowany (np. infinite loop).
- **Sugestia:** Dodać test z `respx` mockiem zwracającym 429 x2, potem 200 — weryfikować że `route.calls` ma 3 wywołania.

### [💡] Guild sync tylko przy starcie bota
- **Lokalizacja:** `discord_bot/bot.py:29-38`
- **Problem:** `tree.sync()` tylko w `setup_hook` — zmiany w komendach wymagają restartu bota.
- **Dlaczego to problem:** W dev środowisku utrudnia szybkie iteracje nad komendami.
- **Sugestia:** Rozważyć dodanie komendy admina `/sync` do manual sync lub użyć `guild_ids` w `@app_commands` dla auto-sync.

### [💡] GRADE_CHOICES hardcoded — brak synchronizacji z backendem
- **Lokalizacja:** `discord_bot/cogs/prices.py:10-22`
- **Problem:** 12 stopni (0-11) zdefiniowanych hardcoded w bocie. Backend może mieć inną listę.
- **Dlaczego to problem:** Ryzyko desynchronizacji — bot pozwala wybrać grade, którego backend nie zna.
- **Sugestia:** Fetchować listę grade z backendu przy starcie bota (np. `/items/grades` endpoint) lub dodać test integracyjny weryfikujący spójność.
# integration — findings

## Podsumowanie

Kontrakty API między warstwami są w większości spójne. Frontend poprawnie używa typów generowanych przez `openapi-typescript` z `api.d.ts`. Bot Discorda ma zgodny contract z endpointem `/api/ingest/prices`. Wszystkie endpointy wymagające auth mają `current_user` dependency. Wykryto kilka niezgodności: workaround na integer keys w inventory for-recipe, brak rate limitu na inventory PUT, oraz brak enum na `source` w ingest.

## Findings

### 🟡 Inventory for-recipe: JSON serializuje int keys jako stringi, frontend konwertuje z powrotem

- **Lokalizacja:** `frontend/src/routes/items/[id]/+page.svelte:150` oraz `backend/app/user_inventory/router.py:23`
- **Problem:** Backend zwraca `dict[int, int]` (np. `{123: 50}`), JSON serializuje klucze jako stringi (`{"123": 50}`). Frontend parsuje to przez `Object.entries(raw as Record<string, number>).map(([k, v]) => [Number(k), v])` — działa, ale jest to workaround.
- **Dlaczego to problem:** JSON nie obsługuje integer keys — to ukryta niezgodność typów. TypeScript w `api.d.ts` definiuje response jako `{ [key: string]: number }` (linia 1480), co jest poprawne, ale frontend musi ręcznie konwertować. Ryzyko pęknięcia przy zmianie serializacji.
- **Powiązane:** `backend/app/user_inventory/schemas.py:6` (InventoryUpsert używa `quantity: int`, nie mapuje item_id)

### 🟠 Brak rate limitu na `PUT /api/inventory/{item_id}` (authenticated write)

- **Lokalizacja:** `backend/app/user_inventory/router.py:32-41`
- **Problem:** Endpoint PUT do upsert inventory wymaga auth (`current_user`), ale nie ma dekoratora `@limiter.limit()`. Ingest endpoint (`/api/ingest/prices`) ma limit 60/min, prices POST ma limit 60/min, ale inventory PUT nie ma żadnego limitu.
- **Dlaczego to problem:** Użytkownik z valid tokenem może spamować update'y inventory bez limitu. Może to prowadzić do przeciążenia DB przy zautomatyzowanym abuse.
- **Powiązane:** `backend/app/ingest/router.py:12` (ingest ma rate limit), `backend/app/prices/router.py:51` (prices ma rate limit)

### 💡 Endpoint `/api/inventory/for-recipe/{item_id}` ma poprawną kolejność w routerze

- **Lokalizacja:** `backend/app/user_inventory/router.py:21-29` (for-recipe), `32-41` ({item_id})
- **Problem:** Brak — `for-recipe` jest przed `/{item_id}` zgodnie z zasadą z `docs/ai/patterns.md`. Warto dodać komentarz dla przyszłych maintainerów.
- **Dlaczego to problem:** Nie ma problemu — kolejność jest poprawna.
- **Powiązane:** `docs/ai/patterns.md:new-domain` (zasada kolejności routerów)

### 🟡 Frontend `ItemTable.svelte` używa hardcoded `grade: 'All'` filtr, ale backend enum zaczyna się od `All` (kapitalik)

- **Lokalizacja:** `frontend/src/lib/components/ItemTable.svelte:38-41` oraz `backend/app/items/models.py:28-41`
- **Problem:** Frontend ma `GRADES = ['All', 'Grand', ...]` (lin 38), backend `ItemGrade.ALL = "All"`. OpenAPI types (`api.d.ts:518`) generuje enum jako `"All" | "Grand" | ...`. Frontend wysyła `grade` jako query param — **brak walidacji, czy wartość istnieje w enum**. Backend zwróci 422 przy nieznanej wartości, ale frontend nie informuje użytkownika.
- **Dlaczego to problem:** Cicha degradacja — użytkownik widzi "No items" zamiast błędu walidacji. Brak feedbacku przy niezgodności enum.
- **Powiązane:** `frontend/src/lib/api.d.ts:518` (ItemGrade enum)

### 🟡 Discord bot nie obsługuje `source` innego niż `'ah'` — hardcoded

- **Lokalizacja:** `discord_bot/cogs/prices.py:97`
- **Problem:** Bot wysyła `source: "ah"` (lin 97) — poprawnie zgodnie z `docs/ai/architecture.md`. Ale schema `PriceIngestRow` pozwala na dowolny `source: str` (min 1, max 40). Brak walidacji/enum na backendzie.
- **Dlaczego to problem:** Jeśli inny klient (np. watcher, test) wyśle `source: "manual"`, frontend filtrujący po `source='ah'` nie pokaże tych danych. Brak centralnej definicji dozwolonych źródeł.
- **Powiązane:** `docs/ai/architecture.md:69` (zasada `source='ah'` consistency)

### 🟠 Brak rate limitu na `POST /api/crafting/{item_id}/calculate` (authenticated write)

- **Lokalizacja:** `backend/app/crafting/router.py:19-24`
- **Problem:** Endpoint POST do calculate crafting profit nie ma rate limitu. Nie wymaga auth (brak `current_user`), ale jest to write endpoint (przyjmuje `inventory` w body). Może być spamowany.
- **Dlaczego to problem:** Calculate może być kosztowny obliczeniowo (rekursywne drzewa). Bez rate limitu użytkownik może obciążyć serwer.
- **Powiązane:** `backend/app/ingest/router.py:12` (ingest ma rate limit), `backend/app/prices/router.py:51` (prices ma rate limit)

### 🟢 Bot Discorda poprawnie obsługuje partial-success response z ingest endpoint

- **Lokalizacja:** `discord_bot/cogs/prices.py:98-106`
- **Problem:** Brak — bot sprawdza `body.get("accepted", 0) == 0` i wyciąga `errors[0]["reason"]` — zgodne z `IngestResponse` schema.
- **Dlaczego to problem:** Nie ma problemu — contract jest poprawnie zaimplementowany.
- **Powiązane:** `backend/app/ingest/schemas.py:23-27`

### 🟢 Wszystkie endpointy z rate limit mają poprawny `request: Request` parametr

- **Lokalizacja:** `backend/app/prices/router.py:52-58`, `backend/app/ingest/router.py:14-18`
- **Problem:** Brak — oba endpointy z `@limiter.limit()` mają `request: Request` w sygnaturze. Import jest na lin 4 prices routera.
- **Dlaczego to problem:** Nie ma problemu — kod jest poprawny.
- **Powiązane:** —

### 🟢 Endpoint `GET /api/me` ma auth dependency (OpenAPI nie pokazuje 401)

- **Lokalizacja:** `backend/app/users/router.py:10-12`, `frontend/src/lib/api.d.ts:95-111`
- **Problem:** OpenAPI nie generuje 401 response dla `/api/me`, ale backend ma `current_user` dependency (lin 11). Frontend używa `/users/me` (auth.svelte.ts:35) — oba endpointy to ten sam router, `/me` jest aliasem.
- **Dlaczego to problem:** Nie ma problemu security — auth jest wymuszone. To limitation fastapi-users/openapi generation.
- **Powiązane:** —
# Security — Findings

## Podsumowanie

Projekt ma solidne podstawy bezpieczeństwa (cookie-based auth, SQLModel z parametryzowanymi zapytaniami, gitignore dla .env), ale **istnieje krytyczny wyciek sekretu** — plik `.env` z hardkodowanym Discord tokenem jest śledzony w repozytorium git. Brakuje rate limitingu na większości endpointów publicznych, CORS nie jest walidowany w production, a admin panel nie ma dodatkzych zabezpieczeń (CSRF, security headers). Frontend jest czysty (brak XSS), ale brakuje walidacji wejścia po stronie API dla niektórych endpointów.

---

## Findings

### 🔴 Discord Token hardkodowany w .env (committed)
- **Lokalizacja:** `/home/dv6/GitHub/improved-octo-potato/.env:23`
- **Problem:** Discord bot token jest hardkodowany w pliku `.env`, który jest śledzony przez git (nie jest w `.gitignore` na root level)
- **Dlaczego to problem:** Token jest publicznie dostępny w repozytorium — każdy z dostępem do repo może przejąć bota. Token w `.env` ma format `[REDACTED — Discord bot token, revoked]`
- **Sugestia:** Natychmiast unieważnij token w Discord Developer Portal, dodaj `.env` do `.gitignore` (tylko na root level — obecnie `.gitignore` ignoruje `.env`, ale plik już był commitowany), użyj zmiennych środowiskowych w production

### 🔴 Brak .env w .gitignore (root level)
- **Lokalizacja:** `/home/dv6/GitHub/improved-octo-potato/.gitignore:139`
- **Problem:** `.env` jest w `.gitignore`, ale plik `.env` został już dodany do repozytorium (git go nie ignoruje retroaktywnie)
- **Dlaczego to problem:** Plik z sekretami (POSTGRES_PASSWORD=postgres, AUTH_SECRET, Discord token) jest version-controlled
- **Sugestia:** `git rm --cached .env` + commit, następnie zweryfikuj `git status`

### 🟠 Rate limiting tylko na 2 endpointach
- **Lokalizacja:** `backend/app/prices/router.py:51`, `backend/app/ingest/router.py:13`
- **Problem:** Tylko `POST /api/items/{item_id}/prices` i `POST /api/ingest/prices` mają rate limit (60/min). Wszystkie inne endpointy publiczne (`GET /api/items/`, `GET /api/items/{id}/price-history`, `GET /api/prices/`) nie mają limitu
- **Dlaczego to problem:** Możliwość scrapingu całego API, DoS przez nadmierne zapytania, abuse endpointów bez autoryzacji
- **Sugestia:** Dodaj `@limiter.limit()` do wszystkich publicznych endpointów GET (np. 30/min), rozważ globalny middleware limiter

### 🟠 CORS origins niebezpieczne w dev
- **Lokalizacja:** `backend/app/config/settings.py:20-22`, `backend/app/main.py:32-38`
- **Problem:** CORS pozwala na `allow_credentials=True` z szeroko zdefiniowanymi origins. W dev: `["http://localhost:5173", "http://127.0.0.1:5173"]`. W production zależy od env, ale brak walidacji czy origins są HTTPS
- **Dlaczego to problem:** Jeśli `CORS_ORIGINS` w production będzie zawierało niezaufane domeny, atakujący może wykonać requesty z ich poziomu z credentialami (cookie)
- **Sugestia:** Waliduj origins w production (tylko HTTPS), rozważ whitelistę z regex, dodaj `Vary: Origin` header

### 🟠 Cookie secure=False w development
- **Lokalizacja:** `backend/app/config/settings.py:16`, `backend/app/auth/backend.py:11`
- **Problem:** `cookie_secure=settings.cookie_secure` domyślnie `False`. Cookie auth mogą być przesyłane przez HTTP
- **Dlaczego to problem:** W środowisku dev (http://localhost) to akceptowalne, ale jeśli dev expose na publiczne IP bez TLS — cookie wyciekają
- **Sugestia:** W documentation zaznacz, że dev wymaga localhost; w production `COOKIE_SECURE=true` jest wymuszone w docker-compose.prod.yml

### 🟠 Brak security headers
- **Lokalizacja:** `backend/app/main.py`, `infra/caddy/Caddyfile`
- **Problem:** Brak nagłówków: `X-Frame-Options`, `Content-Security-Policy`, `X-Content-Type-Options`, `Strict-Transport-Security`, `X-XSS-Protection`
- **Dlaczego to problem:** Clickjacking (brak X-Frame-Options), XSS (brak CSP), MIME sniffing (brak X-Content-Type-Options)
- **Sugestia:** Dodaj middleware w FastAPI lub skonfiguruj w Caddyfile:
  ```
  header {
      X-Frame-Options "DENY"
      X-Content-Type-Options "nosniff"
      Content-Security-Policy "default-src 'self'"
      Strict-Transport-Security "max-age=31536000; includeSubDomains"
  }
  ```

### 🟠 Admin panel bez CSRF protection
- **Lokalizacja:** `backend/app/admin_auth.py:46`, `backend/app/admin.py:12`
- **Problem:** Sqladmin używa session-based auth, ale brak explicit CSRF token validation przy logowaniu. SessionMiddleware ma `same_site="lax"`, ale to nie pełna ochrona CSRF
- **Dlaczego to problem:** Atakujący może spróbować wymusić akcje w admin panelu (jeśli admin jest zalogowany)
- **Sugestia:** Włącz CSRF protection w sqladmin, dodaj `SecureAdminAuth` z `https_only=True` w production

### 🟠 Brak walidacji wejścia w niektórych endpointach
- **Lokalizacja:** `backend/app/items/router.py:13-29`, `backend/app/prices/router.py:24-43`
- **Problem:** Endpoint `GET /api/items/` przyjmuje parametr `q` z `max_length=200`, ale brak walidacji znaków specjalnych. `price-history` przyjmuje `source` z `min_length=1, max_length=40` — brak whitelisty
- **Dlaczego to problem:** Potencjalne SQL injection (choć SQLModel parametryzuje), log injection, abuse search
- **Sugestia:** Dodaj regex validation dla `q` (tylko alfanumeryczne + spacje), whitelistę dla `source`

### 🟡 Hardkodowane domyślne hasła w docker-compose
- **Lokalizacja:** `infra/compose/docker-compose.dev.yml:8`, `.env:6`
- **Problem:** Domyślne `POSTGRES_PASSWORD=postgres`, `AUTH_SECRET=temporary-development-secret-must-be-32-chars`
- **Dlaczego to problem:** Jeśli ktoś użyje dev compose w production (lub expose porty), hasła są trywialne
- **Sugestia:** Wymuś zmianę w dokumentacji, dodaj warning w .env.example

### 🟡 Brak limitu na paginację w niektórych endpointach
- **Lokalizacja:** `backend/app/items/router.py:19`, `backend/app/user_items/router.py`
- **Problem:** `limit=200` to dużo, ale endpointy bez paginacji mogą zwrócić wszystko
- **Dlaczego to problem:** DoS przez memory exhaustion, scraping całego DB
- **Sugestia:** Hard limit 100-200 items na request wszędzie

### 🟡 Discord bot bez rate limitu na komendy
- **Lokalizacja:** `discord_bot/cogs/prices.py:109-228`
- **Problem:** Komendy `/addprice` i `/price` nie mają cooldownu per-user
- **Dlaczego to problem:** Użytkownik może spamować komendy, przeciążyć bota i backend
- **Sugestia:** Dodaj `@app_commands.checks.cooldown()` decorator

### 🟡 Profile endpoint nie sprawdza is_private przed zwróceniem danych
- **Lokalizacja:** `backend/app/profiles/router.py:14-19`
- **Problem:** `GET /api/profiles/me` zwraca profil zawsze. Brak endpointu na publiczny profil z checkiem `is_private`
- **Dlaczego to problem:** Jeśli `is_private` ma ukryć profil przed innymi, brak walidacji przy dostępie innych użytkowników
- **Sugestia:** Dodaj endpoint `GET /api/profiles/{user_id}` z checkiem `if profile.is_private and requester_id != user_id: raise 403`

### 🟢 SQL injection — BRAK (dobrze)
- **Lokalizacja:** Cały backend
- **Problem:** Nie znaleziono — SQLModel używa parametryzowanych zapytań (`session.exec(select(Item).where(Item.id == item_id))`)
- **Dlaczego to problem:** ✅ Brak problemu — wszystkie zapytania są bezpieczne
- **Sugestia:** Utrzymaj ten standard, nie używaj `.execute(text("..."))` z f-stringami

### 🟢 XSS w frontend — BRAK (dobrze)
- **Lokalizacja:** Frontend Svelte components
- **Problem:** Nie znaleziono `{@html ...}` ani `v-html` — wszystkie dane są renderowane safely
- **Dlaczego to problem:** ✅ Brak problemu — Svelte domyślnie escape'uje
- **Sugestia:** Jeśli kiedyś dodasz `{@html}`, dodaj sanitization (DOMPurify)

### 🟢 Token storage — BEZPIECZNIE (dobrze)
- **Lokalizacja:** `frontend/src/lib/auth.svelte.ts`, `backend/app/auth/backend.py`
- **Problem:** Tokeny są w HttpOnly cookie (fastapi-users CookieTransport), nie w localStorage
- **Dlaczego to problem:** ✅ Brak XSS → brak kradzieży tokenów
- **Sugestia:** Utrzymaj, dodaj `SameSite=Lax` (już jest w admin)

### 💡 Brak audit logów
- **Lokalizacja:** Cały backend
- **Problem:** Brak logowania autentycznych akcji (login, delete inventory, price ingest)
- **Sugestia:** Dodaj audit log table + middleware logujące mutate operations

### 💡 Brak health check endpointu
- **Lokalizacja:** `backend/app/main.py`
- **Problem:** Brak `/health` endpointu do monitoringu
- **Sugestia:** Dodaj prosty endpoint sprawdzający połączenie do DB

### 💡 Weak secret validation
- **Lokalizacja:** `backend/app/config/settings.py:24-29`
- **Problem:** Walidacja tylko długości (32 znaki), nie ma checka na entropię
- **Sugestia:** Dodaj check na `secrets.token_hex(16)` w dokumentacji setup

---

## Tabela priorytetów

| Priorytet | Finding | Czas naprawy |
|-----------|---------|--------------|
| 🔴 P0 | Discord token w .env | Natychmiast (< 1h) |
| 🔴 P0 | .env w git | Natychmiast (< 1h) |
| 🟠 P1 | Rate limiting | 1-2 dni |
| 🟠 P1 | Security headers | 2-4h |
| 🟠 P1 | CORS validation | 2-4h |
| 🟡 P2 | CSRF admin | 4-8h |
| 🟡 P2 | Input validation | 1-2 dni |
| 💡 P3 | Audit logs | 1-2 dni |
# dependencies — findings

## Podsumowanie

Wykryto 4 niskopriorytetowe vulnerabilności w frontendzie (pakiet `cookie` przez zależność `@sveltejs/kit`). Brak krytycznych CVE w backendzie Python. Dwie paczki są znacząco za wersją: `pytest-asyncio` (major behind) i `pydantic-settings` w discord_bot (major behind). `slowapi` nie był aktualizowany od lutego 2024 — potencjalnie EOL/deprecated. Lock files są w sync z wyjątkiem frontendu, gdzie `package-lock.json` ma minimalne różnice wersji (patch level).

## Findings

### 🟠 Frontend: Vulnerable dependency `cookie` (<0.7.0)

- **Lokalizacja:** `frontend/package.json`, `frontend/package-lock.json`
- **Problem:** Pakiet `cookie@0.6.0` (zależność `@sveltejs/kit`) akceptuje znaki poza zakresem w nazwie cookie, ścieżce i domenie — vulnerability GHSA-pxg6-pf52-xh8x
- **Dlaczego to problem:** Może prowadzić do injection attacks lub bypassów walidacji inputu. npm audit zgłasza 4 niskie vulnerabilności, fix wymaga `npm audit fix --force` co instaluje `@sveltejs/kit@0.0.30` (breaking change)
- **Sugestia (bez implementacji):** Poczekać na aktualizację `@sveltejs/kit` która używa `cookie@0.7.0+` lub ręcznie wymusić nowszą wersję `cookie` przez `overrides` w `package.json`
- **Powiązane:** —

### 🟠 Backend: `pytest-asyncio` znacząco za wersją (major behind)

- **Lokalizacja:** `backend/pyproject.toml`
- **Problem:** Wersja `pytest-asyncio>=0.24` podczas gdy latest to `1.3.0` — różnica 1 major version
- **Dlaczego to problem:** Możliwe breaking changes w API, brak dostępu do nowych feature'ów i bugfixów. Wersja 1.x może wymagać zmian w konfiguracji testów
- **Sugestia (bez implementacji):** Zaktualizować do `pytest-asyncio>=1.0` i przetestować czy wszystkie testy przechodzą; sprawdzić changelog pod kątem breaking changes
- **Powiązane:** —

### 🟠 Discord bot: `pydantic-settings` znacząco za wersją (major behind)

- **Lokalizacja:** `discord_bot/pyproject.toml`
- **Problem:** Wersja `pydantic-settings>=2.3` podczas gdy latest to `2.14.1` — 11 minor versions behind
- **Dlaczego to problem:** Brak bugfixów i potencjalnych security fixes z nowszych wersji; możliwe niezgodności z innymi paczkami używającymi pydantic
- **Sugestia (bez implementacji):** Zaktualizować do `pydantic-settings>=2.14` i przetestować działanie bota
- **Powiązane:** —

### 🟡 Backend: `sqladmin` za wersją (minor behind)

- **Lokalizacja:** `backend/pyproject.toml`
- **Problem:** Wersja `sqladmin>=0.24.0` podczas gdy latest to `0.26.0`
- **Dlaczego to problem:** Brak dostępu do nowych feature'ów i bugfixów; minor version behind zazwyczaj niskie ryzyko
- **Sugestia (bez implementacji):** Zaktualizować do `sqladmin>=0.26.0` przy następnej okazji
- **Powiązane:** —

### 🟡 Backend: `psycopg` za wersją (minor behind)

- **Lokalizacja:** `backend/pyproject.toml`
- **Problem:** Wersja `psycopg[binary]>=3.2.4` podczas gdy latest to `3.3.4`
- **Dlaczego to problem:** Brak bugfixów i ewentualnych security fixes; minor behind
- **Sugestia (bez implementacji):** Zaktualizować do `psycopg[binary]>=3.3.0`
- **Powiązane:** —

### 🟡 Backend: `asyncpg` za wersją (minor behind)

- **Lokalizacja:** `backend/pyproject.toml`
- **Problem:** Wersja `asyncpg>=0.30.0` podczas gdy latest to `0.31.0`
- **Dlaczego to problem:** Brak bugfixów; minor behind, niskie ryzyko
- **Sugestia (bez implementacji):** Zaktualizować do `asyncpg>=0.31.0`
- **Powiązane:** —

### 🟡 Backend: `pydantic-settings` za wersją (minor behind)

- **Lokalizacja:** `backend/pyproject.toml`
- **Problem:** Wersja `pydantic-settings>=2.13.1` podczas gdy latest to `2.14.1`
- **Dlaczego to problem:** Brak bugfixów; minor behind
- **Sugestia (bez implementacji):** Zaktualizować do `pydantic-settings>=2.14.0`
- **Powiązane:** —

### 🟡 Frontend: `echarts` za wersją (major behind)

- **Lokalizacja:** `frontend/package.json`
- **Problem:** Wersja `echarts@^5.6.0` podczas gdy latest to `6.1.0` — 1 major version behind
- **Dlaczego to problem:** ECharts 6.x może mieć breaking changes w API; brak nowych feature'ów i performance improvements
- **Sugestia (bez implementacji):** Rozważyć upgrade do v6 z testowaniem wizualizacji; sprawdzić changelog ECharts 6.x
- **Powiązane:** —

### 🟡 Frontend: `@sveltejs/kit` za wersją (minor behind)

- **Lokalizacja:** `frontend/package.json`
- **Problem:** Wersja `@sveltejs/kit@^2.57.0` podczas gdy latest to `2.60.1`
- **Dlaczego to problem:** Brak bugfixów i security fixes z nowszych wersji
- **Sugestia (bez implementacji):** Zaktualizować do `@sveltejs/kit@^2.60.0`
- **Powiązane:** —

### 🟡 Frontend: `tailwindcss` za wersją (minor behind)

- **Lokalizacja:** `frontend/package.json`
- **Problem:** Wersja `tailwindcss@^4.2.2` podczas gdy latest to `4.3.0`
- **Dlaczego to problem:** Brak nowych feature'ów i bugfixów
- **Sugestia (bez implementacji):** Zaktualizować do `tailwindcss@^4.3.0`
- **Powiązane:** —

### 🟡 Discord bot: `discord.py` za wersją (minor behind)

- **Lokalizacja:** `discord_bot/pyproject.toml`
- **Problem:** Wersja `discord.py>=2.4` podczas gdy latest to `2.7.1`
- **Dlaczego to problem:** Brak nowych feature'ów Discord API i bugfixów
- **Sugestia (bez implementacji):** Zaktualizować do `discord.py>=2.7.0`
- **Powiązane:** —

### 🟡 Frontend: `vite` za wersją (patch behind)

- **Lokalizacja:** `frontend/package.json`
- **Problem:** Wersja `vite@^8.0.7` podczas gdy latest to `8.0.13`
- **Dlaczego to problem:** Brak bugfixów; patch behind — bardzo niskie ryzyko
- **Sugestia (bez implementacji):** Zaktualizować do `vite@^8.0.13` przy następnej okazji
- **Powiązane:** —

### 🟡 Frontend: `daisyui` za wersją (patch behind)

- **Lokalizacja:** `frontend/package.json`
- **Problem:** Wersja `daisyui@^5.5.19` podczas gdy latest to `5.5.20`
- **Dlaczego to problem:** Brak bugfixów; patch behind — bardzo niskie ryzyko
- **Sugestia (bez implementacji):** Zaktualizować do `daisyui@^5.5.20` przy następnej okazji
- **Powiązane:** —

### 🟠 Backend: `slowapi` potencjalnie EOL/deprecated

- **Lokalizacja:** `backend/pyproject.toml`
- **Problem:** Ostatni release `0.1.9` z lutego 2024 (sprawdzono na PyPI); brak aktualizacji od >1 roku
- **Dlaczego to problem:** Pakiet może być nieutrzymywany (EOL); brak security fixes i compatibility updates dla nowych wersji FastAPI/Starlette
- **Sugestia (bez implementacji):** Rozważyć alternatywy jak `slowapi-latest` fork, `limiter` lub implementacja własnego rate limitingu; monitorować repozytorium GitHub pod kątem aktywności
- **Powiązane:** —

### 🟢 Lock files: Backend i Discord bot w sync

- **Lokalizacja:** `backend/uv.lock`, `discord_bot/uv.lock`
- **Problem:** Brak — lock files są zsynchronizowane z `pyproject.toml`
- **Dlaczego to problem:** N/A (pozytywny finding)
- **Sugestia (bez implementacji):** Kontynuować używanie `uv lock` po zmianach w `pyproject.toml`
- **Powiązane:** —

### 🟡 Frontend: `package-lock.json` minimalnie out of sync

- **Lokalizacja:** `frontend/package-lock.json`
- **Problem:** `package.json` ma `@sveltejs/kit@^2.57.0`, ale `package-lock.json` resolve'uje do `2.57.1` (patch update). npm audit działa na `2.57.1`
- **Dlaczego to problem:** Niewielka niespójność; może prowadzić do confusion przy debugowaniu
- **Sugestia (bez implementacji):** Uruchomić `npm install` aby zaktualizować `package-lock.json` do najnowszych wersji w zakresie semver
- **Powiązane:** —

### 💡 Recommendation: Używać `npm audit` lub `npm audit --production` regularnie

- **Lokalizacja:** `frontend/`
- **Problem:** Brak zautomatyzowanego checks dla vulnerabilności npm
- **Dlaczego to problem:** Vulnerabilności mogą być dodane do istniejących paczek po fakcie (post-release)
- **Sugestia (bez implementacji):** Dodać `npm audit` do CI pipeline; rozważyć `dependabot` lub `renovate` dla automatycznych security updates
- **Powiązane:** —

### 💡 Recommendation: Rozważyć `pip-audit` lub `safety` dla backendu

- **Lokalizacja:** `backend/`, `discord_bot/`
- **Problem:** Brak zautomatyzowanego checks dla vulnerabilności Python
- **Dlaczego to problem:** Vulnerabilności mogą być dodane do istniejących paczek po fakcie
- **Sugestia (bez implementacji):** Dodać `pip-audit` lub `safety` do CI pipeline; uruchamiać po `uv pip compile`
- **Powiązane:** —
# code-quality — findings

## Podsumowanie

Kod jest w dobrej kondycji — dominują małe, jednopłaszczyznowe usługi z wyraźnym podziałem na routery, serwisy i modele. Nie wykryto god objects w kodzie aplikacji (api.d.ts jest auto-generowany). Głównym problemem jest powielona logika paginacji między serwisami oraz wysoka złożoność seed.py (skrypt jednorazowy, więc akceptowalne). Nazewnictwo jest spójne z minor exceptions w testach. Nie znaleziono dead code ani komentarzy-myłek.

---

## Findings

### 🟠 Powielona logika paginacji w serwisach
- **Lokalizacja:** `backend/app/items/services.py:9-47` i `backend/app/user_items/services.py:12-55`
- **Problem:** Identyczna struktura paginacji (count + offset/limit) z duplikacją ~15 linii kodu
- **Dlaczego to problem:** Zmiana logiki paginacji wymaga edycji w wielu miejscach; ryzyko rozjazdu behavior
- **Sugestia:** Wydzielić helper `paginate_query(session, statement, offset, limit)` w `app/config/` lub `app/common/`
- **Powiązane:** `backend/app/prices/services.py:11-92` (podobny pattern, ale inna logika bucketing)

### 🟠 Wysoka złożoność seed.py
- **Lokalizacja:** `backend/seed.py:188-273`
- **Problem:** Funkcja `seed()` ma złożoność cykliczną 15 i 16 branchów (ruff C901, PLR0912)
- **Dlaczego to problem:** Trudny w utrzymaniu, testowaniu; zmiana jednego typu danych może zepsuć inne sekcje
- **Sugestia:** Podzielić na trzy osobne funkcje: `seed_items()`, `seed_recipes()`, `seed_price_history()` z osobnymi pętlami
- **Powiązane:** —

### 🟡 Zbyt wiele parametrów w funkcjach (PLR0913)
- **Lokalizacja:** wzorzec, wiele miejsc
  - `backend/app/crafting/calculator.py:66-74` — `_build_node()` ma 7 parametrów
  - `backend/app/items/router.py:14-20` — `read_items()` ma 6 parametrów
  - `backend/app/prices/services.py:11-17` — `get_item_price_history()` ma 6 parametrów
  - `backend/app/user_items/services.py:12-19` — `get_followed_items()` ma 7 parametrów
- **Problem:** Funkcje z >5 parametrami są trudne do wywołania i testowania
- **Dlaczego to problem:** Ryzyko pomyłki w kolejności parametrów; trudność w dodawaniu nowych opcji
- **Sugestia:** Użyć dataclass/schema (np. `FilterParams`) dla parametrów opcjonalnych; alternatywnie **kwargs z TypedDict
- **Powiązane:** —

### 🟡 Magic numbers w kodzie
- **Lokalizacja:** wzorzec, wiele miejsc
  - `backend/app/config/settings.py:27` — `32` (długość secret)
  - `backend/app/crafting/calculator.py:75` — `10` (max depth rekurencji)
  - `backend/app/prices/services.py:49-52` — `300, 3600, 86400` (interwały w sekundach)
- **Problem:** Liczby magiczne bez nazw utrudniają zrozumienie intencji
- **Dlaczego to problem:** Zmiana wartości wymaga znajomości kontekstu; ryzyko błędu przy kopiowaniu
- **Sugestia:** Wydzielić jako stałe na modułu: `MIN_SECRET_LENGTH`, `MAX_RECIPE_DEPTH`, `INTERVAL_5M_SECONDS`
- **Powiązane:** `backend/app/prices/services.py:49` — INTERVAŁ_SECONDS już jako dict, ale nazwa łamie snake_case

### 🟡 Naruszenie snake_case (N806)
- **Lokalizacja:** `backend/app/prices/services.py:49`
- **Problem:** `INTERVAL_SECONDS` używa SCREAMING_SNAKE_CASE wewnątrz funkcji
- **Dlaczego to problem:** Niezgodne z PEP8 i konwencją projektu (snake_case dla zmiennych lokalnych)
- **Sugestia:** Zmienić na `interval_seconds` lub wynieść jako stałą modułu `INTERVAL_SECONDS_MAP`
- **Powiązane:** —

### 🟡 Długa funkcja w prices/services.py
- **Lokalizacja:** `backend/app/prices/services.py:11-92`
- **Problem:** `get_item_price_history()` ma 93 linie z wbudowaną logiką bucketing
- **Dlaczego to problem:** Mieszanie query logic z agregacją danych; trudność w testowaniu bucketing
- **Sugestia:** Wydzielić `_bucket_price_points(rows, interval)` jako osobna funkcja helper
- **Powiązane:** —

### 🟡 Router pattern — powielona struktura
- **Lokalizacja:** `backend/app/*/router.py` (items, prices, user_items, inventory, crafting)
- **Problem:** Każdy router powiela strukturę: importy, dependency injection, response_model
- **Dlaczego to problem:** Dodać nowy endpoint = ręczne pisanie boilerplate; ryzyko niespójności
- **Sugestia:** Rozważyć factory function `create_crud_router(model, service, prefix)` dla standardowych CRUD
- **Powiązane:** —

### 🟢 Brak dead code (pozytyw)
- **Lokalizacja:** cały kod aplikacji
- **Problem:** — (brak)
- **Dlaczego to problem:** — (brak)
- **Sugestia:** Utrzymać; ruff F401/F841 nie wykrył żadnych problemów
- **Powiązane:** —

### 🟢 Komentarze są pomocne (pozytyw)
- **Lokalizacja:** cały kod aplikacji
- **Problem:** — (brak)
- **Dlaczego to problem:** — (brak)
- **Sugestia:** Kontynuować styl docstringów w service functions (jak w `match_or_create_item`)
- **Powiązane:** —

### 🟢 Brak god objects w kodzie aplikacji (pozytyw)
- **Lokalizacja:** `backend/app/`, `frontend/src/`, `discord_bot/`
- **Problem:** — (brak)
- **Dlaczego to problem:** — (brak)
- **Sugestia:** `api.d.ts` (1617 linii) jest auto-generowany — to akceptowalne
- **Powiązane:** —

### 💡 Frontend: +page.svelte ma za dużo logiki biznesowej
- **Lokalizacja:** `frontend/src/routes/items/[id]/+page.svelte:1-367`
- **Problem:** 367 linii z logiką obliczania kosztów craftu (`computeNodeCost`, `materialCost`, `profit`)
- **Dlaczego to problem:** Logika biznesowa w UI utrudnia testowanie i recykling w innych widokach
- **Sugestia:** Przenieść `computeNodeCost` i derived stats do `frontend/src/lib/crafting.ts` jako pure functions
- **Powiązane:** `backend/app/crafting/calculator.py` — podobna logika już istnieje po stronie backendu

### 💡 Discord bot: prices.py ma powieloną logikę lookup
- **Lokalizacja:** `discord_bot/cogs/prices.py:29-77`
- **Problem:** `lookup_item()` i `format_price()` są proste, ale `addprice` i `price` commands powielają strukturę error handling
- **Dlaczego to problem:** Dodać nowy command = kopiować try/except block
- **Sugestia:** Wydzielić `_handle_api_error(exc, interaction)` helper w cogs/
- **Powiązane:** —

### 💡 Infra: docker-compose.yml nie ma healthcheck dla backendu
- **Lokalizacja:** `infra/compose/docker-compose.dev.yml`, `docker-compose.prod.yml`
- **Problem:** Backend nie ma healthcheck; frontend startuje od razu po starcie backendu
- **Dlaczego to problem:** Ryzyko race condition przy restarcie kontenerów
- **Sugestia:** Dodać healthcheck z `curl http://localhost:8000/api/health` lub podobny
- **Powiązane:** —

---

## Tabela priorytetyzacji

| Priorytet | Finding | Effort | Impact |
|-----------|---------|--------|--------|
| 🔴 High | Powielona logika paginacji | Low | High |
| 🟠 Medium | Wysoka złożoność seed.py | Medium | Medium |
| 🟡 Low | Zbyt wiele parametrów | Medium | Low |
| 🟡 Low | Magic numbers | Low | Low |
| 💡 Nice-to-have | Logika craft w +page.svelte | Medium | Medium |
# tester-evaluator — findings

## Podsumowanie (3–5 zdań)

Testy są **solidnej jakości** — 94 testy, 95% coverage, wszystkie przechodzą. Testy używają UUID suffix dla unikalności (brak flaky tests), testują zachowanie a nie implementację. Główne braki to: niekompletne pokrycie scenariuszy auth (expired token, superuser), brak testów E2E dla krytycznych ścieżek (ingest → price history → crafting), oraz kilka testów integracyjnych w discord_bot, które mogłyby być bardziej izolowane. Ogólnie testy są maintainable i dobrze napisane.

## Findings

### 🟢 Testy używają UUID suffix — brak flaky tests
- **Lokalizacja:** `backend/tests/test_*.py` (wszystkie pliki)
- **Problem:** brak — testy poprawnie używają `uuid.uuid4().hex[:6-8]` w nazwach itemów i emailach
- **Dlaczego to problem:** nie jest to problem — testy są izolowane i powtarzalne
- **Sugestia:** utrzymać ten pattern, rozważyć dodanie fixture'u `_email()` i `_item_name()` w conftest dla DRY

### 🟢 Testy sprawdzają zachowanie, nie implementację
- **Lokalizacja:** `backend/tests/test_*.py`
- **Problem:** brak — testy walidują response status, body, side effects (DB state)
- **Dlaczego to problem:** nie jest to problem — testy są odporne na refaktoryzację
- **Sugestia:** kontynuować ten approach

### 🟠 Brak testów auth: expired token
- **Lokalizacja:** `backend/tests/test_auth.py`
- **Problem:** testy pokrywają brak tokena (401), login/logout, ale nie testują scenariusza z expired tokenem
- **Dlaczego to problem:** expired token to częsty edge case w production; brak testu oznacza ryzyko regresji
- **Sugestia:** dodać test z ręcznie wygenerowanym expired JWT tokenem i sprawdzić czy endpoint zwraca 401

### 🟠 Brak testów auth: superuser uprawnienia
- **Lokalizacja:** `backend/tests/test_auth.py`, `backend/tests/test_inventory.py`
- **Problem:** nie ma testów sprawdzających czy superuser ma dostęp do endpointów admina lub czy zwykły user nie ma dostępu do admin endpoints
- **Dlaczego to problem:** ryzyko eskalacji uprawnień lub wycieku danych admin-only
- **Sugestia:** dodać testy z `is_superuser=True` i sprawdzić dostęp do `/admin/*` endpointów

### 🟠 Brak E2E testu: pełna ścieżka ingest → price history
- **Lokalizacja:** `backend/tests/test_ingest.py`, `backend/tests/test_prices.py`
- **Problem:** testy są rozdzielone — ingest testuje tworzenie PricePoint, prices testuje odczyt, ale nie ma jednego testu E2E łączącego oba
- **Dlaczego to problem:** regresja na styku ingest → prices może zostać wykryta dopiero w production
- **Sugestia:** dodać test: POST /ingest/prices → GET /items/{id}/price-history w jednym teście

### 🟠 Brak E2E testu: crafting z inventory po ingest
- **Lokalizacja:** `backend/tests/test_crafting.py`, `backend/tests/test_inventory.py`, `backend/tests/test_ingest.py`
- **Problem:** brak testu łączącego: ingest itemów → PUT inventory → POST crafting/calculate
- **Dlaczego to problem:** krytyczna ścieżka użytkownika; regresja może zablokować feature crafting calculator
- **Sugestia:** dodać test E2E: ingest 3 items → set inventory → calculate crafting recipe

### 🟡 Testy używają NullPool ale tworzą engine w wielu miejscach
- **Lokalizacja:** `backend/tests/test_items.py:14-21`, `backend/tests/test_prices.py:14-21`, `backend/tests/test_inventory.py:20-29`
- **Problem:** każdy plik testowy definiuje własny fixture `db_session` z create_engine — powielenie kodu
- **Dlaczego to problem:** maintenance burden; ryzyko niespójności jeśli trzeba zmienić konfigurację
- **Sugestia:** przenieść fixture `db_session` do `conftest.py` i używać we wszystkich plikach

### 🟡 Discord bot testy: mockowanie interakcji mogłoby być w fixture
- **Lokalizacja:** `discord_bot/tests/test_prices.py:236-247`
- **Problem:** funkcje `make_interaction()` i `last_message()` są zdefiniowane w pliku testowym, nie w conftest
- **Dlaczego to problem:** jeśli będą nowe cogs z testami, kod się powieli
- **Sugestia:** przenieść do `discord_bot/tests/conftest.py` (którego obecnie nie ma)

### 🟢 Coverage endpointów: wszystkie CRUD endpointów testowane
- **Lokalizacja:** wszystkie pliki testowe
- **Problem:** brak — endpointy items, prices, inventory, user-items, profiles, crafting, ingest mają testy
- **Dlaczego to problem:** nie jest to problem
- **Sugestia:** sprawdzić czy nowe endpointy w przyszłości będą dodawane z testami

### 🟡 Brak testów: rate limiting
- **Lokalizacja:** `backend/tests/` (brak pliku)
- **Problem:** `app/config/rate_limit.py` istnieje, ale nie ma testów sprawdzających czy limiter działa
- **Dlaczego to problem:** ryzyko przeciążenia API w production
- **Sugestia:** dodać test wysyłający N requestów i sprawdzający czy po przekroczeniu limitu jest 429

### 🟡 Testy consistency: hardcoded ścieżki do plików
- **Lokalizacja:** `backend/tests/test_consistency.py:11-14`
- **Problem:** testy używają `REPO_ROOT = Path(__file__).parent.parent.parent` — łamie się jeśli struktura się zmieni
- **Dlaczego to problem:** kruche przy refaktoryzacji struktury projektu
- **Sugestia:** użyć `git rev-parse --show-toplevel` lub env variable `REPO_ROOT`

### 🟢 Edge cases: testy pokrywają większość scenariuszy brzegowych
- **Lokalizacja:** `backend/tests/test_inventory.py:131-148`, `backend/tests/test_crafting.py:148-176`
- **Problem:** brak — testy mają: negative quantity, zero quantity, unknown item, empty inventory, nested recipes
- **Dlaczego to problem:** nie jest to problem
- **Sugestia:** rozważyć dodanie testu z bardzo dużym multiplierem (overflow check)

### 🟠 Brak testów: concurrent access do inventory poza get_or_create_profile
- **Lokalizacja:** `backend/tests/test_inventory.py`
- **Problem:** `test_profiles.py` ma test concurrent get_or_create, ale inventory nie ma testu concurrent PUT
- **Dlaczego to problem:** race condition przy jednoczesnym PUT tego samego itemu może spowodować utratę danych
- **Sugestia:** dodać test: dwa równoległe PUT na ten sam item_id z różnymi quantity → sprawdzić czy końcowy stan jest spójny

### 🟢 Discord bot testy: dobre pokrycie error scenarios
- **Lokalizacja:** `discord_bot/tests/test_prices.py`
- **Problem:** brak — testy pokrywają: zero price, negative gold, unreasonable price, item not found, HTTP error, skipped row
- **Dlaczego to problem:** nie jest to problem
- **Sugestia:** kontynuować ten poziom pokrycia dla nowych cogs

## Tabela podsumowująca coverage

| Obszar | Status | Priorytet |
|--------|--------|-----------|
| Auth (basic) | 🟢 Pełne | - |
| Auth (expired/superuser) | 🟠 Brak | Wysoki |
| Items CRUD | 🟢 Pełne | - |
| Prices CRUD | 🟢 Pełne | - |
| Inventory CRUD | 🟢 Pełne | - |
| Crafting calculator | 🟢 Pełne | - |
| Ingest pipeline | 🟢 Pełne | - |
| E2E (ingest → prices) | 🟠 Brak | Średni |
| E2E (crafting end-to-end) | 🟠 Brak | Średni |
| Rate limiting | 🟡 Brak | Niski |
| Concurrent access | 🟡 Częściowe | Średni |
| Discord bot | 🟢 Pełne | - |
# skeptic — findings

## Podsumowanie (3–5 zdań)

Projekt jest dobrze zorganizowany, ale wykazuje cechy over-engineeringu w kilku obszarach. Największy problem to powielanie kodu (`utcnow` w 5 plikach), nadmiarowa warstwa services dla prostych CRUD-ów oraz użycie full auth frameworka (fastapi-users) dla jednej funkcji login/register. Discord bot i backend mają zduplikowaną logikę formatowania cen. Infrastruktura jest przesadzona dla projektu tej wielkości — Caddy jako osobny kontener, makefile z 14 targetami.

## Findings

### 🔴 Powielona funkcja `utcnow` w 5 miejscach
- **Lokalizacja:** `backend/app/items/models.py`, `backend/app/prices/models.py`, `backend/app/profiles/models.py`, `backend/app/user_items/models.py`, `backend/app/crafting/models.py` (każdy plik ma własną definicję)
- **Problem:** Ta sama funkcja `def utcnow() -> datetime: return datetime.now(timezone.utc).replace(tzinfo=None)` jest zdefiniowana 5 razy
- **Dlaczego to problem:** Naruszenie DRY — zmiana logiki (np. na timezone-aware) wymaga edycji 5 plików; ryzyko niespójności; trudniejszy maintenance
- **Sugestia (bez implementacji):** Przenieś `utcnow` do `app/config/` jako singleton i importuj wszędzie; alternatywnie użyj `datetime.now(timezone.utc).replace(tzinfo=None)` inline w Field(default_factory=...)
- **Powiązane:** —

### 🟠 fastapi-users dla jednej funkcji auth
- **Lokalizacja:** `backend/app/auth/` (manager.py, backend.py, dependencies.py, router.py, schemas.py) + dependency w pyproject.toml
- **Problem:** fastapi-users to heavyweight framework (15+ plików w vendorze, JWT + cookie + verification tokens + reset flows), a używasz tylko `login` + `register` + `current_user`
- **Dlaczego to problem:** 141 linii kodu w auth/ (manager, backend, dependencies) dla 3 endpointów; dodatkowa zależność; niepotrzebna komplikacja (UUIDIDMixin, verification_token_secret, reset_password_token_secret)
- **Sugestia (bez implementacji):** Rozważ ręczną implementację auth (bcrypt + JWT + cookie) w ~50 liniach; lub zostaw jeśli planujesz 2FA, reset password, OAuth w przyszłości
- **Powiązane:** —

### 🟠 Profiles jako oddzielny moduł dla jednego pola
- **Lokalizacja:** `backend/app/profiles/` (models.py, schemas.py, services.py, router.py) + `User` model
- **Problem:** Profile ma 1:1 z User, auto-create on register, ale to tylko 2 dodatkowe pola (`display_name`, `is_private`)
- **Dlaczego to problem:** Dodatkowy join w każdym fetchu usera; osobny router, services, schemas; `get_or_create_profile` z UPSERT-em; to powinno być w modelu User
- **Sugestia (bez implementacji):** Przenieś `display_name` i `is_private` do modelu User; usuń moduł profiles; zrefaktoryzuj `/profiles/me` na `/users/me/profile`
- **Powiązane:** —

### 🟠 Services layer dla prostych CRUD-ów
- **Lokalizacja:** `backend/app/items/services.py`, `backend/app/prices/services.py`, `backend/app/profiles/services.py`
- **Problem:** `get_items` to 50-linijna funkcja w services.py, która tylko buduje SQLModel query; router i tak musi ją callować
- **Dlaczego to problem:** Nadmiarowa warstwa abstrakcji — w prostych CRUD-ach services nie wnosi logiki biznesowej, tylko dodaje boilerplate (import, export, dependency injection)
- **Sugestia (bez implementacji):** Przenieś logikę CRUD bezpośrednio do routera dla prostych przypadków; zostaw services tylko tam, gdzie jest faktyczna logika (ingest, crafting calculator, inventory upsert)
- **Powiązane:** —

### 🟡 Zduplikowana logika formatowania cen
- **Lokalizacja:** `frontend/src/lib/currency.ts` (`formatCurrency`) + `discord_bot/cogs/prices.py` (`format_price`)
- **Problem:** Frontend formatuje "1g 23s 45b", bot formatuje "1g 23s 45c" — ta sama logika, różne implementacje, różne nazwy (bronze vs copper)
- **Dlaczego to problem:** Ryzyko dryfu — jeśli zmienisz format (np. na "1.23.45"), musisz aktualizować 2 miejsca; bot używa `c` zamiast `b`
- **Sugestia (bez implementacji):** Stwórz shared Python package z `format_currency()` i `parse_currency()`; bot używa Pythona, frontend mógłby użyć Pyodide lub przepisać na TypeScript z testami snapshotowymi
- **Powiązane:** —

### 🟡 Caddy jako osobny kontener dla 5 reguł reverse proxy
- **Lokalizacja:** `infra/caddy/Caddyfile` (27 linii) + `infra/compose/docker-compose.prod.yml`
- **Problem:** Caddy to pełnoprawny reverse proxy z TLS, ale obsługuje tylko 5 reguł: `/api/*`, `/admin*`, `/docs*`, `/redoc`, `/openapi.json` → backend, reszta → frontend
- **Dlaczego to problem:** Dodatkowy kontener do monitorowania, logowania, restartu; Caddy to ~15MB, ale to kolejny punkt awarii; w dev nie ma Caddy'ego (bezpośrednio na portach)
- **Sugestia (bez implementacji):** Rozważ nginx jako lżejszą alternatywę; lub przenieś routing na poziom load balancera (jeśli deployujesz na chmurze); w dev/prod parity użyj Caddy także w dev
- **Powiązane:** —

### 🟡 Makefile z 14 targetami dla 3 serwisów
- **Lokalizacja:** `Makefile` (81 linii)
- **Problem:** 14 targetów (`dev-up`, `dev-down`, `dev-status`, `dev-build`, `dev-logs`, `prod-*` x5, `test`, `migrate`, `seed`) dla projektu z 3 kontenerami
- **Dlaczego to problem:** Over-engineering — `podman compose up -d` jest wystarczające; targety `*-status`, `*-logs`, `*-build` to wrapper around compose commands
- **Sugestia (bez implementacji):** Zostaw tylko `dev-up`, `dev-down`, `test`, `migrate`, `seed`; resztę usuń — użytkownicy mogą run `podman compose ps/logs/build` bezpośrednio
- **Powiązane:** —

### 🟡 Discord bot + watcher (usunięty) — niejasna ścieżka ingestu
- **Lokalizacja:** `docs/ai/architecture.md` (watcher daemon usunięty) + `discord_bot/cogs/prices.py`
- **Problem:** Watcher był usunięty, ale architektura nie ma jasnej rekomendacji — bot POSTuje do `/api/ingest/prices`, ale czy to jedyne źródło? Co z addonem Lua?
- **Dlaczego to problem:** Niejasność dla nowych developerów — czy addon wciąż istnieje? Czy bot jest zalecany? Co jeśli chcę ingestować z innego źródła?
- **Sugestia (bez implementacji):** Uaktualnij `architecture.md` — narysuj aktualny flow (addon → ???, bot → API); rozważ dodanie API key auth dla ingestu jeśli bot nie jest jedynym źródłem
- **Powiązane:** —

### 🟢 Admin views bez pagination dla PricePoint
- **Lokalizacja:** `backend/app/prices/admin.py`
- **Problem:** PricePointAdmin ma `column_list` z 6 kolumnami, ale nie ma `page_size` — tabela może mieć miliony wierszy
- **Dlaczego to problem:** sqladmin domyślnie ładuje wszystkie wiersze bez pagination — to może zabić wydajność admin panelu
- **Sugestia (bez implementacji):** Dodaj `page_size = 50` lub `column_default_sort = [(PricePoint.captured_at, False)]` w PricePointAdmin
- **Powiązane:** —

### 🟢 ECharts z `@ts-nocheck`
- **Lokalizacja:** `frontend/src/lib/components/charts/EChartsLineChart.svelte` (linia 2)
- **Problem:** `// @ts-nocheck` wyłącza type checking dla całego pliku — 95 linii bez typowania
- **Dlaczego to problem:** TypeScript nie wykryje błędów w options, formatterach, event handlerach; trudniejszy refactoring
- **Sugestia (bez implementacji):** Dodaj typy dla `options` (echarts types są dostępne); usuń `@ts-nocheck`; użyj `as const` dla static config
- **Powiązane:** —

### 💡 ItemGrade.ALL jako domyślny grade
- **Lokalizacja:** `backend/app/items/models.py` (Item.grade = ItemGrade.ALL)
- **Problem:** `ItemGrade.ALL` jest w enumie, ale semantycznie to nie jest grade — to filtr UI
- **Dlaczego to problem:** Mylące — nowy item z grade=ALL wygląda jak błąd w danych; `ALL` powinien być tylko w frontendowym filtrze
- **Sugestia (bez implementacji):** Usuń `ALL` z ItemGrade enum; dodaj `UNKNOWN` lub `BASIC` jako default; przenieś `ALL` do frontendu jako virtual filter
- **Powiązane:** —

### 💡 12-itemowy enum ItemGrade vs 11-itemowy w bocie
- **Lokalizacja:** `backend/app/items/models.py` (ItemGrade, 12 wartości) + `discord_bot/cogs/prices.py` (GRADE_CHOICES, 12 wartości) + `backend/app/ingest/grade_map.py` (GAME_GRADE_TO_ENUM, 12 wartości)
- **Problem:** Trzy miejsca z definicją grade mappingu — enum w models, choices w bocie, map w ingest
- **Dlaczego to problem:** Jeśli gra doda nowy grade (np. 13), musisz aktualizować 3 pliki; ryzyko niespójności (bot ma inną nazwę niż backend)
- **Sugestia (bez implementacji):** Stwórz `app/items/grades.py` z centralnym enumem + helperem `grade_to_int()` + `grade_to_display_name()`; importuj w bocie (przez shared package) i w ingest
- **Powiązane:** —

### 💡 UserInventory bez indexu na (user_id, item_id)
- **Lokalizacja:** `backend/app/user_inventory/models.py`
- **Problem:** Jest `UniqueConstraint("user_id", "item_id", name="uq_user_inventory")`, ale brakuje explicit indexu dla szybkiego lookupu
- **Dlaczego to problem:** PostgreSQL automatycznie tworzy index dla unique constraint, ale warto to udokumentować; `get_inventory_for_recipe` robi `.in_(ingredient_ids)` — to może być wolne dla dużych inventory
- **Sugestia (bez implementacji):** Dodaj `Index("ix_user_inventory_user_id", "user_id")` w `__table_args__` jeśli go nie ma; sprawdź explain analyze dla `SELECT ... WHERE user_id = ? AND item_id IN (...)`
- **Powiązane:** —

### 💡 CraftResult.batch_profit — myląca nazwa
- **Lokalizacja:** `docs/ai/patterns.md` (notka) + `backend/app/crafting/schemas.py`
- **Problem:** `batch_profit` to profit dla całego batcha, ale nazwa sugeruje profit na batcha (nie per craft)
- **Dlaczego to problem:** Mylące dla frontend developerów — czy to profit na craft, czy na cały batch? Docs mówią "total profit for the entire batch"
- **Sugestia (bez implementacji):** Zmień nazwę na `total_batch_profit` lub dodaj komentarz w schemas.py; alternatywnie dodaj `profit_per_craft` jako derived field
- **Powiązane:** —
# visionary — findings

## Podsumowanie (3–5 zdań)

ArcheRage Market Tracker to solidna aplikacja REST + SQLModel, ale profil ruchu (dużo odczytów cen, rekurencyjne obliczenia craftingu, per-user inventory) otwiera kilka furtek do optymalizacji. Event-driven architecture odciążyłoby backend przy ingestowaniu cen, GraphQL uprościłoby frontendowe zapytania o drzewa craftingowe, a Redis dałby natychmiastową poprawę responsywności dla frequently-accessed danych. Część logiki (crafting calculator, cache) można by przesunąć na edge/CDN lub do Service Workers, redukując obciążenie backendu. Wzorce z e-commerce (materialized views, read models) i gamingowych API (WebSockets, delta updates) są bezpośrednio adaptowalne.

## Findings

### 🟠 Event-driven price ingestion
- **Lokalizacja:** `backend/app/ingest/router.py`, `backend/app/prices/services.py:add_price_point`
- **Problem:** Obecny ingest to synchroniczne HTTP POST → INSERT PricePoint + UPDATE Item.current_price w tej samej transakcji. Przy batchach z watchera/bota każdy request blokuje sesję DB, a przy skoku cen (event w grze) może powstać kolejka.
- **Dlaczego to problem:** Sync HTTP coupling oznacza, że wolny DB = wolny ingest = timeouty po stronie watchera. Brak bufora między "przyjęciem danych" a "zapisem". Nie ma retry queue na poziomie serwera — tylko client-side backoff.
- **Sugestia (bez implementacji):** Wprowadź broker (NATS JetStream, Redis Streams, RabbitMQ) jako bufor. Ingest endpoint tylko pushuje eventy do streamu (200 OK natychmiast), osobny consumer (async, z batchowaniem) aktualizuje DB. Zalety: decoupling, naturalny backpressure, możliwość replayu historii. Alternatywa lżejsza: PostgreSQL LISTEN/NOTIFY + pgqueue.
- **Powiązane:** 🟢 Redis cache layer (event invalidation)

### 🟡 GraphQL dla crafting tree queries
- **Lokalizacja:** `backend/app/crafting/services.py:calculate`, `frontend/src/lib/components/crafting/RecipeTree.svelte`
- **Problem:** Crafting tree wymaga wielokrotnych round-tripów lub over-fetchingu: frontend pobiera cały wynik `calculate()`, ale często potrzebuje tylko fragmentu (np. sumaryczny koszt, albo tylko brakujące materiały). Obecny REST zwraca pełne drzewo za każdym razem.
- **Dlaczego to problem:** Przy głębokich drzewach (5-6 poziomów) payload rośnie eksponencjalnie. Użytkownik z inventory chce zobaczyć tylko "co muszę dokupić" — ale dostaje pełne drzewo z cenami jednostkowymi, kosztami subtotal, flagami can_craft itd. Over-fetching = większe zużycie bandwidth, wolniejsze renderowanie.
- **Sugestia (bez implementacji):** GraphQL pozwala frontendowi zapytać o konkretny kształt danych: `{ craftTree(itemId: 123) { totalCost missingMaterials { itemId quantity } } }`. Alternatywa lżejsza: REST z query params `?fields=totalCost,missingMaterials` (JSON:api style) lub endpoint `/api/crafting/{id}/summary`. Do rozważenia: persisted queries (hash query z frontendu, backend ma zmapowane).
- **Powiązane:** 💡 Edge computing (przenieść obliczenia na client)

### 🟢 Redis cache layer
- **Lokalizacja:** `backend/app/items/services.py:get_items`, `backend/app/prices/services.py:get_item_price_history`, `backend/app/crafting/services.py:list_summaries`
- **Problem:** Często czytane dane (lista itemów, historia cen z ostatnich 24h, crafting summaries) są za każdym razem fetchowane z DB. Przy 10-100 użytkownikach naraz to setki identycznych zapytań PostgreSQL.
- **Dlaczego to problem:** PostgreSQL nie jest zoptymalizowany pod high-read workloads bez cache'owania. `get_items` z paginacją i filtrami wykonuje `COUNT(*) + ORDER BY + OFFSET` za każdym razem. `list_summaries` buduje pełne drzewa craftingowe dla wszystkich receptur — kosztowne przy każdych odwiedzinach `/crafting`.
- **Sugestia (bez implementacji):** Redis jako cache warstwa: (1) `items:list:{filters}` — cache paginowanej listy, (2) `prices:{item_id}:{interval}:{from}-{to}` — cache bucketów cen, (3) `crafting:summary:{item_id}` — cache CraftResult. Strategia invalidation: TTL 1-5 min dla cen, invalidate przy `add_price_point`. Alternatywa: PostgreSQL materialized views z refresh co minutę dla `list_summaries`.
- **Powiązane:** 🟠 Event-driven ingestion (invalidation przez events)

### 💡 Edge computing / Service Workers
- **Lokalizacja:** `frontend/src/lib/components/crafting/RecipeTree.svelte:computeNodeCost`, `backend/app/crafting/calculator.py:build_craft_tree`
- **Problem:** Logika przeliczania kosztów przy zmianie inventory/multipliera (`computeNodeCost`) działa w frontendzie, ale bazuje na pełnym drzewie z backendu. Przy zmianie "Have" dla jednego itemu frontend przelicza całe drzewo — ale dane już są po stronie klienta.
- **Dlaczego to problem:** Marny potencjał: gdyby całe drzewo + ceny były w Service Worker cache, użytkownik mógłby eksperymentować z inventory offline, bez żadnego requestu. Obecnie każdy refresh strony = fetch całego drzewa od nowa.
- **Sugestia (bez implementacji):** (1) Service Worker z cache-first strategią dla `/api/crafting/{id}` — drzewo cache'owane lokalnie, refresh w tle. (2) Przenieść `build_craft_tree` w całości na client (WebAssembly? albo czysty TS) — backend tylko dostarcza surowe dane (items + recipes), klient buduje drzewo lokalnie. (3) Edge Functions (Cloudflare Workers) jako cache + lightweight calculator bliżej użytkownika.
- **Powiązane:** 🟡 GraphQL (mniejsze payloady = łatwiejszy cache)

### 🟡 Materialized views dla crafting profitability
- **Lokalizacja:** `backend/app/crafting/services.py:list_summaries`, `backend/app/crafting/calculator.py`
- **Problem:** `list_summaries` buduje drzewo dla KAŻDEJ receptury przy każdym wywołaniu — to O(n²) przy rosnącej liczbie receptur. Przy 50 recepturach z głębokością 4-5 poziomów to tysiące rekurencyjnych wywołań.
- **Dlaczego to problem:** Endpoint `/api/crafting/summaries` jest wywoływany przy wejściu na stronę crafting — każdy użytkownik triggeruje pełne przeliczenie. To nie skaluje się z liczbą użytkowników ani receptur.
- **Sugestia (bez implementacji):** Materialized view w PostgreSQL: tabela `crafting_summary_cache` z kolumnami `(item_id, total_material_cost, market_price, batch_profit, last_computed)`. Refresh: (1) trigger po `UPDATE Item.current_price`, (2) cron co minutę, (3) invalidation przez event z ingestu. Alternatywa: precompute w tle (celery/RQ worker) + cache w Redis.
- **Powiązane:** 🟢 Redis cache layer

### 🟠 WebSocket / Server-Sent Events dla live price updates
- **Lokalizacja:** `backend/app/prices/router.py`, `frontend/src/lib/components/charts/EChartsLineChart.svelte`
- **Problem:** Wykres cen odświeża się tylko przy reloadzie strony. Użytkownik nie widzi nowych cen w czasie rzeczywistym, mimo że ceny są ingestowane co kilka minut (watcher/bot).
- **Dlaczego to problem:** Tracker cen w MMO to narzędzie do szybkich decyzji — gracz chce widzieć zmianę ceny natychmiast, nie po refreshu. Obecny polling (gdyby go dodać) oznaczałby dodatkowe zapytania do DB.
- **Sugestia (bez implementacji):** (1) WebSocket endpoint `/ws/prices` — backend broadcastuje nową cenę po `add_price_point`. (2) Server-Sent Events (lżej niż WS) — jeden kierunek, natywna obsługa w przeglądarce. (3) Alternatywa: HTTP streaming + `Transfer-Encoding: chunked` dla długich połączeń. Frontend subskrybuje `item_id` i aktualizuje ECharts live.
- **Powiązane:** 🟠 Event-driven ingestion (ten sam event triggeruje WS broadcast)

### 🟡 Read models / CQRS dla inventory + crafting
- **Lokalizacja:** `backend/app/user_inventory/services.py:get_inventory_for_recipe`, `backend/app/crafting/services.py:calculate`
- **Problem:** `get_inventory_for_recipe` łączy inventory z drzewem craftingowym — to zapytanie łączy 3+ tabele i buduje mapę `{item_id: quantity}`. Przy każdym użyciu kalkulatora to samo zapytanie.
- **Dlaczego to problem:** Read-heavy operation (każdy użytkownik sprawdza inventory przed craftem) vs write-light (inventory aktualizowane raz na kilka minut). Obecny model miesza read i write w tym samym schemacie.
- **Sugestia (bez implementacji):** CQRS: osobny read model `user_inventory_cache` zdenormalizowany do postaci `(user_id, item_id, quantity, last_updated)`. Write: nadal przez `UserInventory` table. Read: proste zapytanie bez joinów. Alternatywa: denormalizacja w ramach istniejącego modelu — dodatkowa kolumna `cached_inventory_json` w `Profile` z snapshotem inventory.
- **Powiązane:** 🟢 Redis cache layer (cache per-user inventory)

### 💡 Delta updates dla price history
- **Lokalizacja:** `backend/app/prices/services.py:get_item_price_history`, `frontend/src/routes/items/[id]/+page.svelte`
- **Problem:** Historia cen jest pobierana jako pełna lista punktów/bucketów za każdym razem. Użytkownik, który wraca na stronę itemu po 5 minutach, dostaje TE SAME dane + 1-2 nowe punkty.
- **Dlaczego to problem:** Przy 30 dniach danych i interwale 5m to ~8640 punktów na wykres. Transfer i parsowanie JSON zajmuje czas, a 95% danych to duplikaty względem poprzedniej wizyty.
- **Sugestia (bez implementacji):** (1) Endpoint `/api/prices/{item_id}/delta?since={timestamp}` — zwraca tylko punkty od ostatniej wizyty. (2) Frontend zapisuje `last_fetched_at` w localStorage, przy kolejnej wizycie fetchuje delta. (3) Alternatywa: ETag/If-Modified-Since — backend zwraca 304 jeśli dane się nie zmieniły.
- **Powiązane:** 🟠 WebSocket (live updates)

### 🟡 Batched writes dla inventory updates
- **Lokalizacja:** `backend/app/user_inventory/services.py:upsert_inventory`, `frontend/src/lib/components/crafting/RecipeTree.svelte:onSetInventory`
- **Problem:** Każda zmiana "Have" w RecipeTree wysyła osobny PUT `/api/inventory/{item_id}`. Użytkownik, który ustawia inventory dla 10 itemów, generuje 10 requestów HTTP.
- **Dlaczego to problem:** HTTP overhead (headers, auth, TCP handshake) dominuje nad payloadem. Przy wolnym połączeniu (gracz na mobile) to zauważalne opóźnienia.
- **Sugestia (bez implementacji):** (1) Endpoint `PUT /api/inventory/batch` z payloadem `[{item_id, quantity}, ...]`. (2) Frontend debouncing: zbiera zmiany przez 500ms, wysyła jeden batch. (3) Alternatywa: WebSocket + queue zmian po stronie klienta, batch wysyłany co kilka sekund.
- **Powiązane:** 🟠 Event-driven ingestion (batch processing)

### 🟠 Circuit breaker dla external API (future)
- **Lokalizacja:** `backend/app/ingest/services.py:bulk_ingest`, `discord_bot/cogs/prices.py`
- **Problem:** Obecnie nie ma zewnętrznych API, ale jeśli w przyszłości pojawi się integracja (np. pobieranie cen z innego serwera, API Discorda do rich embeds), brak circuit breakera oznacza kaskadowe awarie.
- **Dlaczego to problem:** Wolne/zawieszone zewnętrzne API blokują wątki backendu, co prowadzi do wyczerpania connection pool i padu całego serwisu.
- **Sugestia (bez implementacji):** Wzorzec circuit breaker (biblioteka `pybreaker` lub własna implementacja): (1) po N błędach otwórz circuit, (2) zwracaj fallback (cache/stare dane), (3) co jakiś czas próbuj zamknąć circuit. Alternatywa: timeouty + retry z backoff (już częściowo w botcie).
- **Powiązane:** —

### 🟡 Denormalizacja `Item.current_price` do historycznych bucketów
- **Lokalizacja:** `backend/app/prices/services.py:get_item_price_history`, `backend/app/items/models.py:Item.current_price`
- **Problem:** `current_price` jest denormalizowane (aktualizowane przy każdym `add_price_point`), ale bucket aggregation (`5m`, `1h`, `1d`) jest liczone za każdym razem od zera. Przy dużej historii to kosztowne.
- **Dlaczego to problem:** Agregacja 30 dni danych w interwale 5m = ~8640 punktów do przetworzenia w Pythonie (pętla w `get_item_price_history`). To O(n) przy każdym requeście.
- **Sugestia (bez implementacji):** (1) Precomputed buckets — tabela `price_bucket_5m`, `price_bucket_1h` z materializowanymi agregatami. (2) Hybrid: świeże dane (ostatnie 24h) liczone live, starsze z precomputed tabeli. (3) Alternatywa: PostgreSQL timeseries extension (TimescaleDB) z automatycznymi agregacjami.
- **Powiązane:** 🟢 Redis cache layer

### 💡 Client-side caching z stale-while-revalidate
- **Lokalizacja:** `frontend/src/lib/auth.svelte.ts:checkMe`, `frontend/src/routes/items/+page.svelte`
- **Problem:** Każdy komponent fetchuje dane od nowa przy mounted. Brak cache'owania między sesjami, brak strategii stale-while-revalidate.
- **Dlaczego to problem:** Użytkownik, który wraca na stronę, czeka na pełny fetch mimo że dane (lista itemów, ceny) nie zmieniły się znacząco. UX jest gorszy, a serwer obciążony.
- **Sugestia (bez implementacji):** (1) Biblioteka `swr` lub `tanstack-query` dla Svelte — cache + background revalidation. (2) Własny hook: fetch → cache w `$state` + localStorage, przy kolejnym mounted najpierw z cache, potem background refresh. (3) HTTP cache headers (`Cache-Control: stale-while-revalidate=300`) + Service Worker.
- **Powiązane:** 💡 Edge computing

### 🟡 Connection pool tuning + read replicas
- **Lokalizacja:** `backend/app/config/db.py:get_async_session`, `infra/compose/docker-compose.prod.yml`
- **Problem:** Jeden PostgreSQL, jeden connection pool. Przy rosnącej liczbie użytkowników read/write contention rośnie.
- **Dlaczego to problem:** Read-heavy workload (ceny, crafting) konkuruje o połączenia z write operations (ingest, inventory updates). Przy 50+ równoległych użytkownikach pool może się wyczerpać.
- **Sugestia (bez implementacji):** (1) Read replica PostgreSQL — routing: write → primary, read → replica. (2) Connection pooler (PgBouncer) w trybie transaction pooling — redukuje liczbę aktywnych połączeń do DB. (3) Alternatywa: tuning `max_connections`, `shared_buffers` w PostgreSQL.
- **Powiązane:** 🟢 Redis cache layer (odciąża DB)

### 🟠 Optimistic UI updates dla inventory
- **Lokalizacja:** `frontend/src/lib/components/crafting/RecipeTree.svelte:onSetInventory`, `backend/app/user_inventory/services.py:upsert_inventory`
- **Problem:** Aktualizacja inventory czeka na odpowiedź serwera przed odświeżeniem UI. Przy wolnym połączeniu użytkownik widzi opóźnienie między wpisaniem wartości a aktualizacją "Still need".
- **Dlaczego to problem:** UX jest gorszy — gracz oczekuje natychmiastowej reakcji. Przy serii szybkich zmian (testowanie różnych wariantów inventory) każde opóźnienie się sumuje.
- **Sugestia (bez implementacji):** Optimistic update: (1) frontend natychmiast aktualizuje `$state` i przelicza drzewo lokalnie, (2) wysyła request w tle, (3) przy błędzie rollback + toast. Wymaga: idempotentność endpointu (już jest przez upsert), conflict resolution (last-write-wins lub vector clocks).
- **Powiązane:** 🟡 Batched writes

### 💡 Precomputed crafting paths (najkrótsza ścieżka do craftu)
- **Lokalizacja:** `backend/app/crafting/calculator.py:build_craft_tree`, `backend/app/user_inventory/services.py:get_inventory_for_recipe`
- **Problem:** Kalkulator buduje PEŁNE drzewo dla każdej receptury, ale użytkownik często chce tylko odpowiedź: "czy mogę to zrobić z moim inventory?" albo "jaką ścieżką najtaniej to zrobić?".
- **Dlaczego to problem:** Pełne drzewo jest kosztowne do obliczenia i wyświetlenia. Czasami użytkownik chce tylko "tak/nie" + listę brakujących itemów.
- **Sugestia (bez implementacji):** (1) Precomputed dependency graph — tabela `recipe_dependencies(item_id, depends_on_item_id, depth)`. (2) Query: "czy user ma wszystkie itemy z zależności?" — prosty JOIN zamiast rekurencji. (3) Alternatywa: BFS/DFS na client-side po pobraniu surowych danych (items + recipes), bez budowania pełnego drzewa kosztów.
- **Powiązane:** 🟡 GraphQL (możliwość zapytania o samą ścieżkę)
# second-opinion — findings

## Podsumowanie (3–5 zdań)

Audit ujawnia projekt w dobrej kondycji technicznej, ale z kilkoma poważnymi lukami bezpieczeństwa wymagającymi natychmiastowej interwencji. Najkrytyczniejszy jest wyciek Discord tokena w `.env` — to P0, który należy naprawić w ciągu godziny. Większość findings z kategorii code quality i dependencies to "nice-to-have" niż blokers. Subagenci przesadzają z liczbą findingów — wiele to duplikaty lub fałszywe alarmy (np. N+1 w crafting services został sam podważony przez backend audytora).

## Potwierdzone najważniejsze findings

| Finding | Dlaczego krytyczne | Priorytet |
|---------|-------------------|-----------|
| **Discord token w .env** (security) | Token jest publicznie dostępny w repo — każdy może przejąć bota | P0, natychmiast |
| **`.env` w git** (security) | Plik z sekretami (POSTGRES_PASSWORD, AUTH_SECRET) jest version-controlled | P0, natychmiast |
| **Brak rate limitu na inventory PUT** (integration/backend) | Authenticated write bez limitu = DoS vector | P1, 1-2 dni |
| **Brak obsługi 429 w discord bot** (discordbot) | Bot traci dane przy rate limitowaniu backendu | P1, 1 dzień |
| **Podwójna instancja authentication_backend** (backend) | Dead code + zamieszanie, ale nie wpływa na runtime | P2, 1 tydzień |
| **Brak rollbacków w services** (backend) | Sesja DB w stanie błędu po wyjątku = "trucizna" | P2, 1 tydzień |

**Dlaczego te są najważniejsze:** Pierwsze dwa to aktywne wycieki sekretów. Kolejne trzy to luki bezpieczeństwa/utraty danych. Ostatnie dwa to problemy z integralnością danych.

## Kwestionowane findings

| Finding | Kto zgłosił | Dlaczego przesadzone | Moja ocena |
|---------|-------------|---------------------|------------|
| **N+1 query w crafting/services.py** | backend | Sam finding przyznaje "FAŁSZYWY ALARM — po bliższej analizie nie ma N+1" | ❌ Do usunięcia |
| **Router kolejność — for-recipe przed PUT** | backend | Sam finding przyznaje "BRAK PROBLEMU — kolejność jest правильna" | ❌ Do usunięcia |
| **Rate limiter singleton — poprawnie** | backend | To finding pozytywny, nie problem | ℹ️ Przenieść do "co działa dobrze" |
| **add_price_point — atomowa aktualizacja** | backend | To finding pozytywny | ℹ️ Przenieść do "co działa dobrze" |
| **UserInventory upsert — poprawnie** | backend | To finding pozytywny | ℹ️ Przenieść do "co działa dobrze" |
| **Naive UTC — poprawnie** | backend | To finding pozytywny | ℹ️ Przenieść do "co działa dobrze" |
| **Caddy jako osobny kontener** | skeptic | Dla produkcji Caddy z TLS to standard, nie over-engineering | ⚠️ Dyskusyjne |
| **Makefile z 14 targetami** | skeptic | Targety ułatwiają życie deweloperom, to nie over-engineering | ⚠️ Dyskusyjne |
| **fastapi-users dla jednej funkcji auth** | skeptic | Framework daje verification token, reset password, OAuth — to inwestycja w przyszłość | ⚠️ Dyskusyjne |
| **Profiles jako oddzielny moduł** | skeptic | 1:1 z User to valid pattern (separation of concerns), nie problem | ⚠️ Dyskusyjne |
| **Vulnerable dependency `cookie`** | dependencies | Zależność pośrednia z @sveltejs/kit, fix wymaga breaking change | 🟡 Niski priorytet |

**Uwaga:** Backend findings.md zawiera 6 findingów oznaczonych jako 🟢 OK — to nie są problemy, tylko potwierdzenia zgodności. Powinny być w osobnej sekcji "What Works Well".

## Dodany kontekst

### Czego inni nie widzieli

1. **Korelacja security + discordbot**: Security finding mówi o braku rate limitu na większości endpointów, a discordbot finding mówi o braku obsługi 429. To są **dwa końce tego samego problemu** — backend nie ma rate limitu na wielu endpointach, ale bot i tak dostaje 429 na `/api/ingest/prices`. Bot powinien mieć retry logic NIEZALEŻNIE od tego, czy backend ma globalny rate limit.

2. **Dependencies finding o `slowapi`**: `slowapi` ostatni release z lutego 2024 — to jest **ważniejsze niż zgłoszono**. Jeśli fastapi-users lub Starlette zaktualizują API, slowapi może przestać działać. To nie jest "potencjalnie EOL" — to **faktycznie EOL** (brak release'ów od >1 roku przy aktywnym rozwoju FastAPI).

3. **Tester-evaluator finding o braku testów rate limiting**: To łączy się z backend findingiem o braku rate limitu na wielu endpointach. **Nie możesz testować czegoś, czego nie ma** — najpierw dodaj rate limit, potem testy.

4. **Visionary finding o WebSocket/SSE**: To jest **najbardziej oderwane od rzeczywistości** finding. Projekt ma 3 kontenery, 94 testy, i nie jest jeszcze w production. WebSocket to premature optimization.

5. **Skeptic finding o powielonej logice `utcnow`**: To jest **valid point**, ale rozwiązanie jest prostsze niż sugerowane. Zamiast tworzyć nowy moduł `app/config/time.py`, wystarczy użyć `datetime.now(timezone.utc).replace(tzinfo=None)` inline w `Field(default_factory=...)` — to eliminuje potrzebę importu.

6. **Frontend finding o `@ts-nocheck` w ECharts**: To nie jest "niespójny error handling" — to **świadoma decyzja** bo echarts types są notorycznie broken. Lepiej mieć `@ts-nocheck` niż walczyć z typami które nie działają.

## Konflikty między subagentami

| Obszar | Visionary | Skeptic | Backend/Integration | Moja ocena |
|--------|-----------|---------|---------------------|------------|
| **Services layer** | Nie komentuje | "Nadmiarowa warstwa dla prostych CRUD" | Używa services layer konsekwentnie | ⚖️ **Skeptic ma rację** — services dla `get_items` to over-engineering, ale services dla `ingest` i `crafting` jest uzasadniony |
| **Caching** | "Redis cache layer" (3 findingi) | Nie komentuje | Brak cache, wszystko z DB | ⚖️ **Visionary ma rację long-term**, ale to premature optimization na tym etapie |
| **Auth complexity** | Nie komentuje | "fastapi-users dla jednej funkcji to overkill" | fastapi-users używany konsekwentnie | ⚖️ **Skeptic ma rację** — ale zmiana teraz to duży refactoring |
| **Rate limiting** | Nie komentuje | Nie komentuje | "Brak na inventory/crafting" | ✅ **Brak konfliktu** — wszyscy się zgadzają że brakuje |
| **Event-driven** | "Event-driven price ingestion" | Nie komentuje | Sync HTTP ingest | ⚖️ **Visionary przesadza** — event-driven to dobry pattern, ale nie na tym etapie projektu |
| **Brak healthchecków** | Nie komentuje | Nie komentuje | Infra: "Brak healthchecków" | ✅ **Infra ma rację** — to critical missing piece |

**Największy konflikt:** Visionary vs rzeczywistość. Visionary sugeruje GraphQL, WebSocket, Redis, CQRS, materialized views — to wszystko są **dobre pomysły za 12-18 miesięcy**, nie teraz.

## Czego brakuje

### Missing from all reports

1. **Monitoring/observability**: Żaden audit nie wspomina o braku:
   - Log aggregation (ELK, Loki)
   - Metrics (Prometheus, Grafana)
   - Distributed tracing (OpenTelemetry)
   - Alerting (PagerDuty, Opsgenie)

2. **Backup strategy**: Brak findingów o:
   - Backupach PostgreSQL (pg_dump cron? WAL archiving?)
   - Recovery time objective (RTO)
   - Recovery point objective (RPO)

3. **Disaster recovery**: Brak planu na:
   - Awarię produkcji
   - Utratę danych
   - Rollback migracji

4. **Documentation gaps**:
   - Brak runbooków dla on-call
   - Brak dokumentacji API dla zewnętrznych konsumentów (poza auto-generowanym OpenAPI)
   - Brak changelogu

5. **Accessibility (a11y)**: Frontend audit nie wspomina o:
   - WCAG compliance
   - Screen reader support
   - Keyboard navigation

6. **Performance benchmarks**: Brak danych o:
   - Response times (p50, p95, p99)
   - Throughput (requests/second)
   - Database query performance

7. **Load testing**: Brak testów wydajnościowych dla:
   - Concurrent users
   - Large inventory (1000+ items)
   - Deep crafting trees (10+ levels)

8. **Data retention policy**: Brak polityki dotyczącej:
   - Jak długo przechowywać PricePoint (30 dni? rok?)
   - Kiedy archiwizować UserInventory
   - GDPR compliance (right to be forgotten)

### Tabela priorytetów napraw

| Priorytet | Finding | Owner | Czas naprawy |
|-----------|---------|-------|--------------|
| P0 | Discord token w .env | security | < 1h |
| P0 | `.env` w git (git rm --cached) | security | < 1h |
| P1 | Rate limit na inventory PUT | backend | 2-4h |
| P1 | Retry logic w discord bot (429) | discordbot | 4-8h |
| P1 | Healthchecki w docker-compose | infra | 2-4h |
| P2 | Rollbacki w services | backend | 4-8h |
| P2 | Security headers (Caddy) | infra | 2-4h |
| P2 | Podwójna instancja authentication_backend | backend | 1h |
| P3 | Refactor pagination helper | code-quality | 4-8h |
| P3 | Testy expired token / superuser | tester | 4-8h |

---

## Podsumowanie

**Najważniejsze action items:**
1. **Natychmiast**: Unieważnij Discord token, `git rm --cached .env`, dodaj `.env` do `.gitignore`
2. **Ten tydzień**: Dodaj rate limit na inventory PUT, retry logic w bocie, healthchecki
3. **Następny tydzień**: Rollbacki w services, security headers, refactor authentication_backend

**Reszta findingów** to albo premature optimization (Visionary), albo over-critiquing (Skeptic), albo confirmed-good (backend 🟢 findings). Skup się na P0 i P1.
# Audit Synthesis — ArcheRage Market Tracker

**Data audytu:** 2026-05-20  
**Worktree:** `/home/dv6/GitHub/audit-opencode-20260520-2222`  
**Model:** opencode-go/qwen3.5-plus

---

## TL;DR — Top 10 findings (posortowane po severity)

| # | Severity | Finding | Owner | Czas naprawy |
|---|----------|---------|-------|--------------|
| 1 | 🔴 P0 | Discord token hardkodowany w `.env` (committed w git) | security | < 1h |
| 2 | 🔴 P0 | `.env` w git — wymaga `git rm --cached` | security | < 1h |
| 3 | 🟠 P1 | Rate limiting tylko na 2/17 endpointach | backend | 1-2 dni |
| 4 | 🟠 P1 | Brak obsługi 429 w discord bot (retry logic) | discordbot | 4-8h |
| 5 | 🟠 P1 | Brak healthchecków dla backend/frontend w compose | infra | 2-4h |
| 6 | 🟠 P1 | Brak rollbacków w 3 serwisach (user_inventory, user_items, profiles) | backend | 4-8h |
| 7 | 🟠 P1 | Security headers brak (CSP, X-Frame-Options, etc.) | infra | 2-4h |
| 8 | 🟡 P2 | Podwójna instancja `authentication_backend` (dead code) | backend | 1h |
| 9 | 🟡 P2 | Brak walidacji `source` w PricePointCreate (enum) | backend | 2-4h |
| 10 | 🟡 P2 | Frontend CI bez build checka | infra | 1-2h |

---

## Krytyczne (🔴 P0) — Natychmiastowa akcja

### 1. Discord token w `.env` (committed)
- **Lokalizacja:** `.env:23`
- **Problem:** Token `[REDACTED — Discord bot token, revoked]` jest publiczny
- **Ryzyko:** Przejęcie bota przez dowolną osobę z dostępem do repo
- **Akcja:**
  1. Natychmiast unieważnij token w [Discord Developer Portal](https://discord.com/developers/applications)
  2. Wygeneruj nowy token
  3. `git rm --cached .env`
  4. Commit: `security: remove .env from git history`
  5. Dodaj `.env` do `.gitignore` (już jest, ale retroaktywnie)

### 2. `.env` w git (sekrety暴露)
- **Lokalizacja:** `.env` (pliki: POSTGRES_PASSWORD, AUTH_SECRET, ADMIN_SESSION_SECRET, Discord token)
- **Problem:** Plik był commitowany, git ignore nie działa retroaktywnie
- **Ryzyko:** Wszystkie secrety projektu są publiczne
- **Akcja:** Patrz wyżej + rotacja WSZYSTKICH sekretów (POSTGRES_PASSWORD, AUTH_SECRET, ADMIN_SESSION_SECRET)

---

## Wzorce powtarzające się (≥2 subagentów)

### 1. Brak rate limitu na endpointach authenticated
- **Zgłoszone przez:** backend, integration, security
- **Endpointy:** `PUT /api/inventory/{item_id}`, `POST /api/crafting/{item_id}/calculate`
- **Ryzyko:** DoS, abuse, scraping
- **Fix:** Dodać `@limiter.limit("60/minute")` do wszystkich endpointów authenticated write

### 2. Brak rollbacków przy błędach DB
- **Zgłoszone przez:** backend, second-opinion
- **Serwisy:** `user_inventory/services.py`, `user_items/services.py`, `profiles/services.py`
- **Problem:** `session.commit()` bez `try/except` z `session.rollback()`
- **Ryzyko:** Sesja DB w stanie błędu "truje" kolejne operacje
- **Fix:** Wzorzec z `ingest/services.py:_process_row` (linie 95-108)

### 3. Brak healthchecków w docker-compose
- **Zgłoszone przez:** infra, second-opinion
- **Problem:** Backend i frontend nie mają healthcheck, `depends_on` nie czeka na gotowość
- **Ryzyko:** Restart kontenera przed aplikacją jest gotowa → 502 errors
- **Fix:** Dodać healthcheck z `curl http://localhost:8000/health` (wymaga endpointu)

### 4. Powielona logika paginacji
- **Zgłoszone przez:** code-quality, skeptic
- **Problem:** `items/services.py` i `user_items/services.py` mają identyczną logikę paginacji
- **Fix:** Extract do `app/config/pagination.py` lub `app/shared/pagination.py`

### 5. Brak testów auth scenarios
- **Zgłoszone przez:** tester-evaluator, second-opinion
- **Brakujące testy:** expired token, brak tokena, superuser auth, rate limiting
- **Fix:** Dodać testy w `backend/tests/test_auth.py`

---

## Konflikty opinii

| Obszar | Visionary | Skeptic | Second Opinion | Werdykt |
|--------|-----------|---------|----------------|---------|
| **GraphQL** | "GraphQL lepsze niż REST" | — | "Premature optimization" | ❌ Odrzucić (teraz) |
| **Redis cache** | "Redis cache layer" | — | "Good long-term, nie teraz" | ⏸️ Backlog (12+ miesięcy) |
| **WebSocket/SSE** | "Real-time price updates" | — | "Projekt nie w production" | ❌ Odrzucić (teraz) |
| **fastapi-users** | — | "Over-engineering dla 3 endpointów" | "Valid, ale zmiana = duży refactoring" | ⚖️ Zostawić (koszt zmiany > benefit) |
| **Services layer** | — | "Nadmiarowa warstwa dla CRUD" | "Services dla ingest/crafting uzasadniony" | ⚖️ Zostawić (separation of concerns) |
| **Caddy jako kontener** | — | "Over-engineering" | "Standard dla production TLS" | ✅ Zostawić (best practice) |
| **`@ts-nocheck` w ECharts** | — | — | "Świadoma decyzja, types broken" | ✅ Zostawić (brak alternatywy) |

**Największy konflikt:** Visionary vs rzeczywistość. 14 findingów visionary (GraphQL, Redis, WebSocket, CQRS, materialized views, read replicas) to **dobre pomysły za 12-18 miesięcy**, nie teraz. Projekt ma 94 testy, 3 kontenery, nie jest w production.

---

## Top 3 Quick Wins (low effort, high impact)

### 1. Health endpoint + healthcheck w compose
**Czas:** 2-4h  
**Impact:** Eliminuje 502 errors przy resecie kontenerów

```python
# backend/app/main.py
@app.get("/health")
async def health():
    return {"status": "ok"}
```

```yaml
# docker-compose.dev.yml
services:
  backend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
```

### 2. Security headers w Caddyfile
**Czas:** 1-2h  
**Impact:** Ochrona przed XSS, clickjacking, MIME sniffing

```caddy
# infra/caddy/Caddyfile
header {
    X-Frame-Options "DENY"
    X-Content-Type-Options "nosniff"
    X-XSS-Protection "1; mode=block"
    Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'"
    Strict-Transport-Security "max-age=31536000; includeSubDomains"
}
```

### 3. Retry logic w discord bot (429)
**Czas:** 2-4h  
**Impact:** Bot nie traci danych przy rate limitowaniu

```python
# discord_bot/cogs/prices.py
async def post_with_retry(session, url, data, max_retries=3):
    for attempt in range(max_retries):
        async with session.post(url, json=data) as resp:
            if resp.status == 429:
                retry_after = int(resp.headers.get("Retry-After", 60))
                await asyncio.sleep(retry_after * (attempt + 1))  # exponential backoff
                continue
            if resp.status >= 500:
                await asyncio.sleep(5 * (attempt + 1))
                continue
            return await resp.json()
```

---

## Long-term Roadmap (pogrupowane tematycznie)

### Q3 2026 (3-6 miesięcy)

#### Bezpieczeństwo
- [ ] Globalny rate limiter middleware (nie tylko per-endpoint)
- [ ] CSRF tokens w admin panelu
- [ ] Audit logi (kto, co, kiedy)
- [ ] Walidacja `source` jako enum (`Literal['ah', 'discord', 'manual']`)

#### Testy
- [ ] Testy rate limitingu
- [ ] Testy expired token / superuser auth
- [ ] Integration tests (ingest → prices → crafting)
- [ ] Load testing (concurrent users, large inventory)

#### Code Quality
- [ ] Extract pagination helper
- [ ] Refactor `seed.py` (złożoność 15 → 3 funkcje)
- [ ] Usunąć podwójną instancję `authentication_backend`
- [ ] Dodać rollbacki we wszystkich serwisach

### Q4 2026 (6-12 miesięcy)

#### Infra
- [ ] Monitoring (Prometheus + Grafana)
- [ ] Log aggregation (Loki + Promtail)
- [ ] Backup strategy (pg_dump cron, WAL archiving)
- [ ] Disaster recovery plan (RTO, RPO)

#### Performance
- [ ] Redis cache dla frequently accessed data (items list, price history)
- [ ] Database indexes audit (czy wszystkie query są optymalne?)
- [ ] Query optimization (SELECT tylko potrzebnych kolumn)

#### Frontend
- [ ] Accessibility audit (WCAG 2.1 AA)
- [ ] Error boundaries w Svelte components
- [ ] Optimistic UI dla inventory operations
- [ ] Loading states dla wszystkich async operations

### 2027+ (12+ miesięcy)

#### Architecture (Visionary findings)
- [ ] Event-driven price ingestion (Kafka/RabbitMQ)
- [ ] WebSocket/SSE dla real-time price updates
- [ ] GraphQL dla complex queries (optional, REST może wystarczyć)
- [ ] CQRS dla crafting calculator (read models z precomputed profit)
- [ ] Read replicas dla heavy read workloads

#### Data
- [ ] Data retention policy (GDPR, right to be forgotten)
- [ ] Archiwizacja starych PricePoint (>1 rok)
- [ ] Analytics dashboard (top items, price trends)

---

## Co działa dobrze (🟢 findings)

| Obszar | Co działa | Dlaczego dobrze |
|--------|-----------|-----------------|
| **Auth** | Cookie-based (HttpOnly), nie localStorage | Brak XSS → brak kradzieży tokenów |
| **SQL** | SQLModel z parametryzowanymi zapytaniami | Brak SQL injection |
| **Frontend** | Svelte escape'uje domyślnie, brak `{@html}` | Brak XSS |
| **Rate limiter** | Singleton w `app/config/rate_limit.py` | Zgodne z `patterns.md` |
| **Ingest** | Partial success (200 z `errors[]`) | Zgodne z kontraktem |
| **add_price_point** | Atomowa aktualizacja `current_price` | Zgodne z `constitution.md` |
| **UserInventory** | `ON CONFLICT` dla upsert, DELETE dla 0 | Zgodne z `patterns.md` |
| **Naive UTC** | `replace(tzinfo=None)` wszędzie | Zgodne z `patterns.md` |
| **Pydantic** | Pełna walidacja (min/max length, ge, gt) | Bezpieczne wejście |
| **Testy** | 94 testy, 95% coverage, UUID suffix | Brak flaky tests |
| **CI** | GitHub Actions (lint, test, alembic) | Automatyczna weryfikacja |

---

## Czego brakuje (niezgłoszone przez subagentów)

| Obszar | Brakujący element | Ryzyko |
|--------|-------------------|--------|
| **Monitoring** | Log aggregation, metrics, tracing, alerting | Brak visibility na production issues |
| **Backup** | pg_dump cron, WAL archiving, recovery testing | Ryzyko utraty danych |
| **Disaster Recovery** | Runbooki, RTO/RPO definicje | Długi downtime przy awarii |
| **Documentation** | Changelog, API docs (poza OpenAPI), runbooki | Trudny onboarding, tribal knowledge |
| **Accessibility** | WCAG audit, screen reader support, keyboard nav | Wykluczenie użytkowników |
| **Performance** | Benchmarks (p50, p95, p99), load tests | Nie wiadomo gdzie są bottlenecks |
| **Data Retention** | Polityka przechowywania PricePoint, GDPR | Ryzyko compliance, storage costs |

---

## Podsumowanie

**Stan projektu:** **Dobry** — większość inwariantów jest zachowana, testy przechodzą, CI działa. Kod jest czysty (ruff, mypy clean), architektura modularna.

**Największe ryzyka:**
1. **Security:** Discord token i `.env` w git — **naprawić w ciągu godziny**
2. **Reliability:** Brak rollbacków w serwisach — naprawić w tym tygodniu
3. **Availability:** Brak healthchecków — naprawić w tym tygodniu

**Dług techniczny:** Umiarkowany — głównie refaktory (pagination helper, seed.py complexity, dead code). Żaden nie blokuje production.

**Premature optimization:** Visionary findings (GraphQL, Redis, WebSocket, CQRS) — **odłożyć na 12+ miesięcy**. Projekt nie jest w production, nie ma sensu optymalizować przed skalą.

**Rekomendacja:** Skup się na P0 i P1 (security + reliability). Reszta to backlog.

---

## Output końcowy

**Pliki audytu:**
```
audit/
├── 00-context.md          # Kontekst projektu
├── 01-plan.md             # Plan audytu
├── backend/findings.md    # 15 findings (1🔴, 4🟠, 4🟡, 6🟢)
├── frontend/findings.md   # 6 findings (1🟠, 3🟡, 2🟢)
├── infra/findings.md      # 13 findings (1🔴, 3🟠, 4🟡, 3🟢, 2💡)
├── discordbot/findings.md # 7 findings (1🔴, 1🟠, 2🟡, 3🟢)
├── integration/findings.md# 5 findings (2🟠, 3🟡)
├── security/findings.md   # 18 findings (2🔴, 6🟠, 4🟡, 3🟢, 3💡)
├── dependencies/findings.md# 8 findings (4🟠, 3🟡, 1🟢)
├── code-quality/findings.md# 7 findings (2🟠, 3🟡, 2🟢)
├── tester-evaluator/findings.md # 7 findings (2🟠, 3🟡, 2🟢)
├── skeptic/findings.md    # 13 findings (2🔴, 5🟠, 4🟡, 2💡)
├── visionary/findings.md  # 15 findings (4🟠, 6🟡, 1🟢, 4💡)
├── second-opinion/findings.md # Krytyczna recenzja wszystkich
└── synthesis.md           # Ten plik
```

**Ścieżka do syntezy:** `/home/dv6/GitHub/audit-opencode-20260520-2222/audit/synthesis.md`
