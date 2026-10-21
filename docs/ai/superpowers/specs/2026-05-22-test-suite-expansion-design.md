# Test Suite Expansion — Design Spec

**Status:** draft
**Author:** brainstorming session, 2026-05-22
**Scope:** this document is a **specification** of *what* tests to add and *why*. Implementation plan (file-by-file ordering, fixture wiring, CI yaml) will be written separately.

---

## 1. Cel i filozofia

Wypełniamy luki w piramidzie testów ArcheRage Market Tracker:

1. **Backend** ma dobre pokrycie domen (109 testów w 18 plikach), ale brakuje rate-limitera, admin endpoints i ścieżek wyścigowych poza `prices`.
2. **Frontend** ma testy jednostkowe tylko dla 3 modułów (`auth`, `crafting`, `currency`) — komponenty Svelte 5 i route `+page.svelte` nie są w ogóle dotknięte.
3. **E2E nie istnieje** — żaden user journey nie jest weryfikowany end-to-end przez prawdziwy stack.

Zasady projektowe (z `docs/ai/patterns.md` i `CLAUDE.md`):

- **Bez mocków DB w backendzie.** Wszystkie testy biją w PostgreSQL `app_test` (historia: mocki ukryły błąd migracji).
- **UUID-suffix** w nazwach itemów i e-mailach — DB nie jest czyszczona między testami.
- **Reset rate-limitera** per-test (już wpięte w `conftest.py` jako autouse).
- **Naive UTC** w DB — testy też muszą strip-ować `tzinfo`.
- **`session.rollback()`** po każdej zamierzonej awarii batcha.

**Out of scope (świadomie):**

- Accessibility (axe-playwright) — odłożone do osobnego spec.
- Visual regression / screenshot diffing — flakiness > value przy tym etapie projektu.
- Load testing / k6 — domena hobbystyczna, ruch < 100 req/s.

---

## 2. Test pyramid — overview

| Warstwa | Tool | Nowe testy | Runtime target | Lokalizacja |
|---|---|---|---|---|
| Backend unit/integration | pytest + real PG | **28** | <30 s | `backend/tests/` |
| Frontend component | vitest + @testing-library/svelte | **38** | <15 s | `frontend/src/lib/**/*.test.ts` + `frontend/src/routes/**/*.test.ts` |
| E2E | Playwright + podman compose | **20** | <3 min | `e2e/` (nowy katalog w repo root) |
| **Suma nowych** | | **86** | | |

Po wdrożeniu spec:
- backend: 109 → **137** testów
- frontend unit: 3 plików (~38 testów) → **41+ plików** (rozszerzenia istniejących + nowe)
- e2e: 0 → **20** testów

---

## 3. Backend — nowe testy (28)

### 3.1 `test_rate_limit_ingest.py` (5 testów)

slowapi limiter jest singletonem (`app/config/rate_limit.py`). Dziś nie ma żadnego testu który by potwierdzał, że `@limiter.limit()` faktycznie odrzuca nadmiarowe requesty. Roadmap wprost wskazuje to jako lukę.

| # | Test | Scenariusz | Asercje |
|---|---|---|---|
| 1 | `test_login_returns_429_after_burst` | 6 prób loginu w 1s | szósta zwraca 429, header `Retry-After` obecny |
| 2 | `test_register_rate_limited_per_ip` | 11 rejestracji z różnymi e-mailami z tego samego IP | 11. zwraca 429 |
| 3 | `test_ingest_returns_429_above_threshold` | flood na `/api/ingest/prices` | 429 po przekroczeniu limitu |
| 4 | `test_limiter_resets_between_tests` | dwa zestawy 6 loginów w osobnych testach | drugi nie dziedziczy stanu (regression dla autouse fixture) |
| 5 | `test_429_payload_shape` | wymuś 429 | body zawiera `error` lub `detail`, nie 500/HTML |

**Edge cases:**
- Limiter musi działać per-IP, nie globalnie (X-Forwarded-For respektowany).
- Reset między testami (już mamy w conftest) — test 4 to regression guard.

---

### 3.2 `test_admin_users.py` (7 testów)

Endpoint `/users/{id}` (PATCH/DELETE z fastapi-users) i `/admin` (sqladmin) nie mają żadnego testu. To znaczne ryzyko bo zarządzanie userami jest atak-vector.

| # | Test | Asercje |
|---|---|---|
| 1 | `test_get_user_by_id_as_superuser` | 200, body zgodne ze schematem |
| 2 | `test_get_user_by_id_as_regular_user_forbidden` | 403 |
| 3 | `test_get_user_by_id_unauthenticated` | 401 |
| 4 | `test_patch_user_as_superuser_can_promote` | `is_superuser=true` po PATCH |
| 5 | `test_patch_user_self_cannot_promote` | regular user nie może podnieść swoich uprawnień |
| 6 | `test_delete_user_as_superuser` | 204, user usunięty z DB |
| 7 | `test_admin_panel_redirects_unauth_to_login` | GET `/admin` bez sesji → 302/401 (sqladmin) |

**Edge cases:**
- `PATCH` z polem nieobecnym w `UserUpdate` schemacie — ignorowany (Pydantic strict).
- DELETE samego siebie jako superuser — wymóg projektowy: zostawiamy działanie fastapi-users domyślne, dokumentujemy zachowanie.

---

### 3.3 `test_user_items_race.py` (3 testy)

Wzorowane na istniejącym `test_prices_race.py`. Follow/unfollow ma `UniqueConstraint(user_id, item_id)` — możliwy duplicate na concurrent POST.

| # | Test | Scenariusz |
|---|---|---|
| 1 | `test_concurrent_follow_same_item_no_duplicate` | 5 jednoczesnych POST `/api/user-items/{item_id}` z jednej sesji | jeden 201, reszta 200/409 idempotent, w DB **jeden** wiersz |
| 2 | `test_follow_then_unfollow_then_follow_idempotent` | sekwencja POST→DELETE→POST | końcowy stan: 1 wiersz, brak orphanów |
| 3 | `test_unfollow_non_existent_returns_404_not_500` | DELETE nieobserwowanego itemu | 404, brak 500 / poisoned session |

**Edge cases:**
- IntegrityError przy duplicate → musi być przechwycony, nie propagowany jako 500.
- Concurrency tester używa `asyncio.gather` + multiple `AsyncSession` z tego samego `session_factory`.

---

### 3.4 `test_user_inventory_race.py` (4 testy)

`UserInventory` używa `ON CONFLICT DO UPDATE` przy upsert i bezpośredniego DELETE przy `quantity=0`. Krytyczny invariant: **nigdy SELECT-then-delete**.

| # | Test | Scenariusz |
|---|---|---|
| 1 | `test_concurrent_upsert_same_item_final_quantity_correct` | 10 równoległych PUT `quantity=N` (różne wartości) | końcowa wartość = ostatnia zapisana, brak duplikatów |
| 2 | `test_concurrent_set_to_zero_deletes_exactly_once` | 5 równoległych PUT `quantity=0` na ten sam wiersz | tylko jeden DELETE, brak 500 |
| 3 | `test_upsert_then_delete_race_no_orphan` | PUT `quantity=5` i PUT `quantity=0` jednocześnie | finalny stan deterministyczny (jedno z dwóch), brak crash |
| 4 | `test_for_recipe_endpoint_consistent_under_writes` | PUT-y + równolegle `GET /api/inventory/for-recipe/{id}` | GET nigdy nie zwraca 500, payload zawsze zgodny ze schematem |

**Edge cases:**
- `quantity` przekraczający Postgres `BIGINT` max — test 1 powinien używać sane upper bound; przepełnienie to osobny check w `test_inventory_edge.py`.
- DELETE-then-UPDATE: SQL `ON CONFLICT` nie odpali bo wiersz zniknął — endpoint musi to obsłużyć (insert nowego wiersza lub no-op).

---

### 3.5 `test_inventory_edge.py` (5 testów)

Istniejący `test_inventory.py` (17 testów) skupia się na happy path. Dokładamy edge cases.

| # | Test | Edge case |
|---|---|---|
| 1 | `test_quantity_negative_rejected` | PUT `quantity=-1` → 422 (Pydantic ge=0) |
| 2 | `test_quantity_overflow_rejected` | PUT `quantity=2**63` → 422 (poza BIGINT) |
| 3 | `test_inventory_for_unknown_item_returns_404` | PUT na `item_id` nieistniejącego → 404, nie 500 |
| 4 | `test_inventory_cross_user_isolation` | userA nie widzi inventory userB; GET `/api/inventory/` zwraca tylko własne |
| 5 | `test_inventory_zero_quantity_idempotent_delete` | PUT `quantity=0` dwukrotnie → 204 oba razy, brak crash przy 2. wywołaniu |

---

### 3.6 `test_calculator_depth.py` (4 testy)

`calculator.py` ma recursive `compute_recipe_profit`. Dziś `test_crafting_calculator.py` testuje shallow recipes (1-2 poziomy). Brakuje testów głębi i cykli.

| # | Test | Scenariusz |
|---|---|---|
| 1 | `test_recipe_depth_3_levels_profit_correct` | A wymaga B, B wymaga C, C to leaf | profit obliczony rekurencyjnie poprawnie |
| 2 | `test_recipe_cycle_does_not_infinite_loop` | A → B → A (utworzone przez `item_with_broken_recipe`-style FK bypass) | calculator zwraca błąd / sentinel, NIE wisi |
| 3 | `test_missing_ingredient_recipe_returns_partial_cost` | recipe odwołuje się do nieistniejącego ingredient_item_id (fixture `item_with_broken_recipe`) | `total_material_cost` = NULL / sentinel, profit oznaczony jako niekompletny |
| 4 | `test_batch_profit_formula_with_multiplier` | recipe z `output_qty=5`, multiplier=2 | `batch_profit = (market_price * 5 * 2) − total_material_cost` — regression dla critical invariantu z `docs/ai/architecture.md` |

**Edge cases:**
- Cykl recipe to teoretycznie niemożliwy w UI, ale FK bypass w testach jest realny — recursion guard MUST być w kodzie produkcyjnym (jeśli nie jest, test 2 fail-uje i ujawnia braki).
- `output_qty=0` → division by zero w niektórych branchach. Test poboczny: walidacja schemy.

---

## 4. Frontend — component & route testy (38)

Stack: vitest 4 + @testing-library/svelte 5 + jsdom 29 (już w `package.json`).

Konwencja: testy obok komponentu, sufiks `.test.ts`. Dla route components — `+page.svelte.test.ts` w tym samym katalogu co route.

### 4.1 `ItemTable.svelte` (6 testów)

Komponent ma znany historyczny bug: lokalna kopia `splitCurrency` (patrz `patterns.md`). Spec wymusza testowanie wyświetlania ceny przez shared `formatCurrency`.

| # | Test |
|---|---|
| 1 | `renders rows from props` |
| 2 | `formatCurrency comes from shared lib (regression for lokalnej kopii)` |
| 3 | `empty items array shows empty-state placeholder` |
| 4 | `clicking row navigates to /items/[id]` (mock `goto`) |
| 5 | `displays grade pill with correct color for each grade` (uses `lib/grades.ts`) |
| 6 | `handles null current_price gracefully (no NaN visible)` |

**Edge cases:** `current_price=null`, `current_price=0`, bardzo duża liczba (>1e9).

---

### 4.2 `RecipeCard.svelte` (4 testy)

| # | Test |
|---|---|
| 1 | `displays profit hero with correct sign (positive green, negative red)` |
| 2 | `batch_profit interpreted as total (not per craft) — regression for architecture.md invariant` |
| 3 | `NaN / undefined profit shows "—" not "NaN"` |
| 4 | `expand/collapse chevron toggles details section` |

---

### 4.3 `RecipeTree.svelte` (8 testów)

Najbardziej złożony komponent. Inline edycja Have, Total Labour footer, recursive render.

| # | Test |
|---|---|
| 1 | `renders root node with output_qty` |
| 2 | `renders child ingredients recursively` |
| 3 | `Have column input updates parent state ($state) — derived totals recompute` |
| 4 | `Total Labour footer sums all non-leaf labour values` |
| 5 | `LABOUR_ITEM_NAME comes from shared lib (no local redefinition)` |
| 6 | `missing recipe (leaf with no children) shows "buy" badge` |
| 7 | `cycle in recipe data (programmatic) renders sentinel, does not stack-overflow` |
| 8 | `clicking ingredient name navigates to that item's page` |

**Edge cases:**
- Recipe z `output_qty=0` → komponent nie powinien wybuchnąć (UI safe-guard).
- Have > required → multiplier=1, Total Labour=0 dla tej gałęzi.

---

### 4.4 `EChartsLineChart.svelte` (3 testy)

ECharts to canvas — testy są ograniczone (jsdom nie ma canvas). Skupiamy się na lifecycle i props plumbing.

| # | Test |
|---|---|
| 1 | `mounts without throwing when given valid data array` |
| 2 | `re-renders when interval prop changes (raw → 5m → 1h → 1d)` |
| 3 | `disposes ECharts instance on unmount (no memory leak)` |

**Edge cases:** pusta `data=[]` (chart nie crashuje, pokazuje "no data"), `interval` poza enumem.

---

### 4.5 Route smoke + interaction testy (8)

Per route file — minimalny smoke + jedna interakcja per strona:

| # | Plik | Test |
|---|---|---|
| 1 | `routes/auth/+page.svelte.test.ts` | login form submit → wywołanie `/api/auth/login` z `credentials:'include'` |
| 2 | `routes/auth/+page.svelte.test.ts` | bad credentials → komunikat błędu (nie crash) |
| 3 | `routes/items/+page.svelte.test.ts` | renderuje ItemTable, search input filtruje |
| 4 | `routes/items/[id]/+page.svelte.test.ts` | renderuje RecipeCard + EChartsLineChart |
| 5 | `routes/saved-items/+page.svelte.test.ts` | gdy `user=null` — fetch nie strzela, pokazuje login CTA |
| 6 | `routes/saved-items/+page.svelte.test.ts` | unfollow button usuwa item z listy bez reload |
| 7 | `routes/inventory/+page.svelte.test.ts` | edycja quantity wysyła PUT |
| 8 | `routes/settings/+page.svelte.test.ts` | edycja `display_name` + `is_private` toggle wysyła PATCH |

**Edge cases:** wszystkie strony testowane też w stanie `user=null` (poprawny redirect / CTA, brak crash).

---

### 4.6 Rozszerzenia istniejących plików (9 testów)

| Plik | Dodatkowe testy |
|---|---|
| `lib/currency.test.ts` | NaN, Infinity, ujemna cena, bardzo duża liczba (>2^53), zaokrąglanie groszy |
| `lib/crafting.test.ts` | LABOUR_ITEM_NAME constant, multiplier edge cases (0, ujemny, ułamkowy), recursive depth limit |
| `lib/auth.svelte.test.ts` | logout czyści `$state user` natychmiast, 401 odpowiedź resetuje sesję, concurrent login attempts nie tworzą dwóch userów |

(3 testy na plik = 9 łącznie)

---

## 5. E2E — Playwright (20)

### 5.1 Setup

- **Nowy katalog `e2e/`** w root repo (poza `frontend/`, żeby nie ciągnąć vitest configu).
- **`playwright.config.ts`**: browser=chromium (single, do rozszerzenia później), `webServer` nie używamy — zakładamy że `make dev-up` już wstał (lokalnie) lub osobny target `make e2e-up` w CI.
- **Test database:** osobna baza `app_e2e` (nie `app_test`, żeby nie kolidować z pytest). Migracje przez `alembic upgrade head`. Seed: minimalny zestaw 3 itemów + 1 recipe (lekka wersja `seed.py`).
- **Auth fixture:** `e2e/fixtures.ts` — pre-utworzony test user, login via `request.context()` (storage state cached między testami).
- **Cleanup:** każdy test używa UUID-suffix dla danych które tworzy (item names, e-mail rejestracji).

### 5.2 `auth.spec.ts` (5 testów)

| # | Test |
|---|---|
| 1 | `register new user → redirected to items list` |
| 2 | `login existing user → cookie set → items page accessible` |
| 3 | `login with bad password → error visible, no cookie` |
| 4 | `logout clears session → /saved-items redirects to /auth` |
| 5 | `settings page: change display_name → reload → value persisted` |

### 5.3 `items.spec.ts` (3 testy)

| # | Test |
|---|---|
| 1 | `items list paginates correctly (next/prev buttons)` |
| 2 | `search filters items case-insensitively` |
| 3 | `item detail page: ECharts canvas renders, interval switcher works (raw → 1d)` |

### 5.4 `saved-items.spec.ts` (2 testy)

| # | Test |
|---|---|
| 1 | `follow item from list → appears on /saved-items` |
| 2 | `unfollow from /saved-items → disappears without reload` |

### 5.5 `crafting-inventory.spec.ts` (7 testów)

Najbardziej rozbudowany journey — kalkulator profitu + integracja z inventory.

| # | Test |
|---|---|
| 1 | `open item with recipe → RecipeTree visible` |
| 2 | `expand/collapse ingredient nodes` |
| 3 | `edit Have column → Total Labour footer updates live` |
| 4 | `Have value persists after navigating away and back (via /inventory PUT)` |
| 5 | `set quantity=0 in /inventory → row removed` |
| 6 | `crafting profit changes when underlying current_price updates` (post `/api/ingest/prices` via fixture, page reload) |
| 7 | `recipe tree handles 3-level depth without rendering glitches` |

### 5.6 `cross-cutting.spec.ts` (3 testy)

| # | Test |
|---|---|
| 1 | `rate limit user-facing: rapid login attempts → friendly error, not 429 raw` |
| 2 | `network failure during PUT inventory → optimistic UI rolls back, error toast shown` |
| 3 | `unauthenticated user opens /inventory → redirected to /auth` |

**Edge cases dla całego e2e:**

- Slow network (Playwright `route.continue({ delay })`) — przynajmniej jeden test musi przeżyć 2s opóźnienie.
- Session expiry mid-action (cookie expired) — operacja zwraca 401, UI redirectuje.
- Backend down (wszystkie API zwracają 503) — żaden test tego nie testuje w MVP, ale notatka: do późniejszego dodania.

---

## 6. Edge cases catalog

Skondensowana tabela pokrycia — pomaga zweryfikować że nie zostawiamy lukę.

| Edge case | Backend | Frontend component | E2E |
|---|---|---|---|
| `current_price = null` | items list query | ItemTable test #6, RecipeCard #3 | items.spec.ts #1 (lista renderuje) |
| `current_price = NaN` (corruption) | — | RecipeCard #3 | — |
| `quantity = 0` (inventory delete) | inventory_edge #5 | route inventory test | crafting-inventory #5 |
| `quantity < 0` | inventory_edge #1 | — | — |
| `quantity > BIGINT max` | inventory_edge #2 | — | — |
| Concurrent upsert same row | user_inventory_race #1-4 | — | — |
| Concurrent follow same item | user_items_race #1 | — | — |
| Rate limit hit (429) | rate_limit_ingest #1-5 | — | cross-cutting #1 |
| Cycle in recipe data | calculator_depth #2 | RecipeTree #7 | — |
| Recipe depth ≥ 3 | calculator_depth #1 | RecipeTree #2 | crafting-inventory #7 |
| Missing ingredient (broken FK) | calculator_depth #3 | RecipeTree #6 | — |
| Session expired / 401 | (covered by auth tests) | auth.svelte #2 | cross-cutting #3 |
| Unauthenticated PUT | inventory_edge (krzyżowo) | route saved-items #5 | cross-cutting #3 |
| Cross-user data leak | inventory_edge #4 | — | — |
| ECharts unmount memory leak | — | EChart #3 | — |
| `output_qty = 0` recipe | calculator_depth (poboczny) | RecipeTree (safe-guard) | — |
| Empty items list | — | ItemTable #3 | — |
| Privilege escalation via PATCH | admin_users #5 | — | — |
| Limiter state leakage between tests | rate_limit_ingest #4 | — | — |
| Slow network (e2e only) | — | — | (rozważ w jednym teście) |

---

## 7. CI integration (high-level)

**Decyzje do podjęcia w planie, ale spec zakłada:**

- **Backend pytest** — blocking gate na każdym PR. Runtime <30s pozwala uruchamiać w pre-commit hook lokalnie.
- **Frontend vitest** — blocking gate na każdym PR. Razem z `svelte-check` jako jedna komenda.
- **E2E Playwright** — początkowo **informational only** (PR widzi wynik, ale nie blokuje merge). Po 2-3 tygodniach stabilizacji → blocking. Powód: real-stack e2e są flake-prone w pierwszych tygodniach.
- **Parallelizacja:** pytest `-n auto` (xdist), vitest natywnie równolegle, Playwright `workers: 2` (więcej wymaga drugiej bazy `app_e2e_2`).
- **Runtime budget całego CI:** <8 min (backend ~1min, frontend ~30s, e2e ~3min, overhead ~3min).

---

## 8. Liczby i podsumowanie

| Warstwa | Pliki nowe | Pliki rozszerzone | Testy nowe |
|---|---|---|---|
| Backend | 6 | 0 | 28 |
| Frontend unit | 4 (komponenty) + 6 (routes) | 3 (currency, crafting, auth) | 38 |
| E2E | 5 + config + fixtures | 0 | 20 |
| **Suma** | **21 plików** | **3 pliki** | **86 testów** |

**Po wdrożeniu:**

- Backend: 109 → 137 testów
- Frontend: 3 pliki → 23 pliki testów
- E2E: 0 → 5 specs (20 testów)

---

## 9. Otwarte pytania (do rozstrzygnięcia w planie)

1. Czy `e2e/` ma być osobnym workspacem npm (`e2e/package.json`) czy częścią `frontend/`?
2. Seed dla e2e — replikujemy `seed.py` czy budujemy minimalny `e2e/fixtures/seed.ts`?
3. Czy backend race tests używają `pytest-asyncio` + `asyncio.gather`, czy oddzielnego `pytest-xdist` setupu?
4. Visual regression baseline — odłożone, ale gdzie trzymać screenshots gdy zdecydujemy się dodać? `e2e/__snapshots__/`?
5. Czy testy admin endpoints wymagają fixture `superuser` (analogiczne do `sample_user`) w `conftest.py`?

Te pytania **nie blokują** akceptacji spec — są inputem do planu implementacyjnego.
