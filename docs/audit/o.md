# Audit Synthesis — ArcheRage Market Tracker

## TL;DR (top 10 by severity)

| # | Severity | Finding | Source |
|---|----------|---------|--------|
| 1 | 🔴 | `GET /api/items/{item_id}/price-history` bez auth — publiczne exposes market data | backend, security, integration |
| 2 | 🔴 | Discord bot pominięty w docker-compose — nie startuje z `make dev-up` | infra, visionary |
| 3 | 🔴 | CVE XSS w `cookie <0.7.0` (transitive przez `@sveltejs/kit`) | dependencies |
| 4 | 🟠 | `RecipeTree.svelte` rekurencja bez maxDepth — możliwy hang przy cyklu | frontend |
| 5 | 🟠 | `EChartsLineChart.svelte` — cały plik z `@ts-nocheck`, brak type-safety | frontend |
| 6 | 🟠 | Memory leak: `setTimeout` bez cleanup w `settings/+page.svelte` | frontend |
| 7 | 🟠 | Rate limiting tylko na 2 endpointach write (public read bez limitów) | security, backend |
| 8 | 🟡 | Bulk_ingest partial commits — **design decision**, nie bug (większość agentów się myli) | second-opinion |
| 9 | 🟡 | Hardcoded fallback secrets — **medium not critical** (validator >= 32 chars) | second-opinion |
| 10 | 🟡 | Discord bot poza CI/CD workflow (`docker.yml` nie buduje bota) | infra |

---

## 🔴 Krytyczne — natychmiastowa akcja

### 1. Price history endpoint bez auth
- **Lokalizacja:** `backend/app/prices/router.py:28-43`
- **Problem:** `read_item_price_history` nie ma `Depends(current_user)`, architektura mówi że wszystkie `/api/` powinny być auth-controlled
- **Akcja:** Dodać `user: User = Depends(current_user)` do tego endpointa
- **Consensus:** backend 🔴, integration 🟡, security 🟠, second-opinion potwierdza

### 2. Discord bot poza docker-compose
- **Lokalizacja:** `infra/compose/docker-compose.{dev,prod}.yml`
- **Problem:** Bot nie jest usługą w compose, startuje tylko z terminala `uv run python bot.py`
- **Akcja:** Dodać `discord_bot` service do obu plików compose
- **Consensus:** infra 🔴, visionary 💡, second-opinion potwierdza

### 3. CVE cookie XSS
- **Lokalizacja:** `frontend/package.json` (transitive)
- **Problem:** `cookie <0.7.0` przez `@sveltejs/kit ^2.57.0`
- **Akcja:** `npm audit fix --force` lub ręczne `"cookie": ">=0.7.0"` w overrides
- **Consensus:** dependencies 🟠, second-opinion potwierdza

---

## Wzorce powtarzające się (wyłapane przez ≥2 subagentów)

### Pattern 1: Brak auth guards na "publicznych" read endpointach
- Backend: `price-history` bez auth
- Frontend: główna strona fetch bez `credentials: 'include'`
- **Wniosek:** Architektura zakłada "auth controlled" ale half measures na read GETs

### Pattern 2: Discord bot jest outsiderem
- Infra: nie ma go w compose
- CI/CD: `docker.yml` nie buduje go
- Visionary: sugeruje konsolidację do backendu
- **Wniosek:** Bot jest de facto sidecar który wymyka się standardowej infrastruktury

### Pattern 3: Frontend bez type-safety tam gdzie ryzyko jest największe
- `EChartsLineChart.svelte` — `@ts-nocheck` na całym pliku
- `RecipeTree.svelte` — rekurencja bez limitu głębokości
- `api.d.ts` — niekompletne typy (puste `parameters`)
- **Wniosek:** Komponenty z najbardziej złożoną logiką mają najsłabsze type-safety

### Pattern 4: Rate limiting jest partial
- Security: tylko 2 endpointy mają `@limiter.limit`
- Backend: crafting endpoints też nie mają
- **Wniosek:** Rate limiter istnieje jako singleton ale nie jest appliqué globalnie

---

## Konflikty opinii między subagentami

| Konflikt | Agent A | Agent B | Second-opinion resolution |
|----------|---------|---------|---------------------------|
| `bulk_ingest` partial commits | backend: 🟡 "problem" | visionary: 💡 "overkill" | second-opinion: **design decision**, nie bug |
| Hardcoded secrets severity | security: 🔴 "critical" | — | second-opinion: 🟡 medium (validator >= 32) |
| Alembic value | skeptic: 🟡 "overhead" | — | second-opinion: 💡 standard practice |
| Rate limiting severity | security: 🟠 "high" | backend: 🟠 "crafting" | second-opinion: 🟡 (public read < risk) |
| fastapi-users | skeptic: 🟠 "over-engineering" | — | second-opinion: 💡 minimum viable |

**Główny wniosek:** Skeptic i security mają tendencję do zawyżania severity. Second-opinion często kwalifikuje te findings niżej.

---

## Top 3 Quick Wins (low effort, high impact)

### 1. Dodać Discord bot do docker-compose
- **Effort:** ~20 linii YAML
- **Impact:** Bot startuje z `make dev-up`, nie trzeba pamiętać o ręcznym starcie
- **Pliki:** `infra/compose/docker-compose.dev.yml`, `infra/compose/docker-compose.prod.yml`

### 2. Naprawić CVE cookie
- **Effort:** `npm audit fix --force` lub dodanie overrides w `package.json`
- **Impact:** Zamknięcie XSS vulnerability
- **Pliki:** `frontend/package.json`

### 3. Dodać `maxDepth` do RecipeTree
- **Effort:** ~5 linii kodu (sprawdzenie `depth > maxDepth`)
- **Impact:** Frontend nie zawiesi się na cyklicznych danych z API
- **Pliki:** `frontend/src/lib/components/crafting/RecipeTree.svelte`

---

## Long-term Roadmap (większe refaktoryzacje)

### Priorytet 1: Architektura auth
- Dodać auth guards na wszystkich `/api/` endpoints (zgodnie z architecture.md)
- Rozważyć uproszczony JWT bez fastapi-users (jeśli tylko 3 endpointy)
- **Ryzyko:** Średnie — wymaga testów integracyjnych

### Priorytet 2: Frontend type-safety
- Usunąć `@ts-nocheck` z EChartsLineChart, dodać interfejs `ChartProps`
- Przenieść `computeNodeCost` do `$lib/crafting.ts` (teraz duplicated w 3 miejscach)
- Dodać Playwright dla critical paths (RecipeTree, crafting calculator)
- **Ryzyko:** Niskie — refactoring bez zmiany behavior

### Priorytet 3: Infrastructure completeness
- Dodać resource limits do compose prod
- Dodać discord_bot do `docker.yml` CI workflow
- Dodać `pip-audit` do CI (backend + discord_bot)
- **Ryzyko:** Niskie — pure config

### Priorytet 4: Consolidate user_items vs user_inventory
- **Uwaga:** Skeptic mówi że to redundantne, ale second-opinion uznaje to za "nice to have" nie "must fix"
- Do rozważenia przy następnej większej refaktoryzacji
- **Ryzyko:** Średnie — wymaga migracji danych i zmiany API contractu

### Priorytet 5: Real-time updates (WebSocket/SSE)
- **Uwaga:** Visionary: największy UX gap
- Rozważyć SSE dla price updates (łatwiejsze niż WebSocket)
- **Ryzyko:** Średnie — wymaga frontend state management changes

---

## Pozytywne observacje (co działa dobrze)

| Aspekt | Status |
|--------|--------|
| SQL injection protection | ✅ SQLModel parameterized queries throughout |
| Rate limiter singleton | ✅ Poprawnie zaimplementowany |
| Test coverage (backend) | ✅ 95% |
| Transaction handling | ✅ Rollback w error path |
| DB constraints | ✅ UniqueConstraint, FK, indeksy |
| Python 3.13 | ✅ Nowoczesny stack |
| CI/CD workflows | ✅ Ruff + pytest dla backend i bot |

---

## Metryki audytu

| Metric | Value |
|--------|-------|
| Total findings | ~50 |
| 🔴 Critical | 3 |
| 🟠 High | 4 |
| 🟡 Medium | ~20 |
| 🟢 Low | ~15 |
| 💡 Suggestions | ~10 |
| Cross-agent conflicts | 5 |
| Quick wins (top 3) | 3 |

---

**Przygotowane przez:** minimax-m2.7 audit agent
**Worktree:** `audit-minimax-m2.7-20260520-2222`
**Data:** 2026-05-20