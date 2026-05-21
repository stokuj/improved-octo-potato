# Audyt ArcheRage Market Tracker — deepseek-v4-pro
>
> **Data:** 2026-05-20 | **Subagentów:** 12 | **Łącznie findings:** 104
>
> ---
>



---


# 00 — Context (Rozpoznanie)

## Stack

| Warstwa | Technologia |
|---------|------------|
| Backend | Python 3.13, FastAPI, SQLModel (SQLAlchemy), uvicorn |
| Frontend | TypeScript 6.0, SvelteKit 5 (adapter-node), Vite 8, Tailwind CSS 4 + daisyUI 5, ECharts 5 |
| Baza danych | PostgreSQL 16 (asyncpg + psycopg) |
| Infra | podman compose (dev + prod), Caddy (reverse proxy) |
| Discord Bot | Python 3.13, discord.py 2.4, httpx |
| Migracje | Alembic (5 rewizji) |
| Auth | fastapi-users (JWT cookie-based) |
| Admin | sqladmin (mounted at `/admin`) |
| Rate limiting | slowapi (singleton w `app/config/rate_limit.py`) |

## Entry pointy

| Warstwa | Plik | Komenda startu |
|---------|------|----------------|
| Backend | `backend/app/main.py` | `uv run fastapi dev app/main.py` |
| Frontend | SvelteKit routes | `npm run dev` (Vite dev server) |
| Discord Bot | `discord_bot/bot.py` | `uv run python bot.py` |
| Infra dev | `infra/compose/docker-compose.dev.yml` | `make dev-up` |
| Infra prod | `infra/compose/docker-compose.prod.yml` | `make prod-up` |

## Mapa warstw i komunikacji

```
Przeglądarka ──HTTP──▶ Caddy ──reverse proxy──▶ Frontend (SvelteKit, port 3000)
                          │                      Backend  (FastAPI,  port 8000)
                          │
Discord Bot ──HTTP──▶ Backend API (/api/ingest/, /api/items/)
Game Addons ──HTTP──▶ Backend API (/api/ingest/prices)
```

- **Frontend ↔ Backend**: REST HTTP, cookie-based JWT auth, `credentials: 'include'`
- **Discord Bot ↔ Backend**: REST HTTP, no auth
- **Brak**: message broker, kolejek, eventów, WebSocketów — czyste REST
- **API types**: generowane z OpenAPI (`openapi-typescript` → `frontend/src/lib/api.d.ts`)

## Domeny backendu (pod `/api/`)

| Router | Prefiks | Odpowiedzialność |
|--------|---------|-----------------|
| auth | `/api/auth/` | Login/logout/register (JWT) |
| users | `/api/users/` | User CRUD |
| profiles | `/api/profiles/` | User profiles |
| items | `/api/items/` | Item listing + search |
| prices | `/api/items/{id}/prices` | Price history |
| user_items | `/api/user-items/` | Followed/saved items |
| user_inventory | `/api/inventory/` | User inventory |
| crafting | `/api/crafting/` | Crafting calculator |
| ingest | `/api/ingest/` | Bulk price submission |

## Stan testów i CI

| Warstwa | Testy | Framework | CI |
|---------|-------|-----------|-----|
| Backend | 11 plików testowych | pytest + pytest-asyncio | GitHub Actions (4 workflows) |
| Discord Bot | 1 plik (`test_prices.py`) | pytest + respx | Brak dedykowanego CI |
| Frontend | **Brak** | — | `svelte-check` tylko |

## Co NIE istnieje

- Frontend testy (Vitest, Playwright, Svelte Testing Library)
- ESLint / Prettier / Biome (frontend)
- Ruff config (backend — leci na defaultach)
- Pre-commit hooks
- Health check endpoint
- Structured logging / OpenTelemetry / Sentry
- API versioning (brak `/api/v1/`)
- CD pipeline (CI buduje obrazy, ale nie pushuje/deployuje)
- Message broker / kolejki / eventy
- Shared npm package / monorepo tooling
- `.dockerignore` dla backend i discord_bot


---


# 01 — Plan audytu

## Subagenty per warstwa

### backend
- **Scope:** `backend/app/` — wszystkie domeny: auth, users, profiles, items, prices, user_items, user_inventory, crafting, ingest + config + admin + admin_auth
- **Out of scope:** `backend/tests/` (to tester-evaluator), `backend/alembic/` (to infra), dependencies (to dependencies)
- **Kluczowe pytania:**
  1. Czy każda domena ma spójną strukturę (models/schemas/services/router)?
  2. Czy są wycieki biznes-logiki do routerów (zamiast w serwisach)?
  3. Czy zapytania SQL nie mają N+1?
  4. Czy obsługa błędów jest spójna i nie wycieka stacktrace'ów?
  5. Czy admin auth backend jest bezpieczny?

### frontend
- **Scope:** `frontend/src/` — routes, components, lib (auth, types, currency, grades, crafting, config)
- **Out of scope:** `frontend/static/`, `frontend/package.json` (dependencies), `frontend/svelte.config.js`
- **Kluczowe pytania:**
  1. Czy state management jest spójny i nie ma wyścigów (race conditions)?
  2. Czy fetch error handling jest obecny wszędzie czy ignored?
  3. Czy komponenty są poprawnie podzielone i reużywalne?
  4. Czy auth flow obsługuje wygaśnięcie tokena?
  5. Czy `api.d.ts` jest zsynchronizowane z backendem?

### infra
- **Scope:** `infra/` (docker-compose, Caddyfile), `Makefile`, `backend/Dockerfile`, `frontend/Dockerfile`, `discord_bot/Dockerfile`, `.github/workflows/`
- **Out of scope:** kod aplikacji, testy
- **Kluczowe pytania:**
  1. Czy docker-compose dev vs prod są spójne?
  2. Czy Caddy konfiguracja jest bezpieczna (TLS, headery)?
  3. Czy CI buildy są poprawne i nie marnują cache?
  4. Czy obrazy są minimalne (multi-stage, .dockerignore)?
  5. Czy healthchecki są skonfigurowane?

### discordbot
- **Scope:** `discord_bot/` — bot.py, cogs/, tests/
- **Out of scope:** pyproject.toml (dependencies)
- **Kluczowe pytania:**
  1. Czy error handling w slash komendach jest kompletny?
  2. Czy bot poprawnie używa defer/respond żeby nie timeoutować?
  3. Czy API client do backendu ma timeout i retry?
  4. Czy `lookup_item()` jest odporny na niejednoznaczne wyniki?

### integration
- **Scope:** Kontrakty API między frontend↔backend, discord_bot↔backend, addon↔backend
- **Out of scope:** wewnętrzna logika warstw
- **Kluczowe pytania:**
  1. Czy frontendowe typy z `api.d.ts` pokrywają wszystkie używane endpointy?
  2. Czy discord_bot i addon używają tych samych endpointów co frontend — czy są niespójności?
  3. Czy format waluty (gold/silver/bronze) jest spójny między wszystkimi warstwami?
  4. Czy `LABOUR_ITEM_NAME` jest zsynchronizowany?

---

## Subagenty cross-cutting

### security
- **Scope:** Całe repo — secrets, CORS, auth, walidacje wejścia, SQL injection, XSS, CSRF, rate limiting, deserializacja
- **Out of scope:** infrastruktura sieciowa poza Caddy
- **Kluczowe pytania:**
  1. Czy NIE ma secrets w repo (skany `.env`, `*.key`, `*.pem`)?
  2. Czy wszystkie endpointy mutujące mają auth guard?
  3. Czy jest podatność na SQL injection przez string concatenation?
  4. Czy CORS jest restrykcyjny czy allow-all?
  5. Czy rate limiting pokrywa wszystkie krytyczne endpointy?

### dependencies
- **Scope:** `backend/pyproject.toml`, `discord_bot/pyproject.toml`, `frontend/package.json`
- **Out of scope:** kod aplikacji
- **Kluczowe pytania:**
  1. Które paczki mają znane CVE?
  2. Które paczki są EOL / deprecated?
  3. Które runtime'y są bliskie EOL?
  4. Czy są nieużywane zależności?
  5. Czy pinning wersji jest odpowiedni (^ vs >=)?

### code-quality
- **Scope:** Całe repo — DRY, nazewnictwo, dead code, struktura katalogów, spójność
- **Out of scope:** testy (tester-evaluator), dependencies
- **Kluczowe pytania:**
  1. Czy jest skopiowany kod (copy-paste)?
  2. Czy nazewnictwo jest spójne (case konwencje, nazwy plików)?
  3. Czy jest dead code (nieużywane funkcje, importy, zmienne)?
  4. Czy są god objects / zbyt duże pliki?
  5. Czy konwencje są spójne między backendem a frontendem?

### tester-evaluator
- **Scope:** `backend/tests/`, `discord_bot/tests/`, `frontend/src/` (brak testów)
- **Out of scope:** implementacja nowych testów
- **Kluczowe pytania:**
  1. Czy istniejące testy backendu testują logikę biznesową czy tylko CRUD?
  2. Czy pokrycie testowe jest odpowiednie (jakie domeny nie są testowane)?
  3. Czy testy discord_bot są sensowne — czy mockują właściwe rzeczy?
  4. Jakich typów testów brakuje (unit vs integration vs e2e)?
  5. Czy conftest.py backendu jest bezpieczny (czy nie zostawia śmieci w DB)?

---

## Subagenty meta-perspektywa

### skeptic
- **Scope:** Całość architektury i decyzji projektowych
- **Out of scope:** implementacja
- **Kluczowe pytania:**
  1. Czy architektura domenowa jest przerostem formy nad treścią?
  2. Czy fastapi-users nie jest overkill dla tego projektu?
  3. Czy sqladmin to dobry wybór czy lepiej custom panel?
  4. Czy SvelteKit 5 (rune mode) nie jest zbyt świeże/niestabilne?
  5. Czy są elementy które można by usunąć bez utraty wartości?

### visionary
- **Scope:** Całość — alternatywne wzorce, uproszczenia, nowe podejścia
- **Out of scope:** implementacja
- **Kluczowe pytania:**
  1. Czy można by uprościć architekturę (np. łącząc niektóre domeny)?
  2. Czy pattern API types mógłby być lepszy (np. tRPC, shared package)?
  3. Czy są okazje na zastąpienie custom kodu biblioteką?
  4. Czy frontend mógłby działać z SSR/SSG dla lepszego UX?
  5. Jakie narzędzia deweloperskie by pomogły (tilt, devbox, Nix)?

### second-opinion (URUCHAMIANY OSTATNI)
- **Scope:** Wszystkie `audit/*/findings.md` poza własnym
- **Out of scope:** tworzenie nowych findings
- **Zadania:**
  1. Potwierdź najistotniejsze findings z każdego subagenta
  2. Podważ te, które wydają się przesadzone / false positive
  3. Dodaj kontekst, który inni mogli przeoczyć
  4. Wskaż konflikty między subagentami
  5. NIE zagłuszaj ani nie ignoruj — dodaj swoją opinię


---


# Synthesis — Audyt ArcheRage Market Tracker

**Model:** deepseek-v4-pro | **Data:** 2026-05-20 | **Subagentów:** 12 | **Łącznie findings:** 104

---

## 1. TL;DR — Top 10 (posortowane po severity)

| # | Sev | Problem | Źródło |
|---|-----|---------|--------|
| 1 | 🔴 | `POST /api/ingest/prices` — brak autoryzacji, każdy może wstrzyknąć ceny | security |
| 2 | 🔴 | Domyślne sekrety przewidywalne w `settings.py` (32-znakowe placeholder) | security |
| 3 | 🔴 | Token Discorda w `.env` — wyciek do repo | security |
| 4 | 🔴 | Race condition w `add_price_point` — brak `SELECT FOR UPDATE` | backend |
| 5 | 🔴 | `load_all_recipes()` + `load_all_items()` ładują całą bazę do RAM per request | backend, skeptic, visionary |
| 6 | 🔴 | Kalkulator craftingu nie propaguje kosztów składników — `batch_profit` błędny | backend |
| 7 | 🔴 | Frontend: zero testów — brak frameworka testowego | tester-evaluator |
| 8 | 🔴 | `SecureAdminAuth` — martwy kod, admin cookies bez `https_only` | backend |
| 9 | 🔴 | `ItemTable.svelte` — god component 349 linii + brak grade "Basic" w filtrze | skeptic, code-quality |
| 10 | 🔴 | `LABOUR_ITEM_NAME` tylko we frontendzie — brak odpowiednika w backendzie | integration |

---

## 2. Krytyczne — natychmiastowa akcja (🔴)

### 2.1 Brak auth na ingest (security)
`POST /api/ingest/prices` nie ma żadnego guarda. Rate limit 60/min to jedyna ochrona. Atakujący może tworzyć dowolne itemy, wstrzykiwać fałszywe ceny i skazić całą bazę danych rynkowych. **To podważa fundamentalną integralność trackera.**

### 2.2 Domyślne sekrety (security)
`settings.py:27` — `"temporary-development-secret-must-be-32-chars"`. Jeśli zmienne `AUTH_SECRET` i `ADMIN_SESSION_SECRET` nie są ustawione produkcyjnie, JWT i sesje admina są łamliwe od razu po wycieku kodu źródłowego.

### 2.3 Token Discorda w `.env` (security)
Discord bot token w `.env` — potencjalnie skomitowany lub wyciekający przez backup/logi. Kompromitacja tokena = przejęcie bota.

### 2.4 Race condition w cenach (backend)
`prices/services.py:add_price_point()` aktualizuje `Item.current_price` przez `SELECT + UPDATE` bez blokady. Dwie współbieżne transakcje mogą nadpisać sobie nawzajem cenę.

### 2.5 `load_all_recipes/load_all_items` (backend + skeptic + visionary)
Każdy request do craftingu wykonuje `SELECT * FROM recipe` + `SELECT * FROM item` + `SELECT * FROM recipe_ingredient`. Przy 29 itemach niezauważalne. Przy 200+ — OOM/timeout. Dotyczy `calculate()`, `list_summaries()`, `build_craft_tree()`.

---

## 3. Wzorce powtarzające się — złapane przez ≥2 subagentów

| Wzorzec | Subagenty | Opis |
|---------|-----------|------|
| **Duplikacja `utcnow()`** | backend, code-quality, skeptic | 5 kopii `utcnow()` w models.py + `to_naive()` + `_normalize_ts()` = **7 kopii** tej samej logiki czasowej |
| **`load_all_recipes` + `load_all_items`** | backend, skeptic, visionary | Ładowanie całej bazy do RAM — 3 subagentów z różnych perspektyw: wydajność, skalowalność, architektura |
| **Over-engineering modułów** | skeptic, visionary | 10 domen na ~1800 linii backendu. Obaj zgadzają się: scalać cienkie moduły (profiles→users, user_items+user_inventory→me) |
| **Duplikacja formatowania waluty** | code-quality, integration | `formatCurrency` (frontend, "bronze") vs `format_price` (bot, "copper") vs `splitCurrency` — 3 implementacje z różnymi konwencjami |
| **Brak konfiguracji linterów** | code-quality, visionary, security | Brak `.editorconfig`, `.pre-commit-config.yaml`, konfiguracji ruff, ESLint, Prettier. `print()` w auth wyciekłby gdyby była reguła T201 |
| **ItemTable.svelte** | skeptic, code-quality | God component + brak grade "Basic" — ten sam problem: ręczna kopia enuma w monolitycznym komponencie |
| **Brak testów frontendu** | tester-evaluator, second-opinion | 22 pliki, 0 testów. Logika `formatCurrency`, `computeNodeCost` — nietestowana czysta logika biznesowa |

---

## 4. Konflikty opinii

| Temat | Strona A | Strona B | Rozstrzygnięcie |
|-------|----------|----------|-----------------|
| **fastapi-users: zostawić vs przepisać** | Skeptic: przepisać na `python-jose` (~80 linii) | Backend: naprawić istniejące bugi w auth | Naprawić martwy kod w `admin_auth.py` + dodać rate limit na login. Przepisanie auth to zbyt duże ryzyko regresji na tym etapie |
| **Scalanie domen: jak grupować** | Skeptic: user_items+user_inventory razem, profiles+users razem | Visionary: auth+users, items+prices, me (user_items+inventory) | Visionary ma lepsze grupowanie. Ale najpierw ujednolicić strukturę modułów (każdy z tym samym zestawem plików) |
| **SQL vs Python bucketing** | Visionary: `date_trunc` + `GROUP BY` w SQL | Nikt nie kwestionuje | Visionary ma rację, ale to nie jest bottleneck przy 29 itemach. Zrobić przy okazji dodawania paginacji |
| **SSR vs CSR w SvelteKit** | Visionary: użyć `load` zamiast `onMount` | Frontend/Skeptic: nie komentują | Najpierw naprawić backend caching (`load_all_*`), potem rozważyć SSR. Bez cache'a SSR będzie wolniejsze niż CSR |

---

## 5. Top 3 Quick Wins (low effort, high impact)

| # | Akcja | Wysiłek | Impact |
|---|-------|---------|--------|
| 1 | Dodać `@limiter.limit("30/minute")` + auth guard na `POST /api/ingest/prices` | ~15 min | Blokuje największy wektor ataku |
| 2 | Wynieść `utcnow()` do `app/config/_utils.py` + zaimportować we wszystkich 7 miejscach | ~30 min | Eliminuje najczęściej duplikowaną logikę, zapobiega rozjazdom |
| 3 | Dodać `GRADES` + `CATEGORIES` jako endpoint `GET /api/items/metadata` + używać w ItemTable | ~1h | Naprawia bug z brakującym "Basic", eliminuje ręczną kopię enuma |

---

## 6. Long-term Roadmap

### Faza 1 — Hardening (bezpieczeństwo + stabilność)
- [ ] Dodać auth na `POST /api/ingest/prices`
- [ ] Wymusić `AUTH_SECRET` + `ADMIN_SESSION_SECRET` przez env (brak defaultów)
- [ ] Dodać `SELECT FOR UPDATE` w `add_price_point`
- [ ] Naprawić `SecureAdminAuth` — `https_only` na sesji admina
- [ ] Dodać security headers w Caddyfile (HSTS, CSP, X-Frame-Options)
- [ ] Dodać healthcheck endpoint `/api/health`
- [ ] Dodać healthchecki w docker-compose (backend, frontend, caddy, db)
- [ ] Dodać rate limiting na `POST /api/auth/login` i `POST /api/auth/register`

### Faza 2 — Performance + skalowalność
- [ ] Cache'ować `all_recipes` + `all_items` w `app.state` (ładowane raz w `lifespan`)
- [ ] Dodać paginację do `GET /api/items/` (offset/limit)
- [ ] Dodać paginację do `GET /api/crafting/` (zamiast liczenia wszystkiego)
- [ ] Zamienić Python-bucketing cen na SQL `date_trunc` + `GROUP BY`
- [ ] Naprawić kalkulator craftingu — propagować koszty sub-składników
- [ ] Dodać dedykowany `GET /api/items/by-name-grade` dla discord bota

### Faza 3 — Testy
- [ ] Dodać vitest + @testing-library/svelte do frontendu
- [ ] Unit testy dla `currency.ts`, `grades.ts`, `crafting.ts`
- [ ] Testy komponentowe dla ItemTable, RecipeTree, EChartsLineChart
- [ ] Testy dla `admin_auth.py` (login, autoryzacja)
- [ ] Testy dla rate limitingu (sprawdzić 429)
- [ ] Rozszerzyć `test_consistency.py` o więcej cross-file invariantów
- [ ] Przenieść duplikowane fixture'y (`db_session`, `_email`, `auth_client`) do `conftest.py`

### Faza 4 — Architektura
- [ ] Ujednolicić strukturę modułów — każda domena z tym samym zestawem plików
- [ ] Scalać cienkie moduły: `profiles`→`users`, `user_items`+`user_inventory`→`me`
- [ ] Centralizować `utcnow()`, `to_naive()`, `_normalize_ts()` do jednego utility
- [ ] Ujednolicić formatowanie waluty — jeden format, jedna konwencja ("copper")
- [ ] Wyciągnąć `LABOUR_ITEM_NAME` do backendu (lub shared constant)
- [ ] Rozbić `ItemTable.svelte` na: data-fetching, filtrowanie, wirtualna lista, wiersz
- [ ] Wyciągnąć `computeNodeCost` do `$lib/crafting.ts` (jedna wspólna funkcja)

### Faza 5 — DevOps + DX
- [ ] Dodać `.editorconfig`, `.pre-commit-config.yaml` (ruff + prettier + svelte-check)
- [ ] Dodać konfigurację ruff w `backend/pyproject.toml` (`[tool.ruff]`)
- [ ] Dodać regułę `T201` (no-print) w ruff
- [ ] Dodać `make lint`, `make format`, `make typecheck` do Makefile
- [ ] Commitować `uv.lock` i `package-lock.json` dla reprodukowalnych buildów
- [ ] Dodać `.dockerignore` dla backend i discord_bot
- [ ] Rozważyć `openapi-fetch` zamiast ręcznych `fetch()` w frontendzie
- [ ] Rozważyć wyciągnięcie shared API schemas do osobnego pakietu Python

### Faza 6 — Przyszłościowe (nice-to-have)
- [ ] SSR dla publicznych stron (po naprawie backend cache)
- [ ] Lżejsza biblioteka wykresów (uPlot zamiast ECharts — jeśli bundle size będzie problemem)
- [ ] Wersjonowanie API (`/api/v1/...`)
- [ ] CD pipeline (push obrazów do rejestru, deploy)
- [ ] Structured logging / OpenTelemetry / Sentry
- [ ] Zastąpienie ręcznych grade mappingów między backend↔frontend↔bot przez API metadata


---




---




---




---




---




---




---




---




---




---




---




---


