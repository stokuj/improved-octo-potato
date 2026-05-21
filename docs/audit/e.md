# Strategic Architecture Audit — ArcheRage Market Tracker

**Model:** GLM-5.1 | **Date:** 2026-05-20 | **Scope:** Backend, Frontend, Infra, Discord Bot

---

## Executive Summary

Projekt ma solidne fundamenty — jasne granice domenowe, consistent naming, integration testy z real DB. Architektura modułowa (backend) i runes-based state (frontend) to dobre decyzje. Jednak audyt odkrywa **5 strategicznych problemów** i kilkanaście średnich, które ograniczają rozszerzalność, bezpieczeństwo i utrzymanie:

| # | Problem | Impact |
|---|---------|--------|
| S1 | Ingest endpoint bez auth — anyone can inject prices | Data integrity risk |
| S2 | Frontend działa w 100% CSR — brak SSR, brak load functions | SEO, performance, UX |
| S3 | Containers run as root + brak security headers w Caddy | Production security risk |
| S4 | Brak API client layer — każdy komponent robi raw fetch | Maintenance, type safety, error handling |
| S5 | Spaghetti w ItemTable (349 LOC) i items/[id] (367 LOC) | Hard to extend, hard to test |

---

## 1. Backend — Architecture & Patterns

### 1.1 Module Structure

Granice modułowe są **dobre**. Każdy moduł ma `models → schemas → services → router` — spójne, przewidywalne. Cross-module imports idą przez services, nie bezpośrednio między modelami — to poprawne.

**Problem: auth→profiles coupling** (`auth/manager.py:30`): `UserManager.on_after_register` importuje `Profile` model i tworzy profil direkt. Łamie izolację — auth module wie o profiles module. Rozwiązanie: event/signal system albo post-registration hook w main.

**Problem: ingest→prices transactional boundary** (`ingest/services.py`): `bulk_ingest` przetwarza wiersze sekwencyjnie, każdy commitowany niezależnie przez `add_price_point()`. Brak atomicznego batcha — jeśli wiersz 5 z 10 fails, pierwsze 4 są już w DB. To celowe (partial success per constitution), ale kontrastuje z tym, że `session.rollback()` jest na poziomie pojedynczego wiersza — batch jako całość nie ma transactional integrity.

### 1.2 Modern Python Gaps

| Feature | Status | Where it matters |
|---------|--------|-----------------|
| `match` statements | Nie używane | `Interval` validation, `grade_map.py`, `ItemCategory` dispatch |
| `Annotated` dependencies | Nie używane | Każdy endpoint powtarza `Depends(get_async_session)` — `Annotated[AsyncSession, Depends(...)]` skróciłby boilerplate |
| `dataclass(kw_only=True)` | Nie używane | Schemas mogłyby użyć `kw_only` zamiast manualnego `field_validator` |
| `logging` module | Używane tylko w `admin_auth.py` | `UserManager` używa `print()` zamiast `logging` |
| Type narrowing expressions | Częściowo | `str \| None` jest OK, ale brak `TypeGuard` czy `assert` type narrowing |

**Werdykt:** Python 3.13 jest required, ale kod wygląda jak Python 3.11. Brak `match`, brak `Annotated` pattern, brak `TypeGuard`. Składnia jest modern, ale idiomy ne.

### 1.3 Database Patterns

**Dobre:** Naive UTC everywhere, parameterized queries, ON CONFLICT upsert pattern, integration tests z real PG.

**Problemy:**

1. **`utcnow()` duplicated 5x** — `items/models.py`, `prices/models.py`, `user_items/models.py`, `profiles/models.py`, `seed.py`. Przenieść do `app/utils.py` albo jako `default_factory` na bazowej klasie.

2. **`created_at` vs `captured_at` w PricePoint** — dwa timestampy, `created_at` nigdy nie expose'owany w API. Jeśli nie jest używany, usunąć.

3. **`UserInventory` brak `created_at/updated_at`** — `UserItem` ma, `UserInventory` nie. Niespójność.

4. **`Recipe` i `RecipeIngredient` brak timestamps** — trudniejsze debugowanie (kiedy ta receptura została dodana?).

5. **Price bucketing w Python** (`prices/services.py:get_item_price_history`) — fetchuje WSZYSTKIE punkty, potem bucketuje w Python. Przy 30d history z minute intervals to >40k wierszy. SQL `date_trunc()` + aggregation byłby skalowalny.

6. **Crafting calculator bez cache** — `load_all_recipes()` i `load_all_items()` na każdy request. Przy 30 itemach OK, ale przy 1000+ to killer.

### 1.4 ORM→Schema Mapping

**Niespójność:** Tylko `ProfileRead` używa `from_attributes=True`. Reszta routerów mapuje ręcznie:
```python
ItemRead(id=item.id, name=item.name, ...)  # 8 pól ręcznie
```
To verbose, error-prone (easy to miss a field), i niespójne. Wszystkie Read schema powinny mieć `model_config = ConfigDict(from_attributes=True)` i używać `ItemRead.model_validate(item)`.

### 1.5 Security

| Issue | Severity | Detail |
|-------|----------|--------|
| `/api/ingest/prices` bez auth | **CRITICAL** | Ktokolwiek może wstrzyknąć ceny. Rate limit 60/min to za dużo na złośliwe dane. |
| Brak rate limit na auth endpoints | **HIGH** | `/auth/register` i `/auth/login` bez limitu — vulnerability na brute force i account spam. |
| Default secrets w settings | **MEDIUM** | `auth_secret` i `admin_session_secret` mają hardcodowane defaults które "pass" walidację >=32 chars. W prod powinny fail jeśli nie są ustawione. |
| CORS `allow_methods=["*"]` i `allow_headers=["*"]` | **MEDIUM** | Overly permissive. |
| `cookie_secure` defaults to `False` | **MEDIUM** | W prod over HTTPS musi być `True`, bez warning. |
| `admin_auth.py:14-15` — `str(None)` → `"None"` | **LOW** | Brak walidacji None przed cast do string. |

### 1.6 Test Architecture

**Dobre:** Integration tests z real PG. UUID suffix pattern. Conftest z `httpx.AsyncClient`.

**Problemy:**

1. **Duplicated fixtures** — `db_session` i `auth_client` powtórzone w 6+ plikach. Powinny być w `conftest.py`.
2. **Brak coverage dla:** admin endpoints, rate limiting, CORS, user update/delete, pagination edge cases, `5m` bucket interval.
3. **Brak negatywnych testów ingest rollback** — constitution mówi "session.rollback after failed add_price_point" ale nie ma testu który weryfikuje to behavior.

### 1.7 Service Layer Patterns

**Transaction management inconsistency:** Każdy moduł robi commit inaczej:

| Module | Pattern |
|--------|---------|
| prices | `session.add() + commit() + refresh()` |
| user_items | `pg_insert + commit()` |
| user_inventory | `session.execute() + commit()` |
| profiles | `setattr + add() + commit() + refresh()` |
| ingest | Hierarchiczne commity (outer batch, inner per-row) |

Brak standardu. Powinien być jeden wzorzec: service robi operacje na sesji, **router** robi `session.commit()` na końcu — albo (alternatywnie) każdy service jest atomowy i commituje sam, ale z clear unit-of-work boundary. Obecny mix to potencjalne źródło bugów.

---

## 2. Frontend — Architecture & Patterns

### 2.1 SSR vs CSR — The Big Strategic Gap

**Żaden route nie ma `+page.ts` ani `+layout.ts` z `load` function.** Wszystko jest client-side fetch w `onMount` albo jako side-effect w scopes komponentów. Skutek:

- **Zero SSR** — strona jest empty shell dopóki JS nie pobierze danych. Crawleri widzą pustą stronę.
- **Brak hydration** — dane są pobierane dwa razy (SSR shell + client fetch).
- **Flash of empty content** — spinner po każdym nawigation.
- **`data-sveltekit-preload-data="hover"` w app.html** — bezużyteczne bo nie ma `load` functions.

**Rekomendacja:** Dodaj `+page.ts` z `load` do wszystkich route. Przenies fetch z `onMount` do load functions. To najważniejsza zmiana architektoniczna w frontend.

### 2.2 API Client Layer — Missing Abstraction

Każdy komponent robi raw `fetch()` z inline `${API_BASE_URL}`. Skutek:

- Brak centralnego error handling (każdy komponent łapie catch sam)
- Brak retry logic
- Brak type-safe response parsing (`response.json()` bez generyka)
- Auth redirect (401 → `/auth`) powtórzony w 3 miejscach
- Brak request interceptors (logging, timing)

**Rekomendacja:** Stwórz `src/lib/api.ts` z typed clientem. Pattern:

```typescript
// src/lib/api.ts
export const api = {
  async get<T>(path: string): Promise<T> { ... },
  async post<T>(path: string, body: unknown): Promise<T> { ... },
  // central 401 handling, error typing, etc.
}
```

### 2.3 God Components

**`ItemTable.svelte` (349 LOC)** — fetch, filter, virtual scroll, save/unsave, pagination, error handling. Łamie SRP. Powinien być rozbity na: `ItemsFetch` (data), `ItemsList` (render), `VirtualScroll` (scroll behavior), `SaveButton` (interaction).

**`items/[id]/+page.svelte` (367 LOC)** — 4 API calls, craft calculator, inventory management, chart rendering. Powinien być rozbity na: data loading w `+page.ts`, komponenty per-section.

### 2.4 Duplikacja

| Co | Gdzie | Rozwiązanie |
|----|-------|-------------|
| `computeNodeCost()` | `items/[id]/+page.svelte:36-53`, `RecipeTree.svelte:19-33` | Przenieś do `$lib/crafting.ts` |
| `CATEGORIES` / `GRADES` | `ItemTable.svelte:34-43`, `inventory/+page.svelte:10-18` | Przenieś do `$lib/constants.ts` albo SDK types |
| Auth redirect (401 → `/auth`) | 3 różne komponenty | Centralizuj w API client |
| `margin` calculation | `+page.svelte:65-68` i `RecipeCard.svelte` | Przenieś do shared utility |

Dodatkowo: `_GRADES` w inventory zawiera "Basic", ale w ItemTable nie — niespójność w danych samej enumeracji. Powinno pochodzić z jednego źródła.

### 2.5 Modern SvelteKit 5 Gaps

| Pattern | Problem | Rekomendacja |
|---------|---------|--------------|
| `onMount` async init | `ItemTable.svelte:178`, `inventory/+page.svelte:95` | Przenieś do `+page.ts` load |
| `loadHotItems()` poza lifecycle | `+page.svelte:23` — side-effect przy każdym render | Użyj `$effect` albo load function |
| `{#each}` bez keyed | `+page.svelte:84` | Dodaj `(item.id)` key |
| `@ts-nocheck` | `EChartsLineChart.svelte:2` | Override typów przez `.d.ts` zamiast wyłączać checking |
| `(row: any)` | `items/[id]/+page.svelte:124` | Użyj typu z `api.d.ts` |
| `.js` import extension | `auth.svelte.ts:2` | Usuń `.js` — TypeScript resolution działa bez rozszerzenia |
| CSS variables vs JS | `layout.css` definiuje `--grade-*`, ale kod używa `gradeColor()` z JS | Wybierz jedno — preferuj CSS variables |
| Timer leaks | `searchTimeout` w ItemTable, `debounceTimers` w inventory, `setTimeout` w settings | Użyj `$effect` z cleanup albo utility функцji |

### 2.6 Security — Frontend

| Issue | Severity | Detail |
|-------|----------|--------|
| **Brak CSRF protection** | **HIGH** | Cookie-based auth bez CSRF token = vulnerability na state-changing requests (follow, unfollow, inventory, register) |
| Brak CSP headers | MEDIUM | Caddy nie ustawia Content-Security-Policy |
| `response.json()` bez typing | LOW | Brak runtime validation API response |

### 2.7 State Management

**Auth state** (`auth.svelte.ts`) — global singleton z `$state` — działa poprawnie z Svelte 5 runes.

**Page state** — każdy komponent zarządza swoim stanem lokalnie. Brak client-side cache. Navigacja do `/items` powoduje pełny re-fetch każdego razu. Brak sharing między routes.

**Inventory state** — trzymany na detail page, nie synchronizuje z inventory na listach.

**Rekomendacja:** Oddzielny API cache layer (najprościej: `Map<string, {data, timestamp}>` albo軽ki store) z TTL, żeby nawigacja back nie triggerowała re-fetch.

---

## 3. Infrastructure — Security & Operability

### 3.1 Container Security

| Issue | Severity | Detail |
|-------|----------|--------|
| **All 3 Dockerfiles run as root** | **CRITICAL** | Brak `USER` directive w backend, frontend, i discord_bot Dockerfile |
| **Brak `.dockerignore`** | **HIGH** | `COPY . .` w frontend Dockerfile kopiuje `.git`, `.env`, etc. |
| `libpq-dev` w runtime image | MEDIUM | Backend Dockerfile instaluje dev package i nie czyści. Multi-stage albo `libpq5` w runtime |

### 3.2 Caddy Configuration

| Issue | Severity | Detail |
|-------|----------|--------|
| **Brak security headers** | **HIGH** | HSTS, X-Content-Type-Options, X-Frame-Options, CSP — wszystkie missing |
| **`/docs`, `/redoc`, `/openapi.json` exposed** | **HIGH** | API documentation dostępne bez auth w prod |
| `/admin*` matches too broadly | MEDIUM | `/administrator` też by match. Powinno być `/admin/*` albo specific subpaths |
| Brak compression | LOW | Caddy może `encode gzip zstd` |
| Brak logging config | LOW | Default stderr tylko |

### 3.3 CI/CD

**Co jest:** 4 workflows (backend, frontend, discord_bot, docker).

**Problemy:**

1. **discord_bot.yml** — triggers na ALL branches (brak `branches:` filter). Każdy push na jakikolwiek branch odpala CI.
2. **docker.yml** — nie buduje discord_bot Dockerfile.
3. **Brak CD pipeline** — żadnego deployment automation.
4. **Brak security scanning** — no pip-audit, npm audit, albo container scanning.
5. **Brak coverage reporting**.
6. **Frontend CI** — tylko `svelte-check`, brak lint i unit testów.
7. **Alembic CI job** — hardcoded secrets w pipeline (`AUTH_SECRET: ci-secret-minimum-32-characters-long`). Działa, ale innekspresywne.

### 3.4 Discord Bot

**Dobre:** Cog architecture, async, type hints, thorough testing (21 testów).

**Problemy:**

1. **Nowy HTTP client per request** — `httpx.AsyncClient()` tworzony per-call. Powinien być shared z connection pooling.
2. **`format_price` duplikuje `formatCurrency`** — CLAUDE.md mówi "nigdy nie redefiniuj". Shared package albo import z frontend lib.
3. **`GRADE_CHOICES` hardcoded** — ryzyko desync z backend enums.
4. **Brak global error handler** — `on_app_command_error` nie zdefiniowany. Nieobsłużone exception = "interaction failed".
5. **`logging.basicConfig()`** — konfiguruje root logger globalnie, affects httpx i discord loggery.
6. **`command_prefix="!"`** — ustawiony ale nieużywany (tylko slash commands).

### 3.5 Secrets Management

| Secret | W .env.example? | W compose? | Problem |
|--------|----------------|------------|---------|
| `POSTGRES_PASSWORD` | Tak (`postgres`) | Dev: default, Prod: required | Dev default jest słaby |
| `AUTH_SECRET` | Tak (hardcoded) | Dev: default, Prod: required | Default "works" — nie failuje |
| `ADMIN_SESSION_SECRET` | Tak (hardcoded) | Dev: default, Prod: required | Tak samo |
| `DISCORD_TOKEN` | **Nie** | **Nie** | Brak template w .env.example |
| `DISCORD_GUILD_ID` | **Nie** | **Nie** | Brak template w .env.example |

### 3.6 Health Checks & Monitoring

| Service | Healthcheck | Problem |
|---------|-------------|---------|
| db | `pg_isready` | OK |
| backend | **Brak** | Żaden healthcheck endpoint ani compose healthcheck |
| frontend | **Brak** | |
| caddy | **Brak** | |
| discord_bot | **Brak** (nie w compose) | |

Backend powinien mieć `/healthz` endpoint i compose healthcheck.

---

## 4. Cross-Cutting — Patterns, Consistency, Modern Stack

### 4.1 Type Safety Across the Stack

| Layer | Issue |
|-------|-------|
| Backend | Dobre — SQLModel, Pydantic v2, type hints wszędzie. Ale `type: ignore` w 2 miejscach i brak `Annotated` pattern. |
| Frontend | Słabe — `api.d.ts` generowany ale nieużywany do typed fetch, `any` w chart mapping, `@ts-nocheck` w ECharts. |
| Discord bot | OK — type hints obecne, ale nie ma shared types z backend. |
| **Gap** | **Brak shared type contract** między backend i frontend. OpenAPI types są generowane ale fetch nie używa ich do request/response typing. |

### 4.2 Error Handling Patterns

| Layer | Pattern | Problem |
|-------|---------|---------|
| Backend | Services rzucają `HTTPException` z `detail`. Ingest zwraca partial success z `errors[]`. | Inconsystentne — inne endpointy nie mają structured error response. |
| Frontend | Każdy komponent łapie catch sam. `auth.svelte.ts` rzuca na network error. Brak global error boundary. | Brak centralnego error handling — toast/notification system nie istnieje. |
| Bot | Catches `httpx.HTTPError` i `ValueError`. Brak global handler. | Działa, ale fragile na nowe error types. |

### 4.3 Time Handling

**Constitution mówi:** "Naive UTC wszędzie." Backend to respektuje. Ale:

- Frontend nie formatuje timestamps — brak evidence że timezone handling jest consistent.
- Discord bot nie formatuje timestamps w user-facing messages.
- Brak utility do konwersji UTC→local w frontend.

### 4.4 Dead Code & Orphaned Files

| Plik | Status |
|------|--------|
| `mockData.ts` (frontend) | Martwy — w roadmpa jako "do cleanup" |
| `InventoryModal.svelte` | Komponent bez importera |
| `lib/index.ts` | Pusty barrel file — nikt nie importuje z `$lib/index` |
| `aiosqlite` (backend) | Zależność bez użycia — relikt z early dev |
| `favicon.svg` | Domyślne logo Svelte — niecustomize'owane |
| `command_prefix="!"` (bot) | Ustawiony ale nieużywany |

---

## 5. Strategic Roadmap — Phased Remediation

### Phase 1: Security & Fundamentals (1-2 dni)

| # | Akcja | Effort |
|---|-------|--------|
| 1.1 | Dodaj auth do ingest endpoint (API key albo rate-limit + signed payload) | 2h |
| 1.2 | Dodaj rate limiting na `/auth/register` i `/auth/login` | 1h |
| 1.3 | Caddy: security headers (HSTS, X-Content-Type-Options, X-Frame-Options, CSP) | 1h |
| 1.4 | Caddy: ogranicz `/docs`, `/redoc`, `/openapi.json` do auth albo wyłącz w prod | 30min |
| 1.5 | Dockerfiles: dodaj `USER` directive (non-root) dla backend, frontend, discord_bot | 2h |
| 1.6 | Dockerfiles: dodaj `.dockerignore` | 30min |
| 1.7 | Settings: fail loudly w prod jeśli `AUTH_SECRET` i `ADMIN_SESSION_SECRET` nie są ustawione | 30min |
| 1.8 | `cookie_secure=True` w prod — env var albo assert | 30min |

### Phase 2: Architecture Cleanup (3-5 dni)

| # | Akcja | Effort |
|---|-------|--------|
| 2.1 | Frontend: stwórz API client layer (`src/lib/api.ts`) — typed fetch, central 401 handling, error typing | 4h |
| 2.2 | Frontend: dodaj `+page.ts` load functions — przenieś fetch z onMount do load | 6h |
| 2.3 | Frontend: wydziel `ItemTable` na mniejsze komponenty (data fetching, list, virtual scroll, save action) | 4h |
| 2.4 | Frontend: wydziel `items/[id]` — data loading do load, sekcje do komponentów | 4h |
| 2.5 | Frontend: przenieś duplikacje — `computeNodeCost` → `$lib/crafting.ts`, `CATEGORIES/GRADES` → `$lib/constants.ts` | 2h |
| 2.6 | Backend: wydziel `utcnow()` do `app/utils.py` albo bazowej klasy modelu | 1h |
| 2.7 | Backend: ujednolicony commit pattern w services — standard (service does unit of work, router commits, albo każdy service jest atomic z wyraźnym boundary) | 3h |
| 2.8 | Backend: dodaj `from_attributes=True` do wszystkich Read schemas | 2h |
| 2.9 | Backend: decouple auth→profiles — post-registration hook zamiast direct import | 2h |

### Phase 3: Modern Stack Gains (2-3 dni)

| # | Akcja | Effort |
|---|-------|--------|
| 3.1 | Backend: `Annotated` pattern dla FastAPI dependencies (skróci router boilerplate) | 2h |
| 3.2 | Backend: `match` statements w `Interval` validation, `grade_map.py`, `ItemCategory` | 2h |
| 3.3 | Frontend: usuń `@ts-nocheck` z ECharts — stwórz `.d.ts` override | 1h |
| 3.4 | Frontend: usuń `(row: any)` — użyj typów z `api.d.ts` | 1h |
| 3.5 | Frontend: Svelte 5 cleanup — timer leaks (searchTimeout, debounce), `loadHotItems` poza lifecycle, unkeyed `{#each}` | 3h |
| 3.6 | Discord bot: shared `httpx.AsyncClient` z connection pooling | 1h |
| 3.7 | Discord bot: dodaj `on_app_command_error` global handler | 1h |
| 3.8 | Shared types: rozważ generowanie typed API client z OpenAPI (openapi-fetch albo openapi-typescript) | 4h |

### Phase 4: Operations & Observability (1-2 dni)

| # | Akcja | Effort |
|---|-------|--------|
| 4.1 | Backend: dodaj `/healthz` endpoint | 30min |
| 4.2 | Compose: healthchecks dla backend, frontend, caddy | 1h |
| 4.3 | Compose: dodaj discord_bot service (dev i prod) | 1h |
| 4.4 | CI: dodaj `branches:` filter do discord_bot.yml | 15min |
| 4.5 | CI: dodaj lint step do frontend.yml (eslint/prettier albo oxlint) | 1h |
| 4.6 | CI: dodaj discord_bot Dockerfile do docker.yml | 30min |
| 4.7 | Makefile: dodaj `lint`, `typecheck`, `bot-up`, `bot-down` targets | 1h |
| 4.8 | .env.example: dodaj `DISCORD_TOKEN` i `DISCORD_GUILD_ID` template | 15min |
| 4.9 | Dead code cleanup: mockData.ts, InventoryModal, aiosqlite, empty index.ts | 1h |

---

## 6. What's Working Well

Ważne jest dokumentować co działa dobrze — nie tylko co trzeba naprawić:

| Area | Co działa | Dlaczego |
|------|----------|---------|
| Module boundaries | Każdy moduł ma models→schemas→services→router | Przewidywalna struktura, łatwo nawigować |
| Integration tests | Real PG, UUID suffix isolation, httpx client | Nie ma mocków które ukrywają bugi |
| Svelte 5 runes | `$state`, `$derived`, `$derived.by`, `$props()` | Poprawne użycie nowych mechanizmów |
| API type generation | `openapi-typescript` → `api.d.ts` | Single source of truth dla API types |
| Ingest partial success | Constitution-defined, implemented correctly | Robust pattern dla bulk ingestion |
| Recipe calculator | Pure function, tested separately | Clean separation od DB logic |
| Caddy + Podman | TLS auto-provisioning, compose-based dev/prod | Prosta infra bez Kubernetes |
| Discord bot | Cog pattern, async, 21 tests | Clean architecture dla bota |
| Constitution docs | `CLAUDE.md`, `architecture.md`, `patterns.md`, `constitution.md` | Jasne zasady które zapobiegają regression |
| UserInventory upsert | Atomic ON CONFLICT / DELETE | Correct concurrency pattern |

---

## Appendix A: Finding Severity Matrix

| ID | Severity | Area | Finding |
|----|----------|------|---------|
| S1 | CRITICAL | Security | Ingest endpoint bez auth |
| S2 | HIGH | Architecture | Frontend 100% CSR, brak SSR/load functions |
| S3 | HIGH | Security | Containers run as root |
| S4 | HIGH | Security | Caddy brak security headers + exposed docs |
| S5 | HIGH | Architecture | Brak API client layer |
| S6 | HIGH | Security | Brak CSRF protection (cookie auth bez CSRF) |
| S7 | HIGH | Security | Brak rate limiting na auth endpoints |
| S8 | MEDIUM | Architecture | God components (ItemTable 349 LOC, items/[id] 367 LOC) |
| S9 | MEDIUM | Quality | Duplications: computeNodeCost, CATEGORIES/GRADES, auth redirect |
| S10 | MEDIUM | Quality | `utcnow()` duplicated 5x |
| S11 | MEDIUM | Quality | Inconsistent commit patterns w services |
| S12 | MEDIUM | Quality | ORM→schema mapping inconsistent (manual vs from_attributes) |
| S13 | MEDIUM | Architecture | auth→profiles coupling |
| S14 | MEDIUM | Performance | Price history bucketing w Python (nie SQL) |
| S15 | MEDIUM | Performance | Crafting calculator no cache |
| S16 | MEDIUM | Modern | Python 3.13 unused features (match, Annotated, TypeGuard) |
| S17 | MEDIUM | Modern | `@ts-nocheck`, `any` type, `.js` import extension |
| S18 | MEDIUM | Security | Default secrets pass validation — should fail in prod |
| S19 | MEDIUM | Security | `cookie_secure` defaults to False |
| S20 | MEDIUM | Config | CORS too permissive (`allow_methods=["*"]`) |
| S21 | MEDIUM | Ops | Discord bot nie w compose |
| S22 | MEDIUM | Ops | Brak healthchecks na backend, frontend, caddy |
| S23 | MEDIUM | Quality | Bot: httpx client per request, format_price duplication |
| S24 | MEDIUM | Quality | Test fixtures duplicated 6+ |
| S25 | LOW | Consistency | UserInventory brak timestamps, Recipe brak timestamps |
| S26 | LOW | Consistency | GRADES niespójne (Basic vs nie) |
| S27 | LOW | Quality | `print()` w UserManager zamiast `logging` |
| S28 | LOW | Quality | `str(None)` w admin_auth |
| S29 | LOW | Quality | CSS variables vs JS gradeColor niespójność |
| S30 | LOW | Quality | Dead code: mockData.ts, InventoryModal, empty index.ts, aiosqlite |
| S31 | LOW | Accessibility | Brak ARIA labels, skip-nav, focus management |
| S32 | LOW | Ops | Brak `.dockerignore`, brak resource limits, brak DB backup |
| S33 | LOW | Ops | CI: brak coverage, brak security scanning, frontend brak lint |
| S34 | LOW | Ops | Makefile: hardcoded `podman`, brak lint/bot targets |

---

## Appendix B: LOC Summary

| Warstwa | Pliki | LOC (approx) |
|---------|-------|--------------|
| Backend app | 38 | ~1,760 |
| Backend tests | 10 | ~1,825 |
| Backend migrations | 5 | ~372 |
| Backend seed | 1 | 286 |
| Frontend src | 20 | ~2,029 |
| Frontend api.d.ts (auto) | 1 | ~1,617 |
| Discord bot | 3 | ~276 |
| Discord bot tests | 1 | ~462 |
| Infra (compose, Caddy, Makefile) | 5 | ~230 |
| **Total (excl. auto-generated)** | **~78** | **~6,840** |