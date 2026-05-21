# Synteza audytu — ArcheRage Market Tracker

**Data audytu:** 2026-05-20  
**Commit:** `d0175bf`  
**Model:** kimi-k2.6  
**Worktree:** `/home/dv6/GitHub/audit-kimi-20260520-2223`

---

## 1. TL;DR — Top 10 findings (posortowane po severity)

| # | Severity | Finding | Subagenci |
|---|----------|---------|-----------|
| 1 | 🔴 | **Publiczny ingest bez autentykacji** — każdy z internetu może wprowadzać fałszywe ceny i auto-create itemów | backend, security, visionary, second-opinion |
| 2 | 🔴 | **Hardcoded secrets fallback w Settings** — znane domyślne sekrety JWT/DB uruchomią się jeśli env nie zostaną ustawione | security, second-opinion |
| 3 | 🔴 | **UserRead OpenAPI schema niezgodna z runtime** — serializer usuwa 3 pola, ale schema deklaruje je jako wymagane; zielony build, czerwona produkcja | integration, second-opinion |
| 4 | 🔴 | **TypeScript `^6.0.2` w package.json** — nieoficjalna wersja, ryzyko braku kompatybilności z SvelteKit/Vite | frontend, second-opinion |
| 5 | 🟠 | **Brak atomowości batcha w ingest + brak rollback po błędzie** — commit per row, session poisoning po failed `match_or_create_item` | backend, skeptic, second-opinion |
| 6 | 🟠 | **Over-permissive CORS** — `allow_methods=["*"]` + `allow_headers=["*"]` + `allow_credentials=True` | security |
| 7 | 🟠 | **Brak rate limitingu na auth + in-memory slowapi** — brute-force na login/register, nieskuteczne przy `--workers 2` | backend, security, visionary, dependencies |
| 8 | 🟠 | **Wszystkie Dockerfile'y działają jako root** — RCE = root w kontenerze | infra, frontend, discordbot |
| 9 | 🟠 | **Migracje DB uruchamiane w CMD backendu** — race condition przy scale / rolling deploy | infra, second-opinion |
| 10 | 🟠 | **Brak testów frontendowych + brak E2E** — zero `.test.` / `.spec.` w `frontend/src/` | tester-evaluator, code-quality, frontend |

---

## 2. Krytyczne — natychmiastowa akcja (🔴)

### 2.1 Publiczny ingest bez autentykacji
- **Lokalizacja:** `backend/app/ingest/router.py:12`
- **Wektory ataku:** fałszywe ceny, manipulacja `current_price`, zaśmiecanie tabeli `Item` przez auto-create, DoS przez commit-per-row.
- **Sugestia:** Wprowadź API-key header lub HMAC dla źródeł danych (bot, przyszły watcher). Nie polegaj wyłącznie na rate limitie `60/minute`.

### 2.2 Hardcoded secrets fallback w Settings
- **Lokalizacja:** `backend/app/config/settings.py:10-15`
- **Wektory ataku:** Jeśli env nie są ustawione, aplikacja uruchamia się z `temporary-development-secret-must-be-32-chars` — znanym sekretem.
- **Sugestia:** Usuń fallbacki. Wymuszaj `env` (brak defaultu = crash przy starcie). Dla dev użyj `.env.dev`.

### 2.3 UserRead OpenAPI schema niezgodna z runtime
- **Lokalizacja:** `backend/app/auth/schemas.py:8-15` vs `frontend/src/lib/api.d.ts:688-714`
- **Wektory ataku:** Frontend polega na `user.data.is_superuser` które w runtime jest `undefined`. Może prowadzić do błędów renderowania lub nieautoryzowanego dostępu do `/admin`.
- **Sugestia:** Usuń custom serializer lub użyj osobnego schema `UserReadPublic` bez wrażliwych flag. Zsynchronizuj OpenAPI schema z runtime.

### 2.4 TypeScript `^6.0.2` w package.json
- **Lokalizacja:** `frontend/package.json:25`
- **Wektory ataku:** Microsoft nie wydaje wersji 6.x. Nieprzewidywalne zachowanie kompilatora, potencjalne błędy w `svelte-check`.
- **Sugestia:** Zmień na oficjalną wersję `^5.8.0`. Zweryfikuj `package-lock.json`.

---

## 3. Wzorce powtarzające się (≥2 subagentów = najważniejsze)

| Wzorzec | Wykryli | Opis |
|---------|---------|------|
| **Brak testów frontendowych** | tester-evaluator, code-quality, frontend | Zero testów w `frontend/src/`. Logika `computeNodeCost`, `formatCurrency`, auth flow niechroniona regresją. |
| **Duplikacja logiki** | code-quality, frontend, discordbot | `computeNodeCost` w dwóch komponentach, `format_price` w bocie vs `formatCurrency` we frontendzie, `GRADE_CHOICES` w bocie vs `grade_map` w backendzie. |
| **seed.py jako anti-pattern** | code-quality, skeptic, backend | 286 linii poza `app/`, inline dane, dwa identyczne SELECT-y, aktualizuje `current_price` bez `last_price_at`. |
| **Root w Dockerfile'ach** | infra, frontend, discordbot | Wszystkie 3 kontenery działają jako root. Zwiększa powierzchnię ataku. |
| **Brak rate limitów na auth** | backend, security, visionary | Tylko 2 endpointy mają `@limiter.limit`. Brak ochrony login/register. slowapi in-memory nie działa przy `--workers 2`. |
| **Publiczny ingest** | backend, security, visionary | Brak autentykacji na `POST /api/ingest/prices`. Zatruwanie danych, DoS. |
| **Niespójne nazewnictwo domenowe** | code-quality, integration | `user_items` (backend) vs `saved_items` (frontend) vs `inventory` (inne). Trzy nazwy, dwa koncepty. |
| **slowapi — stack problemów** | dependencies, visionary, security, backend | Nieutrzymywany od 15+ miesięcy, in-memory (nieskuteczny przy scale), brak limitów na auth. |

---

## 4. Konflikty opinii między subagentami

### 4.1 Denormalizacja `current_price` — backend akceptuje vs skeptic chce usunąć
- **Backend:** Zgłasza tylko niespójność w `seed.py` (🟡), nie kwestionuje decyzji architektonicznej.
- **Skeptic:** Uznaje denormalizację za 🟠 nieuzasadnioną przy 29 itemach — „premature optimization”.
- **Second-opinion:** Skektor ma rację co do proporcji complexity/value, ale decyzja jest chroniona przez Constitution (`docs/ai/constitution.md:15`). Zmiana wymaga ADR, nie tylko refaktoringu. **Wniosek:** Pozostaw jako technical debt, nie naprawiaj bez ADR.

### 4.2 sqladmin — skeptic krytykuje vs second-opinion broni
- **Skeptic:** „Overkill dla 5 widoków, ręczne CRUD w 30 liniach byłyby prostsze.”
- **Second-opinion:** sqladmin to standardowe narzędzie w ekosystemie FastAPI. Ręczne pisanie auth + pagination + filtrowanie + UI to znacznie więcej niż 30 linii. Jedyny realny problem to martwy kod `SecureAdminAuth.middlewares` (🟢). **Wniosek:** Nie usuwaj sqladmin, usuń martwy kod.

### 4.3 Dwa osobne pyproject.toml — overkill czy uzasadnione?
- **Skeptic:** Overkill dla 230 LOC bota — powinien być w `backend/app/bot/`.
- **Second-opinion:** Standardowa praktyka organizacyjna. Bot ma inny runtime, inny cykl życia, inny deploy. Wspólny lockfile wymuszałby aktualizację zależności bota przy każdej zmianie backendu. **Wniosek:** Uzasadnione, nie zmieniaj.

### 4.4 Watcher daemon — regresja czy trade-off produktowy?
- **Skeptic:** „Usunięcie watchera to architektoniczna regresja — ręczny bot nie skaluje się w MMO.”
- **Second-opinion:** Decyzja jest celowa i udokumentowana w roadmapie. Projekt jest w fazie MVP/hobby. Ręczny ingest pozwala zbierać dane bez pisania addonu Lua. **Wniosek:** Nie jest to bug — to subiektywny trade-off.

### 4.5 Severity ingest — backend 🔴 vs security 🟡
- **Backend:** 🔴 — integralność danych, zatruwanie cen, auto-create itemów.
- **Security:** 🟡 — skupia się na DoS/resource exhaustion.
- **Second-opinion:** Backend ma rację — zatruwanie danych jest poważniejsze niż DoS. Finalny severity: **🔴 Critical** z dwoma wektorami ataku.

### 4.6 TypeScript ^6.0.2 — frontend 🔴 vs dependencies (brak uwagi)
- **Frontend:** 🔴 — anomalia wersji, ryzyko kompilatora.
- **Dependencies:** Nie wykrył — skupił się na CVE w pyjwt i cookie.
- **Second-opinion:** Luka w pokryciu audytu zależności. npm audit nie wykrywa „dziwnych” wersji. **Wniosek:** Dodaj ręczną weryfikację wersji TypeScript do CI.

---

## 5. Top 3 quick wins — low effort, high impact

| # | Zmiana | Linie kodu | Impact |
|---|--------|-----------|--------|
| 1 | **Usuń hardcoded secrets fallbacki** w `Settings` — zamień defaulty na `Field(...)` lub usuń je całkiem | ~3 | 🔴 → eliminuje najpoważniejszą lukę bezpieczeństwa |
| 2 | **Ujednolić `credentials: 'include'`** we wszystkich fetchach frontendu (publiczne + prywatne) | ~5-10 | 🟠 → eliminuje niespójność auth i cache, zapobiega przyszłym bugom |
| 3 | **Dodaj `USER` do Dockerfile'ów** + usuń `devDependencies` z frontend runtime (`npm prune --production`) | ~6 per Dockerfile | 🟠 → znacząco zmniejsza powierzchnię ataku i rozmiar obrazu |

---

## 6. Long-term roadmap — większe refactory

### 6.1 Security hardening (2-4 tygodnie)
- Wprowadź API-key / HMAC na ingest
- Zamień `allow_methods=["*"]` i `allow_headers=["*"]` na jawne listy
- Dodaj limity na auth (5/min login, 3/min register) — rozważ migrację z `slowapi` na `fastapi-limiter` + Redis
- Dodaj security headers w Caddyfile (HSTS, CSP, X-Frame-Options)
- Wyłącz `/docs` i `/openapi.json` w produkcji lub ogranicz IP allowlist
- Rozdziel sekrety: `jwt_secret`, `reset_token_secret`, `verification_token_secret`
- Dodaj `max_age` do admin session cookie

### 6.2 Transakcyjność i spójność danych (1-2 tygodnie)
- Usuń commity z `match_or_create_item` i `add_price_point` — commit na poziomie `bulk_ingest` (per batch lub per row)
- Dodaj `session.rollback()` po każdym błędzie w batchu
- Używaj `add_price_point` w `seed.py` (lub wydziel `set_item_current_price`) aby zachować invariant `current_price` + `last_price_at`
- Dodaj test regresji na "session poison" w środku batcha

### 6.3 Testy i jakość (2-3 tygodnie)
- Wprowadź **Vitest** + testing-library/svelte dla logiki pure i komponentów
- Dodaj **2-3 smoke-testy Playwright** (login, item detail, crafting calculator) uruchamiane w CI przeciwko dev backendu
- Przenieś wspólne fixtures (`db_session`, `auth_client`) do `conftest.py`
- Dodaj testy rate limitera, edge case'ów walidacji, bucketingu `5m`
- Rozszerz `test_consistency.py` o parsowanie AST/ESM (nie string-match)

### 6.4 Refactoring duplikacji i nazewnictwa (1-2 tygodnie)
- Wydziel `computeNodeCost` do `$lib/crafting.ts`
- Ujednolić nazewnictwo: `watchlist` (zamiast `user_items`/`saved_items`) i `inventory` (stan posiadania)
- Wydziel grade mapping do wspólnego endpointu `/api/grades` lub shared JSON
- Wydziel `formatCurrency`/`format_price` do shared kontraktu (JS + Python)
- Rozdziel `seed.py`: dane do JSON/YAML, logikę do `app/cli/seed.py` (Typer)

### 6.5 Infra i operacje (2-3 tygodnie)
- Wydziel migracje DB do osobnego init containera / GitHub Action pre-deploy
- Dodaj healthchecki do backend, frontend, caddy w prod compose
- Dodaj resource limits (CPU / memory) w prod compose
- Rozdziel sieci w prod compose (`frontend_network`, `backend_network`)
- Dodaj skanowanie bezpieczeństwa do CI: `pip-audit`, `npm audit`, Trivy image scan
- Dodaj build discord_bot do CI docker workflow

### 6.6 Architektura — alternatywy do rozważenia (nie priorytetowe na MVP)
- **Redis Streams / kolejka** dla ingestu — zdejmij back-pressure z klientów, umożliwia retry
- **Static adapter** dla frontendu — usuń kontener Node, serwuj przez Caddy jako SPA (`fallback: '200.html'`)
- **TimescaleDB** dla `PricePoint` — hypertables, continuous aggregates, polityka retencji
- **Wersjonowanie API** (`/api/v1/`) — odporność na przyszłość
- **GraphQL** dla strony item detail — 1 RTT zamiast 3 requestów

---

## 7. Statystyka findings per subagent

| Subagent | 🔴 | 🟠 | 🟡 | 🟢 | 💡 | Razem |
|----------|----|----|----|----|----|-------|
| backend | 1 | 3 | 4 | 4 | 1 | 13 |
| frontend | 2 | 2 | 5 | 3 | 3 | 15 |
| infra | 0 | 5 | 7 | 2 | 3 | 17 |
| discordbot | 0 | 1 | 6 | 3 | 2 | 12 |
| integration | 1 | 1 | 2 | 1 | 0 | 5 |
| security | 1 | 3 | 5 | 2 | 1 | 12 |
| dependencies | 0 | 0 | 3 | 1 | 3 | 7 |
| code-quality | 0 | 3 | 4 | 3 | 3 | 13 |
| tester-evaluator | 1 | 3 | 4 | 2 | 1 | 11 |
| skeptic | 1 | 2 | 4 | 3 | 2 | 12 |
| visionary | 0 | 4 | 5 | 0 | 2 | 11 |
| second-opinion | 0 | 0 | 0 | 0 | 0 | ~18 opinii* |
| **RAZEM** | **7** | **27** | **49** | **24** | **24** | **~131** |

*second-opinion nie tworzył nowych findings w tradycyjnym sensie, ale potwierdził ~12, podważył 7 i zgłosił 6 własnych obserwacji.

---

## 8. Podsumowanie w jednym zdaniu

Projekt jest stabilny na poziomie MVP, ale ma **4 krytyczne luki** (publiczny ingest, hardcoded secrets, niezgodność OpenAPI, anomalia TypeScript) i **powtarzające się antywzorce** (brak testów frontendu, duplikacja logiki, root w kontenerach, niespójne nazewnictwo) które wymagają natychmiastowej i długoterminowej uwagi — szczególnie w obszarze bezpieczeństwa i spójności transakcyjnej.
