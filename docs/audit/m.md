# ArcheRage Market Tracker — Kompleksowy Audyt

> Data: 2026-05-20 | Worktree: `audit-opencode-20260520-2222` | 12 subagentów, ~154 findings

---

## Spis treści
1. [TL;DR](#1-tldr)
2. [Krytyczne — natychmiastowa akcja](#2-krytyczne--natychmiastowa-akcja)
3. [Backend findings](#3-backend-findings)
4. [Frontend findings](#4-frontend-findings)
5. [Infra findings](#5-infra-findings)
6. [Discord Bot findings](#6-discord-bot-findings)
7. [Integration findings](#7-integration-findings)
8. [Security findings](#8-security-findings)
9. [Dependencies findings](#9-dependencies-findings)
10. [Code Quality findings](#10-code-quality-findings)
11. [Tester Evaluator findings](#11-tester-evaluator-findings)
12. [Skeptic findings](#12-skeptic-findings)
13. [Visionary findings](#13-visionary-findings)
14. [Second Opinion](#14-second-opinion)
15. [Wzorce powtarzające się](#15-wzorce-powtarzające-się)
16. [Konflikty opinii](#16-konflikty-opinii)
17. [Top 3 Quick Wins](#17-top-3-quick-wins)
18. [Long-term Roadmap](#18-long-term-roadmap)

---

## 1. TL;DR

1. 🔴 Discord token jawny w `.env` — zrewokować natychmiast
2. 🔴 Brak rate limitu na `/api/auth/login` i `/api/auth/register` — brute-force risk
3. 🔴 Ingest commituje per-row (brak atomowości batcha) — częściowe dane przy błędzie
4. 🔴 Price-history bez LIMIT (DoS risk) — 30 dni × 5m = ~8640 punktów
5. 🔴 `SecureAdminAuth` dead code — cookie bez Secure flag w produkcji
6. 🔴 Root w Dockerfile (backend, discord_bot) — container escape risk
7. 🔴 Testy omijają Alembic (`create_all` zamiast migracji) — migracje produkcyjne nie testowane
8. 🟠 `slowapi` 0.1.9 — nieaktualizowany od 2024, incompatibility z nowym Starlette
9. 🟠 Brak healthchecków dla backendu i frontendu — race conditions przy starcie
10. 🟠 Brak rollbacków przy błędach w upsertach (inventory, profiles, user_items)

---

## 2. Krytyczne — natychmiastowa akcja

| # | Finding | Lokalizacja | Akcja |
|---|---------|-------------|-------|
| 1 | Discord token w `.env` | `discord_bot/.env:23` | Zrewokować token, przenieść do secret managera |
| 2 | Brak rate limitu na auth | `backend/app/auth/router.py` | Dodać `@limiter.limit("10/minute")` |
| 3 | Ingest commit per-row | `backend/app/ingest/services.py` | Batch transaction, commit na końcu |
| 4 | Price-history bez LIMIT | `backend/app/prices/services.py` | Dodać max limit parametr |
| 5 | SecureAdminAuth dead code | `backend/app/admin_auth.py` | Usunąć, naprawić Secure flag |
| 6 | Root w Dockerfile | `backend/Dockerfile`, `discord_bot/Dockerfile` | Dodać `USER nonroot` |
| 7 | Testy bez Alembic | `backend/tests/conftest.py` | Użyć `alembic upgrade head` w testach |

---

## 3. Backend findings

### Podsumowanie
Backend jest w dobrym stanie — większość inwariantów z dokumentacji jest zachowana. Rate limiter singleton poprawnie skonfigurowany, ingest zwraca partial success. Wykryto brak rollbacków przy błędach, N+1 w crafting, niespójność w admin_auth.

### Findings

#### 🔴 Podwójna instancja authentication_backend w admin_auth.py
- **Lokalizacja:** `backend/app/admin_auth.py:46` i `backend/app/admin_auth.py:68`
- **Problem:** Plik tworzy `authentication_backend` dwukrotnie — najpierw jako `AdminAuth`, potem nadpisuje jako `SecureAdminAuth`. Pierwsza instancja jest martwym kodem.
- **Dlaczego to problem:** Niejasna intencja, potencjalne problemy z importem.
- **Sugestia:** Usunąć pierwszą definicję, zostawić tylko `SecureAdminAuth`.

#### 🟠 Brak rollbacków przy błędach w upsert_inventory
- **Lokalizacja:** `backend/app/user_inventory/services.py:38-64`
- **Problem:** `upsert_inventory` wykonuje `session.commit()` bez `session.rollback()` w przypadku wyjątku.
- **Dlaczego to problem:** Sesja pozostaje w stanie błędu — trucizna dla kolejnych operacji.
- **Sugestia:** Dodać `try/except` z `await session.rollback()`.

#### 🟠 Brak rollbacków w follow_item / unfollow_item
- **Lokalizacja:** `backend/app/user_items/services.py:65-94`
- **Problem:** Brak obsługi wyjątków z rollbackiem.
- **Sugestia:** Dodać `try/except` z rollbackiem.

#### 🟠 Brak rollbacków w profiles/services.py
- **Lokalizacja:** `backend/app/profiles/services.py:10-35`
- **Problem:** `get_or_create_profile` i `update_profile` bez obsługi wyjątków.
- **Sugestia:** Dodać try/except z rollbackiem.

#### 🟡 Brak walidacji `source` w PricePointCreate
- **Lokalizacja:** `backend/app/prices/schemas.py:22-25`
- **Problem:** Schema pozwala na dowolny `source` — brak enum `PriceSource`.
- **Sugestia:** Dodać `Literal['ah']` lub enum do pola `source`.

#### 🟡 Brak rate limitu na endpointach crafting i inventory
- **Lokalizacja:** `backend/app/crafting/router.py`, `backend/app/user_inventory/router.py`
- **Problem:** Endpointy bez dekoratorów `@limiter.limit()`.
- **Sugestia:** Dodać `@limiter.limit("60/minute")`.

#### 🟡 Ingest — match_or_create_item commituje przed add_price_point
- **Lokalizacja:** `backend/app/ingest/services.py:20-57`
- **Problem:** Item tworzony jest w osobnej transakcji — może powstać osierocony item bez price point.
- **Sugestia:** Dodać komentarz wyjaśniający celowy design.

---

## 4. Frontend findings

### Podsumowanie
Frontend poprawnie używa `credentials: 'include'`, typy z `api.d.ts` są konsekwentnie re-eksportowane. Wykryto potencjalny wyciek stanu, brak credentials na home page, `@ts-nocheck` w chart.

### Findings

#### 🟠 Potencjalny wyciek stanu poza `$state`
- **Lokalizacja:** `frontend/src/lib/components/ItemTable.svelte:28-29`
- **Problem:** `savingIds` i `savedIds` jako `new Set()` bezpośrednio w `$state` — mogą być współdzielone między instancjami.
- **Sugestia:** Zainicjalizować przez funkcję fabrykującą.

#### 🟠 Brak `credentials: 'include'` w fetchu na stronie domowej
- **Lokalizacja:** `frontend/src/routes/+page.svelte:14`
- **Problem:** Fetch `/items/?limit=3` bez credentials.
- **Sugestia:** Dodać `{ credentials: 'include' }`.

#### 🟡 Niespójny error handling
- **Lokalizacja:** `frontend/src/routes/items/[id]/+page.svelte:103-105`
- **Problem:** Statyczny komunikat bez szczegółów błędu.
- **Sugestia:** Ujednolicić pattern — logować błąd przed ustawieniem stanu error.

#### 🟡 Brak type-safety w EChartsLineChart
- **Lokalizacja:** `frontend/src/lib/components/charts/EChartsLineChart.svelte:2`
- **Problem:** `// @ts-nocheck` wyłącza sprawdzanie typów.
- **Sugestia:** Usunąć `@ts-nocheck`, naprawić typowanie.

#### 🟡 Hardkodowany prefix API
- **Lokalizacja:** `frontend/src/lib/config.ts:7`
- **Problem:** Ścieżki budowane przez konkatenację — ryzyko literówek.
- **Sugestia:** Stworzyć typed client API z `$lib`.

---

## 5. Infra findings

### Podsumowanie
Infrastruktura poprawnie zaprojektowana, ale z lukami: hardkodowane domyślne sekrety w dev, brak healthchecków, frontend CI bez build.

### Findings

#### 🔴 Hardkodowane domyślne wartości sekretów w dev compose
- **Lokalizacja:** `infra/compose/docker-compose.dev.yml:8-9, 29-30`
- **Problem:** `POSTGRES_PASSWORD`, `AUTH_SECRET`, `ADMIN_SESSION_SECRET` mają fallbacki.
- **Sugestia:** Usunąć fallbacki, wymagać `.env` nawet w dev.

#### 🟠 Brak healthchecków dla backendu i frontendu
- **Lokalizacja:** `infra/compose/docker-compose.dev.yml`, `docker-compose.prod.yml`
- **Problem:** Backend i frontend bez healthchecków.
- **Sugestia:** Dodać healthcheck HTTP, użyć `condition: service_healthy`.

#### 🟠 Frontend CI bez etapu build
- **Lokalizacja:** `.github/workflows/frontend.yml:14-36`
- **Problem:** Brak `npm run build`.
- **Sugestia:** Dodać krok build po `svelte-check`.

#### 🟠 Caddyfile nie obsługuje wszystkich wariantów endpointów API docs
- **Lokalizacja:** `infra/caddy/Caddyfile:11-21`
- **Problem:** Brak obsługi `/docs` bez trailing slash, `/redoc/`, `/openapi.json/`.
- **Sugestia:** Użyć `/docs` i `/redoc` bez gwiazdki.

#### 🟡 Hardkodowane porty w dev compose
- **Lokalizacja:** `infra/compose/docker-compose.dev.yml:13, 38, 56`
- **Problem:** Porty 5432, 8000, 5173 hardkodowane.
- **Sugestia:** Użyć zmiennych `${DEV_DB_PORT:-5432}`.

#### 🟡 CORS_ORIGINS w prod compose może failować przy interpolacji
- **Lokalizacja:** `infra/compose/docker-compose.prod.yml:30`
- **Problem:** Interpolacja wewnątrz JSON stringa.
- **Sugestia:** Użyć podwójnych cudzysłowów i escapowania.

---

## 6. Discord Bot findings

### Podsumowanie
Bot używa poprawnego endpointu ingest. Brak obsługi rate limitingu (429 retry), error handling nie rozróżnia 429 od 5xx.

### Findings

#### 🔴 Brak obsługi rate limitingu (429 retry z backoff)
- **Lokalizacja:** `discord_bot/cogs/prices.py:98-103`, `discord_bot/cogs/prices.py:145-149`
- **Problem:** Bot nie obsługuje HTTP 429 — utrata danych przy rate limit.
- **Sugestia:** Dodać retry z exponential backoff (3 próby: 1s, 2s, 4s).

#### 🟠 Error handling nie rozróżnia 429 od 5xx
- **Lokalizacja:** `discord_bot/cogs/prices.py:145-149`
- **Problem:** Oba catche łapią `httpx.HTTPError` ogólnie.
- **Sugestia:** Rozróżnić `HTTPStatusError` od `HTTPError`.

#### 🟡 Timeout 10s może być za krótki
- **Lokalizacja:** `discord_bot/cogs/prices.py:52`
- **Problem:** Sztywny 10s timeout dla obu wywołań.
- **Sugestia:** Dłuższy timeout dla POST (30s).

#### 🟡 Brak walidacji API_URL
- **Lokalizacja:** `discord_bot/bot.py:14`
- **Problem:** Brak walidacji czy URL jest poprawny.
- **Sugestia:** Dodać `pydantic.HttpUrl`.

#### 💡 GRADE_CHOICES hardcoded — brak synchronizacji z backendem
- **Lokalizacja:** `discord_bot/cogs/prices.py:10-22`
- **Problem:** 12 stopni hardcoded w bocie, backend może mieć inną listę.
- **Sugestia:** Fetchować listę grade z backendu przy starcie.

---

## 7. Integration findings

### Podsumowanie
Kontrakty API spójne. Frontend poprawnie używa typów generowanych. Wykryto: JSON serializuje int keys jako stringi, brak rate limitu na inventory PUT, brak enum na `source`.

### Findings

#### 🟡 Inventory for-recipe: JSON serializuje int keys jako stringi
- **Lokalizacja:** `frontend/src/routes/items/[id]/+page.svelte:150`
- **Problem:** Backend zwraca `dict[int, int]`, JSON serializuje jako stringi, frontend konwertuje z powrotem.
- **Sugestia:** Ujednolicić serializację — zwracać listę `[{item_id, quantity}]`.

#### 🟠 Brak rate limitu na `PUT /api/inventory/{item_id}`
- **Lokalizacja:** `backend/app/user_inventory/router.py:32-41`
- **Problem:** Endpoint PUT bez rate limitu.
- **Sugestia:** Dodać `@limiter.limit("60/minute")`.

#### 🟠 Brak rate limitu na `POST /api/crafting/{item_id}/calculate`
- **Lokalizacja:** `backend/app/crafting/router.py:19-24`
- **Problem:** Endpoint POST bez rate limitu, może być spamowany.
- **Sugestia:** Dodać rate limit.

#### 🟡 Discord bot nie obsługuje `source` innego niż `'ah'`
- **Lokalizacja:** `discord_bot/cogs/prices.py:97`
- **Problem:** Schema pozwala na dowolny `source` — brak walidacji.
- **Sugestia:** Dodać enum `PriceSource` na backendzie.

---

## 8. Security findings

### Podsumowanie
Brak hardcoded secrets w repo (poza `.env` gitignored). Rate limiting chroni ingest ale nie auth. CORS poprawnie skonfigurowany. JWT cookie flow wymaga weryfikacji Secure/HttpOnly/SameSite.

### Findings

#### 🔴 Brak rate limitu na `/api/auth/login` i `/api/auth/register`
- **Lokalizacja:** `backend/app/auth/router.py`
- **Problem:** Auth endpointy bez rate limitu — brute-force attack possible.
- **Sugestia:** Dodać `@limiter.limit("10/minute")`.

#### 🟠 Brak security headers w Caddyfile
- **Lokalizacja:** `infra/caddy/Caddyfile`
- **Problem:** Brak CSP, HSTS, X-Frame-Options, X-Content-Type-Options.
- **Sugestia:** Dodać `header` dyrektywy w Caddyfile.

#### 🟠 `avatar_url` bez walidacji
- **Lokalizacja:** `backend/app/users/schemas.py`
- **Problem:** Akceptuje dowolny URL — ryzyko `javascript:` URI.
- **Sugestia:** Dodać walidację URL scheme (http/https only).

#### 🟠 Brak password policy
- **Lokalizacja:** `backend/app/auth/schemas.py`
- **Problem:** Hasło "1234" przejdzie walidację.
- **Sugestia:** Dodać min_length=8, wymagane znaki specjalne.

#### 🟡 CORS może być zbyt permisive
- **Lokalizacja:** `backend/app/config/settings.py`
- **Problem:** `allow_methods=["*"]`, `allow_headers=["*"]`.
- **Sugestia:** Ograniczyć do konkretnych metod i headers.

---

## 9. Dependencies findings

### Podsumowanie
Brak krytycznych CVE. `slowapi` nieaktualizowany od 2024. Kilka paczek minor/major behind. `cookie` <0.7.0 vulnerability w frontendzie.

### Findings

#### 🟠 Frontend: Vulnerable dependency `cookie` (<0.7.0)
- **Lokalizacja:** `frontend/package.json`
- **Problem:** `cookie@0.6.0` — GHSA-pxg6-pf52-xh8x.
- **Sugestia:** Poczekać na aktualizację `@sveltejs/kit` lub wymusić przez `overrides`.

#### 🟠 Backend: `pytest-asyncio` znacząco za wersją
- **Lokalizacja:** `backend/pyproject.toml`
- **Problem:** `>=0.24` vs latest `1.3.0`.
- **Sugestia:** Zaktualizować do `>=1.0`.

#### 🟠 Backend: `slowapi` potencjalnie EOL
- **Lokalizacja:** `backend/pyproject.toml`
- **Problem:** Ostatni release 0.1.9 z lutego 2024.
- **Sugestia:** Rozważyć alternatywy (custom middleware, `limits`).

#### 🟡 Discord bot: `pydantic-settings` za wersją
- **Lokalizacja:** `discord_bot/pyproject.toml`
- **Problem:** `>=2.3` vs latest `2.14.1`.
- **Sugestia:** Zaktualizować do `>=2.14`.

#### 🟡 Frontend: `echarts` major behind
- **Lokalizacja:** `frontend/package.json`
- **Problem:** `^5.6.0` vs latest `6.1.0`.
- **Sugestia:** Rozważyć upgrade do v6.

---

## 10. Code Quality findings

### Podsumowanie
Kod w dobrej kondycji — małe, jednopłaszczyznowe usługi. Główny problem: powielona logika paginacji, wysoka złożoność seed.py, zbyt wiele parametrów w funkcjach.

### Findings

#### 🟠 Powielona logika paginacji w serwisach
- **Lokalizacja:** `backend/app/items/services.py:9-47`, `backend/app/user_items/services.py:12-55`
- **Problem:** Identyczna struktura paginacji — duplikacja ~15 linii.
- **Sugestia:** Wydzielić helper `paginate_query()`.

#### 🟠 Wysoka złożoność seed.py
- **Lokalizacja:** `backend/seed.py:188-273`
- **Problem:** Złożoność cykliczna 15, 16 branchów.
- **Sugestia:** Podzielić na `seed_items()`, `seed_recipes()`, `seed_price_history()`.

#### 🟡 Zbyt wiele parametrów w funkcjach
- **Lokalizacja:** `backend/app/crafting/calculator.py:66`, `backend/app/items/router.py:14`
- **Problem:** Funkcje z >5 parametrami.
- **Sugestia:** Użyć dataclass/schema dla parametrów opcjonalnych.

#### 🟡 Magic numbers w kodzie
- **Lokalizacja:** `backend/app/config/settings.py:27`, `backend/app/crafting/calculator.py:75`
- **Problem:** Liczby magiczne bez nazw.
- **Sugestia:** Wydzielić jako stałe.

#### 🟡 Długa funkcja w prices/services.py
- **Lokalizacja:** `backend/app/prices/services.py:11-92`
- **Problem:** 93 linie z wbudowaną logiką bucketing.
- **Sugestia:** Wydzielić `_bucket_price_points()`.

---

## 11. Tester Evaluator findings

### Podsumowanie
Testy solidnej jakości — 94 testy, 95% coverage. Braki: niekompletne pokrycie auth (expired token, superuser), brak E2E, brak testów rate limiting.

### Findings

#### 🟠 Brak testów auth: expired token
- **Lokalizacja:** `backend/tests/test_auth.py`
- **Problem:** Brak testu z expired JWT.
- **Sugestia:** Dodać test z ręcznie wygenerowanym expired tokenem.

#### 🟠 Brak testów auth: superuser uprawnienia
- **Lokalizacja:** `backend/tests/test_auth.py`
- **Problem:** Brak testów dostępu do admin endpoints.
- **Sugestia:** Dodać testy z `is_superuser=True`.

#### 🟠 Brak E2E testu: pełna ścieżka ingest → price history
- **Lokalizacja:** `backend/tests/test_ingest.py`, `backend/tests/test_prices.py`
- **Problem:** Testy rozdzielone — brak jednego testu łączącego.
- **Sugestia:** Dodać test E2E: POST ingest → GET price-history.

#### 🟠 Brak E2E testu: crafting z inventory po ingest
- **Lokalizacja:** `backend/tests/test_crafting.py`, `backend/tests/test_inventory.py`
- **Problem:** Brak testu łączącego ingest → inventory → crafting.
- **Sugestia:** Dodać test E2E.

#### 🟡 Brak testów: rate limiting
- **Lokalizacja:** `backend/tests/` (brak pliku)
- **Problem:** Brak testów sprawdzających czy limiter działa.
- **Sugestia:** Dodać test wysyłający N requestów.

#### 🟡 Testy używają NullPool ale tworzą engine w wielu miejscach
- **Lokalizacja:** `backend/tests/test_items.py:14-21`
- **Problem:** Każdy plik definiuje własny fixture `db_session`.
- **Sugestia:** Przenieść fixture do `conftest.py`.

---

## 12. Skeptic findings

### Podsumowanie
Projekt wykazuje cechy over-engineeringu: powielony `utcnow` (5 miejsc), fastapi-users dla jednej funkcji, profiles jako oddzielny moduł dla jednego pola, Caddy jako osobny kontener dla 5 reguł.

### Findings

#### 🔴 Powielona funkcja `utcnow` w 5 miejscach
- **Lokalizacja:** `backend/app/items/models.py`, `backend/app/prices/models.py`, `backend/app/profiles/models.py`, `backend/app/user_items/models.py`, `backend/app/crafting/models.py`
- **Problem:** Ta sama funkcja zdefiniowana 5 razy.
- **Sugestia:** Przenieść do `app/config/` jako singleton.

#### 🟠 fastapi-users dla jednej funkcji auth
- **Lokalizacja:** `backend/app/auth/` (5 plików)
- **Problem:** Heavyweight framework dla 3 endpointów.
- **Sugestia:** Rozważyć ręczną implementację (~50 linii) lub zostawić jeśli planujesz 2FA/OAuth.

#### 🟠 Profiles jako oddzielny moduł dla jednego pola
- **Lokalizacja:** `backend/app/profiles/` (4 pliki)
- **Problem:** Profile ma 1:1 z User, tylko 2 dodatkowe pola.
- **Sugestia:** Przenieść `display_name` i `is_private` do modelu User.

#### 🟠 Services layer dla prostych CRUD-ów
- **Lokalizacja:** `backend/app/items/services.py`, `backend/app/prices/services.py`
- **Problem:** Nadmiarowa warstwa abstrakcji.
- **Sugestia:** Przenieść CRUD bezpośrednio do routera dla prostych przypadków.

#### 🟡 Zduplikowana logika formatowania cen
- **Lokalizacja:** `frontend/src/lib/currency.ts`, `discord_bot/cogs/prices.py`
- **Problem:** Ta sama logika, różne implementacje.
- **Sugestia:** Stworzyć shared Python package.

---

## 13. Visionary findings

### Podsumowanie
Event-driven architecture odciążyłaby backend, GraphQL uprościłoby crafting queries, Redis dałby natychmiastową poprawę responsywności. WebSocket/SSE dla live price updates.

### Findings

#### 🟠 Event-driven price ingestion
- **Lokalizacja:** `backend/app/ingest/router.py`, `backend/app/prices/services.py`
- **Problem:** Sync HTTP coupling — wolny DB = wolny ingest.
- **Sugestia:** Wprowadź broker (NATS, Redis Streams) jako bufor.

#### 🟠 WebSocket / SSE dla live price updates
- **Lokalizacja:** `backend/app/prices/router.py`
- **Problem:** Wykres odświeża się tylko przy reloadzie.
- **Sugestia:** WebSocket endpoint `/ws/prices` lub Server-Sent Events.

#### 🟡 GraphQL dla crafting tree queries
- **Lokalizacja:** `backend/app/crafting/services.py`
- **Problem:** Over-fetching pełnego drzewa.
- **Sugestia:** GraphQL lub REST z `?fields=` params.

#### 🟡 Redis cache layer
- **Lokalizacja:** `backend/app/items/services.py`, `backend/app/prices/services.py`
- **Problem:** Często czytane dane fetchowane za każdym razem z DB.
- **Sugestia:** Redis cache z TTL 1-5 min, invalidation przy `add_price_point`.

#### 🟡 Materialized views dla crafting profitability
- **Lokalizacja:** `backend/app/crafting/services.py:list_summaries`
- **Problem:** O(n²) przy rosnącej liczbie receptur.
- **Sugestia:** Materialized view w PostgreSQL, refresh co minutę.

---

## 14. Second Opinion

### Potwierdzone kluczowe findings
1. ✅ Brak rate limitu na auth — potwierdzone przez backend, security, integration
2. ✅ Powielony `utcnow` — potwierdzone przez skeptic, code-quality
3. ✅ Brak rollbacków — potwierdzone przez backend, code-quality
4. ✅ `slowapi` EOL — potwierdzone przez dependencies, skeptic

### Podważone findings
1. ❌ "Broken link w Svelte" — Svelte interpoluje `{item.id}` poprawnie, finding błędny
2. ❌ "Register schema wymaga więcej niż email+password" — `BaseUserCreate` wymaga tylko email+password, finding błędny
3. ❌ "pyjwt CVE-2025-45768" — false positive, patched w 2.12.1

### Dodany kontekst
- `SecureAdminAuth.middlewares` są **niemożliwe do użycia** — SQLAdmin ignoruje ten atrybut
- Case-insensitive match vs case-sensitive unique constraint tworzy duplicate items
- Frontend `@ts-nocheck` w ECharts — uzasadnione brakiem typów w svelte-echarts

### Konflikty między subagentami
| Konflikt | Subagenty | Werdykt |
|----------|-----------|---------|
| N+1 w crafting | backend (🟠) vs code-quality (🟢) | 🟢 FAŁSZYWY ALARM — dane ładowane raz |
| Router kolejność | backend (🟡) vs integration (🟢) | 🟢 POPRAWNIE — for-recipe przed PUT |
| fastapi-users overkill | skeptic (🟠) vs visionary (brak opinii) | 🟠 SUBIEKTYWNE — zostawić jeśli planujesz rozszerzenie auth |
| Services layer | skeptic (🟠) vs code-quality (🟢) | 🟡 ZALEŻY — zostawić dla spójności, ale uprościć proste CRUD |

---

## 15. Wzorce powtarzające się

| Wzorzec | Subagenty | Severity |
|---------|-----------|----------|
| Brak rollbacków przy błędach DB | backend, code-quality, integration | 🟠 |
| Powielony `utcnow` (5 miejsc) | skeptic, code-quality | 🔴 |
| Brak rate limitu na endpointach | backend, security, integration | 🔴 |
| `@ts-nocheck` w ECharts | frontend, skeptic | 🟡 |
| Brak healthchecków | infra, code-quality | 🟠 |
| Magic numbers bez nazw | code-quality, skeptic | 🟡 |
| Zduplikowana logika formatowania cen | skeptic, integration | 🟡 |
| Brak testów E2E | tester-evaluator, integration | 🟠 |
| Hardkodowane enumy (grade) | skeptic, discordbot | 🟡 |
| Brak walidacji `source` | backend, integration | 🟡 |
| Services layer dla CRUD | skeptic, code-quality | 🟡 |
| Brak security headers | security, infra | 🟠 |

---

## 16. Konflikty opinii

| Obszar | Skeptic | Visionary | Werdykt |
|--------|---------|-----------|---------|
| fastapi-users | Overkill dla 3 endpointów | — | Zostawić jeśli planujesz 2FA/OAuth |
| Services layer | Nadmiarowa abstrakcja | — | Zostawić dla spójności |
| Caddy | Over-engineering dla 5 reguł | — | Zostawić — TLS auto |
| SQLModel | Dual-engine komplikacja | — | Zostawić — jeden model DB+schema |
| Brak brokera | Problem przy skalowaniu | Event-driven ingestion | Rozważyć przy >50 userach |

---

## 17. Top 3 Quick Wins

1. **Dodać rate limit na auth endpointy** — 5 minut, 2 linie kodu, eliminuje brute-force risk
2. **Usunąć dead code `AdminAuth` w admin_auth.py** — 2 minuty, 1 linia do usunięcia
3. **Dodać `credentials: 'include'` na home page** — 1 minuta, 1 linia kodu

---

## 18. Long-term Roadmap

### Auth & Security
- [ ] Dodać rate limiting na wszystkie endpointy (auth, crafting, inventory)
- [ ] Dodać security headers w Caddyfile (CSP, HSTS, X-Frame-Options)
- [ ] Dodać password policy (min_length, special chars)
- [ ] Walidacja `avatar_url` scheme (http/https only)
- [ ] Przenieść secrets z `.env` do secret managera

### Database & Performance
- [ ] Dodać healthchecki dla backendu i frontendu
- [ ] Dodać rate limit na price-history (max limit parametr)
- [ ] Wydzielić helper `paginate_query()` (DRY)
- [ ] Dodać rollbacki we wszystkich serwisach DB
- [ ] Rozważyć Redis cache dla często czytanych danych

### Code Quality
- [ ] Przenieść `utcnow` do `app/config/` (usuń 4 duplikaty)
- [ ] Podzielić `seed.py` na 3 funkcje
- [ ] Usunąć dead code `AdminAuth`
- [ ] Dodać enum `PriceSource` dla walidacji `source`
- [ ] Wydzielić `_bucket_price_points()` helper

### Testing
- [ ] Dodać testy expired token i superuser auth
- [ ] Dodać E2E testy (ingest → prices, crafting end-to-end)
- [ ] Dodać testy rate limiting
- [ ] Przenieść `db_session` fixture do `conftest.py`
- [ ] Użyć `alembic upgrade head` w testach zamiast `create_all`

### Infrastructure
- [ ] Dodać `npm run build` do frontend CI
- [ ] Dodać multi-stage build do Dockerfile
- [ ] Dodać non-root user w Dockerfile
- [ ] Usunąć fallbacki sekretów z dev compose
- [ ] Dodać `.dockerignore` dla discord_bot

### Architecture (future)
- [ ] Rozważyć event-driven ingestion (NATS/Redis Streams)
- [ ] Rozważyć WebSocket/SSE dla live price updates
- [ ] Rozważyć GraphQL dla crafting tree queries
- [ ] Rozważyć materialized views dla crafting profitability
- [ ] Rozważyć batched writes dla inventory updates

---

*Audyt wykonany przez 12 subagentów równoległych + second opinion + synteza.*
*Żadne zmiany w kodzie projektu nie zostały wprowadzone.*
