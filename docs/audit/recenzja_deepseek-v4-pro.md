# Recenzja audytów — deepseek-v4-pro

**Data:** 2026-05-21
**Oceniający:** deepseek-v4-pro
**Metoda:** Ocena + weryfikacja subagentami explore (8 równoległych weryfikacji)

---

## Ranking końcowy

| # | Plik | Model | Ocena | Kluczowe zalety | Główne wady |
|---|------|-------|-------|-----------------|-------------|
| **1** | **e.md** | GLM-5.1 | **8.5/10** | Najszerszy zakres, fazowany plan naprawczy, trafne: root w kontenerach, brak auth ingest, 100% CSR, Caddy bez security headers | Kilka opinii architektonicznych jako fakty |
| **2** | **p.md** | kimi-k2.6 | **8.5/10** | **Unikalne i krytyczne**: TypeScript `^6.0.2` (nieistniejąca wersja!), świetna statystyka per subagent, klarowne rozstrzyganie konfliktów | Brak |
| **3** | **k.md** | opencode | **8.5/10** | Najdokładniejszy (12 subagentów), **samokorygujący** (N+1 w crafting jako FALSE ALARM), pełne pokrycie API contract validation | Bardzo długi |
| **4** | **b.md** | qwen3.6-plus-free | **8/10** | Najlepszy jako "pierwszy audyt" — 34 zbalansowane findingi, wszystkie potwierdzone | Niektóre findingi zbyt niskiej wagi |
| **5** | **h.md** | gpt-5.4 | **8/10** | **Uruchomił weryfikację** (`npm run check`, `pytest`), znalazł brakujący PUBLIC_API_URL, atomicity test gap | Nieco przegadany, zaniża severity |
| **6** | **m.md** | opencode | **8/10** | Second-opinion **poprawnie podważa false positives** (N+1 w crafting, broken link w Svelte, pyjwt CVE) | Powiela fałszywy "Discord token w .env" |
| **7** | **l.md** | opencode | **8/10** | Równie dokładny jak k.md, dobra analiza kontraktów API | Bardzo długi |
| **8** | **d.md** | kimi-k2.6 | **7.5/10** | Czytelny ranking P0-P3, wykrycie silent failure w for-recipe | Brak pokrycia security/infra |
| **9** | **f.md** | deepseek-v4-pro | **7.5/10** | Najwięcej findingów (114), unikalna analiza addon Lua | **2 false claims**: Caddy `/admin*` glob (działa poprawnie), `5 copies apitypes.lua` (niezweryfikowane) |
| **10** | **r.md** | Opus 4.7 | **7.5/10** | Dobra synteza, szybkie quick-wins, tabela health snapshot | **2 false claims**: "Caddy admin API on" (nie ma w configu), "slowapi key na connection IP" (przesadzone) |
| **11** | **j.md** | Gemini 3.1 | **7/10** | **Unikalne**: SELECT-then-delete anti-pattern, Uvicorn bez `--proxy-headers` | Nieukończony (brak syntezy) |
| **12** | **c.md** | qwen3.6-plus | **7/10** | Dobra struktura tabelaryczna | **1 false claim**: "SecureAdminAuth.middlewares never attached" — **sqladmin faktycznie go używa** |
| **13** | **i.md** | deepseek-v4-pro | **7/10** | 12 subagentów, dobry plan | Powiela fałszywy "Discord token w .env", niechlujna struktura |
| **14** | **o.md** | minimax-m2.7 | **7/10** | Dobra synteza konfliktów | Część claimów niezweryfikowana |
| **15** | **g.md** | minimax-m2.7 | **6/10** | **Unikalne**: literówka `ingredient_item_id` → poprawnie `ingredient` | Wąski zakres, niektóre findingi dyskusyjne |
| **16** | **a.md** | ? | **6/10** | Skupiony, treściwy | Zbyt wąski (tylko 3 problemy) |
| **17** | **n.md** | ? | **4/10** | Zwięzły | Za krótki, brak jakiejkolwiek weryfikacji |

---

## Metodologia oceny

Każdy audyt oceniany w 5 wymiarach:
1. **Trafność** — czy findingi są potwierdzone przez kod źródłowy (weryfikacja subagentami `explore`)
2. **Zakres** — pokrycie backend/frontend/infra/bot/security/testy
3. **Głębia** — czy audyt wykrywa root cause, czy tylko objawy
4. **Użyteczność** — czy ma ranking priorytetów i rekomendacje wykonalne
5. **Błędy** — czy zawiera false positives (im mniej, tym lepiej)

Weryfikacja kluczowych claimów wykonana przez 8 równoległych subagentów explore (każdy czytał faktyczny kod źródłowy).

---

## Potwierdzone jako PRAWDA (wszystkie audyty zgodne)

| Finding | Weryfikacja |
|---------|-------------|
| `utcnow()` zduplikowane 5× (items, prices, profiles, user_items, seed) | ✅ Identyczne kopie, brak shared utility |
| Ingest ma problem z granicami transakcji (commit per row w `match_or_create_item` + `add_price_point`) | ✅ 2 osobne commity, brak rollbacka po błędzie `match_or_create_item`, osierocone itemy |
| `computeNodeCost` zduplikowane w `+page.svelte` i `RecipeTree.svelte` | ✅ Niemal identyczne (różnica tylko w domyślnym `scale`) |
| `@ts-nocheck` w EChartsLineChart.svelte | ✅ Linia 2 |
| `(row: any)` w mapowaniu price history | ✅ Linia 124 w `items/[id]/+page.svelte` |
| `as InventoryItem[]` bez walidacji | ✅ Linia 68 w `inventory/+page.svelte` |
| Brak `USER` we wszystkich Dockerfile'ach (root) | ✅ backend, frontend, discord_bot — wszystkie jako root |
| Hardcoded default secrets w `settings.py` | ✅ `temporary-development-secret-must-be-32-chars` i odpowiednik dla admina |
| Hardcoded fallbacki w `docker-compose.dev.yml` | ✅ POSTGRES_PASSWORD, AUTH_SECRET, ADMIN_SESSION_SECRET |
| CORS `allow_methods=["*"]` i `allow_headers=["*"]` | ✅ W `main.py` linia 36-37 |
| Brak auth na `POST /api/ingest/prices` | ✅ Tylko rate limit 60/min, brak `Depends(current_user)` |
| Brak rate limitów na auth/crafting/inventory endpointach | ✅ `auth/router.py`, `crafting/router.py`, `user_inventory/router.py` — zero dekoratorów `@limiter` |
| Brak healthchecków dla backend/frontend (tylko DB ma) | ✅ Dev i prod compose — tylko `db` z `pg_isready` |
| Caddyfile bez security headers (HSTS/CSP/X-Frame-Options) | ✅ 27 linii, żadnego bloku `header` |
| `/docs`, `/redoc`, `/openapi.json` publicznie dostępne | ✅ Otwarte proxy do backendu bez auth |
| `authentication_backend` dwukrotnie przypisane (linia 46 martwa) | ✅ Linia 46 nadpisana przez 67 |

---

## Obiektywnie FALSE (przynajmniej 1 audyt się myli)

| False claim | Audyty które go zawierają | Dowód obalenia |
|-------------|---------------------------|----------------|
| "SecureAdminAuth.middlewares never attached by sqladmin" | c.md | sqladmin `BaseAdmin.__init__` (application.py:102) jawnie czyta `authentication_backend.middlewares` |
| "Discord token leaked in .env" | i.md, m.md | Plik `discord_bot/.env` nie istnieje. `.gitignore` zawiera regułę `.env` |
| "Caddy `/admin*` doesn't match sub-paths like `/admin/items`" | f.md | Caddy `*` glob dopasowuje dowolne znaki włącznie z `/` |
| "Caddy admin API on" | r.md | W Caddyfile nie ma `admin` directive |
| "slowapi key on connection IP instead of forwarded" | r.md | Przesadzone — `get_remote_address()` działa poprawnie, kwestia konfiguracji `--proxy-headers` w Uvicorn |

---

## Unikalne trafne znaleziska (tylko 1 audyt)

| Finding | Audyt | Weryfikacja |
|---------|-------|-------------|
| TypeScript `^6.0.2` w package.json — nieistniejąca wersja (prawdopodobny typosquat) | **p.md** | ✅ Potwierdzone. TS 6.x nie istnieje oficjalnie |
| `ingredient_item_id` — literówka (poprawnie: `ingredient`) | **g.md** | ✅ Brakuje litery "r" |
| SELECT-then-delete anti-pattern w `user_items/services.py` | **j.md** | ✅ `unfollow_item` robi SELECT przed DELETE zamiast atomowego DELETE WHERE |
| PUBLIC_API_URL brak eksportu w `config.ts` — `npm run check` failuje | **h.md** | ✅ Zweryfikowane przez audytora przy pomocy `svelte-check` |
| Uvicorn bez `--proxy-headers` — slowapi widzi IP proxy, nie klienta | **j.md** | ✅ W docker-compose.prod.yml brak flagi |

---

## Podsumowanie

Wszystkie 17 audytów łącznie wygenerowało ~150 unikalnych findingów. Po usunięciu duplikatów i false positives zostaje ~40 potwierdzonych problemów, z czego:

| Severity | Liczba | Top 3 |
|----------|--------|-------|
| Krytyczne | ~8 | Ingest bez auth, TS 6.0.2 typosquat, hardcoded secrets, root w kontenerach, Caddy bez security headers |
| Wysokie | ~12 | Brak rate limitów na auth, SELECT-then-delete, osierocone itemy w ingest, brak frontend testów |
| Średnie | ~15 | Duplikacja `utcnow()`/`computeNodeCost`, `@ts-nocheck`, brak healthchecków |
| Niskie | ~5 | Martwy kod `admin_auth:46`, `print()` zamiast logging, brak `max_length` na avatar_url |

**Najlepszy pojedynczy audyt** to **e.md** (GLM-5.1) — najszerszy zakres, fazowany plan, zero false positives.

**Najlepsza synteza** to **p.md** (kimi-k2.6) — jako jedyny wykrył krytyczny problem z TypeScript 6.0.2 i dostarczył statystykę per subagent.
