# Audyt ArcheRage Market Tracker — kimi-k2.6 / 2026-05-20

**Data:** 2026-05-20  
**Model:** kimi-k2.6 (opencode-go/kimi-k2.6)  
**Scope:** backend, frontend, discord_bot, infra, docs (bez addon Lua)  
**Branch:** `audit/kimi-k2.6` na worktree `.worktrees/kimi-k2.6`

---

## 1. Podsumowanie wykonawcze

Projekt jest **dobrze zorganizowany i konsekwentny** — szczególnie backend wykazuje silną dyscyplinę architektoniczną (domena-per-folder, cienkie routery, DI). Jednak w miarę rozwoju pojawiły się **duplikacje, tight coupling i anty-patterny**, które z czasem staną się długiem technicznym. Najpoważniejsze problemy to:

1. **Wydajność ingest** — każdy wiersz bulk ingest powoduje osobny commit DB.
2. **Frontend bez warstwy API** — wszystkie komponenty robią `fetch()` bezpośrednio, co prowadzi do god components i duplikacji logiki.
3. **Brak `from_attributes=True`** — wymusza ręczne mapowanie schematów w routerach i serwisach.
4. **Silent failures** — `get_inventory_for_recipe` ukrywa błędy (`AppError` → `{}` 200).

---

## 2. Backend (FastAPI + SQLModel)

### 2.1 Struktura i architektura — ocena: dobra

- **Pattern domenowy** (`models/schemas/services/router/admin`) jest konsekwentnie stosowany we wszystkich modułach.
- **Pliki są małe** — żaden produkcyjny plik nie przekracza 300 linii (poza `seed.py` 286 linii).
- **Dependency injection** działa poprawnie przez `Depends(get_async_session)`.
- **Brak circular imports** — graf zależności jest acykliczny.

### 2.2 Znalezione problemy

#### KRYTYCZNE / HIGH

| # | Problem | Lokalizacja | Konsekwencja |
|---|---------|-------------|--------------|
| BE-01 | **Ingest robi commit per row** | `app/ingest/services.py:46`, `app/prices/services.py:123` | Przy 100 wierszach = 200 commitów. To zabija wydajność i obciąża DB. |
| BE-02 | **Broad `except Exception`** | `app/ingest/services.py:88-93`, `95-107` | Maskuje błędy programistyczne (np. `AttributeError`, `TypeError`). |
| BE-03 | **Cross-domain write coupling** | `app/prices/services.py:117-121` | Serwis `prices` mutuje `Item.current_price`. To reguła biznesowa należąca do `items`. |
| BE-04 | **Silent failure w `for-recipe`** | `app/user_inventory/services.py:87-88` | `AppError` (cycle, max depth) jest łapiony i zwracany jako `{}` z HTTP 200. Klient nie wie o błędzie. |
| BE-05 | **Routing overlap / shadowing** | `app/main.py:47-48` | `prices_router` ma prefix `/items`, ten sam co `items_router`. Działa przez kolejność rejestracji, ale jest fragile. |

#### MEDIUM

| # | Problem | Lokalizacja | Konsekwencja |
|---|---------|-------------|--------------|
| BE-06 | **Brak `ConfigDict(from_attributes=True)`** | `app/items/schemas.py`, `app/prices/schemas.py` | Wymusza ręczne mapowanie pól w routerach (`items/router.py:37-45`, `prices/router.py:60-65`). Podatne na błędy przy zmianach schematu. |
| BE-07 | **Duplikacja `utcnow()`** | `items/models.py:7`, `prices/models.py:6`, `user_items/models.py:7`, `profiles/models.py:7`, `seed.py:17` | Identyczna funkcja w 5 plikach. Powinna być w `app/config/utils.py`. |
| BE-08 | **Duplikacja timezone normalization** | `app/prices/services.py:23-24`, `105-107`, `app/ingest/services.py:59-62` | Logika `replace(tzinfo=None)` jest powtarzana. Wspólna funkcja `to_naive_utc()` potrzebna. |
| BE-09 | **Dead code w `admin_auth.py`** | `app/admin_auth.py:46` | `authentication_backend = AdminAuth(...)` jest natychmiast nadpisane przez `SecureAdminAuth(...)` w liniach 67-69. |
| BE-10 | **Unused schema `UserItemRead`** | `app/user_items/schemas.py:8-14` | Zdefiniowany ale nigdy nieużywany w routerze ani serwisie. |
| BE-11 | **Manual schema construction w services** | `app/items/services.py:36-46`, `app/prices/services.py:38-45` | `ItemListItem` i `PricePointRead` są konstruowane ręcznie zamiast przez `model_validate`. |
| BE-12 | **`load_all_recipes` / `load_all_items` wczytują całe tabele** | `app/crafting/services.py:12-25` | Przy 10k+ przedmiotów to będzie problem pamięciowy. Brak paginacji / caching. |

#### LOW

| # | Problem | Lokalizacja | Konsekwencja |
|---|---------|-------------|--------------|
| BE-13 | **Magic strings w testach** | `test_auth.py`, `test_inventory.py`, `test_prices.py`, `test_profiles.py`, `test_user_items.py` | Hardcoded `"password123"` — powinien być stały `TEST_PASSWORD`. |
| BE-14 | **Duplikacja fixture testowych** | `test_*.py` | `db_session` fixture powtarzana w 6+ plikach, `auth_client` w 4+, `_email()` helper w 5+. Powinny być w `conftest.py`. |
| BE-15 | **`test_prices.py` używa `source="market"`** | `test_prices.py:60,75,90,155,184` | Niespójne z konwencją `source="ah"` wymaganą przez `test_consistency.py`. Nie jest błędem, ale jest mylące. |

### 2.3 Modern Python — ocena: bardzo dobra

- **Python 3.13+** — najnowsza wersja.
- **Type hints** (`int | None`, `list[...]`) zamiast `Optional`, `List` z `typing`.
- **`StrEnum`** zamiast `Enum` + manual value.
- **`pydantic-settings`** + `BaseSettings` do konfiguracji.
- **`uv`** jako manager pakietów — nowoczesny i szybki.
- **`sqlmodel`** — łączy SQLAlchemy i Pydantic, choć ma swoje ograniczenia (np. `from_attributes` wymaga `ConfigDict`).
- **Async everywhere** — `asyncpg`, `AsyncSession`, `async/await` w całym stacku.
- **Brak `pytest-mock`** — testy integracyjne na realnym PostgreSQL (`app_test`), bez SQLite.

### 2.4 Wzorce rozbudowy — ocena: dobra

- Dodanie nowej domeny jest dobrze udokumentowane w `docs/ai/patterns.md#new-domain`.
- `backend/app/config/` jest wąsko zdefiniowane i nie rośnie.
- Jedynym zagrożeniem jest to, że `ingest` importuje `prices.services`, a `prices` importuje `items.models` — łańcuch zależności rośnie.

---

## 3. Frontend (SvelteKit 5 + Tailwind 4 + DaisyUI 5)

### 3.1 Architektura — ocena: średnia

- **Svelte 5 runes** są używane konsekwentnie (`$state`, `$derived`, `$props`, `$effect`). Brak legacy `writable`/`derived`.
- **Tailwind 4 + DaisyUI 5** — nowoczesny stack.
- **TypeScript strict** — `tsconfig.json` ma `"strict": true`.
- **openapi-typescript** — typy API generowane automatycznie z backendu.

### 3.2 Znalezione problemy

#### KRYTYCZNE / HIGH

| # | Problem | Lokalizacja | Konsekwencja |
|---|---------|-------------|--------------|
| FE-01 | **Brak warstwy API service** | Wszędzie (`+page.svelte`, `ItemTable.svelte`, `auth.svelte.ts`) | Każdy komponent robi `fetch()` bezpośrednio. Powoduje tight coupling, duplikację URL-i, brak centralnej obsługi błędów. |
| FE-02 | **God component: `items/[id]/+page.svelte`** | `routes/items/[id]/+page.svelte` (367 linii) | Łączy data fetching (4 endpointy), business logic (`computeNodeCost`, profit, margin), chart data transform, inventory optimistic updates, i UI w jednym pliku. |
| FE-03 | **Duplikacja `computeNodeCost`** | `routes/items/[id]/+page.svelte:36-53`, `lib/components/crafting/RecipeTree.svelte:19-33` | Ta sama rekurencyjna logika kosztów w dwóch miejscach. Każda zmiana musi być nanoszona podwójnie. |
| FE-04 | **`// @ts-nocheck` w komponencie chart** | `lib/components/charts/EChartsLineChart.svelte:1` | Wyłącza TypeScript dla całego pliku. To duża dziura w type safety. |
| FE-05 | **`any` w mapowaniu price history** | `routes/items/[id]/+page.svelte:124` | `row: any` zamiast typów z `api.d.ts`. Pozwala na błędne property access. |

#### MEDIUM

| # | Problem | Lokalizacja | Konsekwencja |
|---|---------|-------------|--------------|
| FE-06 | **Mega-komponent: `ItemTable.svelte`** | `lib/components/ItemTable.svelte` (349 linii) | Virtual scrolling, infinite scroll, search debouncing, category/grade filtering, auth-gated saved-item toggling — wszystko w jednym pliku. |
| FE-07 | **Brak server-side data loading** | Wszystkie `+page.svelte` | Brak `+page.ts` / `+page.server.ts`. Wszystko fetchowane w `onMount` → brak SSR, brak preloading, auth redirect po hydracji (flash). |
| FE-08 | **`goto()` w logice biznesowej** | `lib/auth.svelte.ts:65`, `lib/components/ItemTable.svelte:102`, `126` | Funkcje `login()` i `toggleSaved()` wiedzą o routingu. Powinny emitować eventy lub zwracać status. |
| FE-09 | **Duplikacja currency display HTML** | `routes/items/[id]/+page.svelte:286-292`, `lib/components/ItemTable.svelte:299-307` | Ten sam layout gold/silver/bronze pisany ręcznie w dwóch miejscach. Potrzebny `<CurrencyDisplay />`. |
| FE-10 | **Runtime crash risk w avatarze** | `routes/+layout.svelte:54` | `user.data?.email?.[0].toUpperCase()` — jeśli email to pusty string, `.toUpperCase()` rzuci na `undefined`. |

#### LOW

| # | Problem | Lokalizacja | Konsekwencja |
|---|---------|-------------|--------------|
| FE-11 | **Implicit `any` z `response.json()`** | Wiele miejsc (`+page.svelte`, `inventory/+page.svelte`) | `await r.json()` bez castu lub typowania. |
| FE-12 | **`settings/+page.svelte` — dwa `$effect`** | `routes/settings/+page.svelte` | Redirect i profile sync w osobnych `$effect`. Można połączyć w jeden z wczesnym `return`. |

### 3.3 Modern TS/Svelte — ocena: dobra

- **Svelte 5 runes** — pełne zastosowanie, brak legacy stores.
- **Tailwind 4** — nowa wersja z `@tailwindcss/vite`.
- **DaisyUI 5** — nowa wersja.
- **ECharts 5** — aktualny.
- **Adapter Node** — poprawny dla self-hostingu.

### 3.4 Wzorce rozbudowy — ocena: średnia

- Brak centralnego stanu per-domena (np. `items.svelte.ts`, `inventory.svelte.ts`).
- Przy dodaniu nowej strony trzeba powtórzyć ten sam pattern `onMount` + `fetch`.
- Brak reusable API clienta utrudnia dodawanie nowych endpointów.

---

## 4. Discord Bot

### 4.1 Jakość kodu — ocena: dobra

- **Pydantic-settings** do konfiguracji.
- **Respx** do mockowania HTTP w testach — nowoczesne.
- **Testy pokrywają** formatowanie, lookup, posting, handler commands.

### 4.2 Znalezione problemy

| # | Problem | Lokalizacja | Konsekwencja |
|---|---------|-------------|--------------|
| DB-01 | **`command_prefix="!"` w slash-command bocie** | `discord_bot/bot.py:26` | Bot rejestruje tylko slash commands (`/addprice`, `/price`), ale instancja `commands.Bot` wymaga prefixu. To jest niepotrzebne i mylące. |
| DB-02 | **Brak retry / backoff przy błędach HTTP** | `cogs/prices.py` (wnioskowane z testów) | Jeśli backend zwróci 500 lub timeout, bot wysyła błąd do użytkownika zamiast retryować. |
| DB-03 | **Brak healthcheck / readiness** | Brak | Bot nie ma endpointu health ani komendy status. |

---

## 5. Infrastructure (Docker, Caddy, Makefile)

### 5.1 Bezpieczeństwo i utrzymanie — ocena: dobra

- **Prod compose** wymaga secrets przez `:?` — dobra praktyka.
- **Caddy** obsługuje TLS automatycznie.
- **Podman** zamiast Docker — zgodne z wymaganiami projektu.

### 5.2 Znalezione problemy

| # | Problem | Lokalizacja | Konsekwencja |
|---|---------|-------------|--------------|
| INF-01 | **Brak healthchecków dla backend/frontend** | `docker-compose.*.yml` | Tylko `db` ma `healthcheck`. Backend i frontend nie mają — `depends_on` bez `condition: service_healthy` jest słabszy. |
| INF-02 | **Brak rate limitingu w Caddy** | `infra/caddy/Caddyfile` | Wszystkie requesty przechodzą przez Caddy do backendu. Brak rate limitingu na poziomie reverse proxy (chociaż slowapi jest w backendu). |
| INF-03 | **Frontend w dev robi `npm install` przy starcie** | `docker-compose.dev.yml:47` | Każdy restart kontenera = `npm install`. Wolne i niepotrzebne — powinno być w Dockerfile. |
| INF-04 | **`make test` tworzy DB ale nie czyści** | `Makefile:71-75` | `CREATE DATABASE app_test` z `|| true` — jeśli DB istnieje, testy działają na istniejących danych. `conftest.py` robi `drop_all`/`create_all`, więc to jest OK, ale warto dodać komentarz. |
| INF-05 | **Brak `depends_on` `condition` dla backend** | `docker-compose.dev.yml` | Backend startuje gdy db jest healthy, ale frontend nie czeka na backend (choć to mniej krytyczne w dev). |

---

## 6. Dokumentacja (`docs/ai/`)

### 6.1 Spójność — ocena: dobra

- `architecture.md`, `stack.md`, `patterns.md`, `roadmap.md`, `constitution.md` tworzą spójny zestaw.
- `CLAUDE.md` jest świetnym quick-reference.

### 6.2 Znalezione problemy

| # | Problem | Lokalizacja | Konsekwencja |
|---|---------|-------------|--------------|
| DOC-01 | **`patterns.md` wspomina `UserItemRead`** | `docs/ai/patterns.md` | Schema jest zdefiniowany (`app/user_items/schemas.py`) ale nieużywany — dokumentacja może być nieaktualna. |
| DOC-02 | **Brak dokumentacji ingest performance** | `docs/ai/architecture.md` | Nie wspomina o commit-per-row w ingest. To jest ważny invariant dla przyszłych deweloperów. |
| DOC-03 | **Brak dokumentacji frontend patterns** | Brak | Nie ma guide'a jak dodawać nowe strony/komponenty — każdy robi to na czuja. |

---

## 7. Ranking priorytetów

| Priorytet | ID | Problem | Est. effort | Impact |
|-----------|----|---------|-------------|--------|
| **P0** | BE-01 | Ingest commit-per-row | 2-3h | Wysoki — skalowalność |
| **P0** | BE-04 | Silent failure w `for-recipe` | 30m | Wysoki — ukryte błędy |
| **P1** | FE-01 | Brak warstwy API service | 4-6h | Wysoki — utrzymanie |
| **P1** | FE-02 | God component `[id]/+page` | 4-6h | Wysoki — testowalność |
| **P1** | FE-03 | Duplikacja `computeNodeCost` | 1h | Średni — błędy konsystencji |
| **P1** | FE-04 | `// @ts-nocheck` w chart | 1-2h | Średni — type safety |
| **P2** | BE-02 | Broad `except Exception` | 1-2h | Średni — debuggowalność |
| **P2** | BE-03 | Cross-domain write coupling | 2-3h | Średni — architektura |
| **P2** | BE-06 | Brak `from_attributes=True` | 2h | Średni — DRY |
| **P2** | FE-06 | Mega-komponent `ItemTable` | 3-4h | Średni — utrzymanie |
| **P2** | BE-14 | Duplikacja fixture testowych | 1h | Niski — czytelność testów |
| **P3** | BE-07 | Duplikacja `utcnow()` | 30m | Niski — DRY |
| **P3** | BE-09 | Dead code `admin_auth.py` | 15m | Niski — porządek |
| **P3** | FE-10 | Runtime crash risk avatar | 15m | Niski — stabilność |
| **P3** | INF-01 | Brak healthchecków | 1h | Niski — reliability |

---

## 8. Sugestie modernizacji (nie-krytyczne)

1. **Backend:** Rozważ wprowadzenie **CQRS** dla price history (read model z materialized view lub time-series DB jeśli skala wzrośnie).
2. **Backend:** Dodaj **Redis** do cache'owania `load_all_items` / `load_all_recipes` — unikniesz wczytywania całych tabel przy każdym requeście craftingu.
3. **Frontend:** Wprowadź **TanStack Query (Svelte Query)** — zamiast pisać własną warstwę API, dostaniesz caching, deduplication, retry, background refetch.
4. **Frontend:** Użyj **`+page.ts` load functions** — nawet jeśli CSR, `load` daje lepszą kontrolę nad fetchingiem i error boundary.
5. **Testy:** Dodaj **frontend tests** (Playwright lub Vitest + Testing Library). Obecnie frontend ma tylko `svelte-check`.
6. **CI/CD:** Dodaj **frontend build** do GitHub Actions — obecnie workflow sprawdza `svelte-check`, ale nie robi `vite build`.

---

## 9. Wnioski końcowe

Projekt ma **solidne fundamenty** — dobra separację domen w backendzie, nowoczesny stack (Python 3.13, Svelte 5, Tailwind 4), i konsekwentne testy na realnym PostgreSQL. Główne ryzyka to:

- **Wydajność ingest** (P0) — łatwo naprawić, ale obecnie jest wąskim gardłem.
- **Frontend tight coupling** (P1) — bez warstwy API service projekt będzie coraz trudniejszy w utrzymaniu.
- **Silent failures** (P0) — ukryte błędy to najgorszy rodzaj długu technicznego.

Rekomendacja: najpierw naprawić P0 (ingest + silent failures), potem P1 (frontend API layer + god components), a dopiero potem P2/P3.
