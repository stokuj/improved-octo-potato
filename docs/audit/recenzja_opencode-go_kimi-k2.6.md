# Recenzja Audytów — ArcheRage Market Tracker

**Autor recenzji:** opencode-go/kimi-k2.6  
**Data:** 2026-05-21  
**Zakres:** 17 plików audytowych w `docs/audit/`  
**Metoda:** odczyt treści + weryfikacja subagentami (explore)  

---

## Metodologia

1. Przeczytano wszystkie 17 plików audytowych (a.md–r.md).
2. Zidentyfikowano najczęściej powtarzające się findings.
3. Zweryfikowano 14 kluczowych zarzutów za pomocą subagentów (read + grep na produkcyjnym kodzie).
4. Opracowano ranking audytów pod kątem: trafności, dokładności, rzetelności severity, praktyczności.

---

## Weryfikacja kluczowych findings (14 zarzutów)

| # | Zarzut | Plik / Linia | Weryfikacja | Wynik |
|---|--------|--------------|-------------|-------|
| 1 | `match_or_create_item` commituje wewnątrz, brak rollback po błędzie | `backend/app/ingest/services.py:46, 86-93` | Subagent | ✅ PRAWDA |
| 2 | `add_price_point` też commituje wewnątrz, item może zostać osierocony | `backend/app/prices/services.py:123` | Subagent | ✅ PRAWDA |
| 3 | Globalny `$state` w `auth.svelte.ts` → wyciek sesji przy SSR (`adapter-node`) | `frontend/src/lib/auth.svelte.ts:12`, `svelte.config.js:1` | Subagent | ✅ PRAWDA |
| 4 | `authentication_backend` przypisany 2× (martwy kod) | `backend/app/admin_auth.py:46, 67-69` | Subagent | ✅ PRAWDA |
| 5 | `utcnow()` zduplikowany w 5 plikach | 5 definicji w models + seed | Subagent | ✅ PRAWDA |
| 6 | Ingest endpoint publiczny (bez auth) | `backend/app/ingest/router.py:12` | Subagent | ✅ PRAWDA |
| 7 | Wszystkie Dockerfile działają jako root (brak `USER`) | 3 Dockerfile, zero `USER` | Subagent | ✅ PRAWDA |
| 8 | Zero testów frontendowych | 0 plików `.test.*`/`.spec.*` | Subagent | ✅ PRAWDA |
| 9 | TypeScript `^6.0.2` w `package.json` (nieoficjalna wersja) | `frontend/package.json:25` | Subagent | ✅ PRAWDA |
| 10 | `computeNodeCost` zduplikowany w 2 komponentach | `+page.svelte:36-53`, `RecipeTree.svelte:19-33` | Subagent | ✅ PRAWDA |
| 11 | Race condition przy aktualizacji `current_price` | `prices/services.py:117-121` | Subagent | ✅ PRAWDA |
| 12 | `session.exec()` zamiast `execute()` przy DELETE | `user_inventory/services.py:45-49` | Subagent | ✅ PRAWDA |
| 13 | `print()` zamiast `logging` w `auth/manager.py` | `backend/app/auth/manager.py:30` | Subagent | ✅ PRAWDA |
| 14 | `load_all_recipes/items` ładują wszystko do RAM | `crafting/services.py:15-16, 24` | Subagent | ✅ PRAWDA |

**Jedyny wyraźny false positive:** `k.md` (opencode) zgłasza SQL injection przez `ilike(f"%\{q\}%")` — SQLAlchemy robi parameterized binding, więc to **nie jest SQL injection**.

---

## Ranking audytów (od najlepszego)

| # | Plik | Model / Źródło | Ocena | Uzasadnienie |
|---|------|----------------|-------|-------------|
| **1** | `p.md` | **kimi-k2.6 synteza** | 🥇 **Najlepszy** | 4 krytyczne, wszystkie zweryfikowane. Mądre konflikty opinii (np. denormalizacja `current_price` — zostawić wg constitution). Quick wins + long-term roadmap. Nie przesadza severity. TypeScript `^6.0.2` jako 🔴 — trafne. |
| **2** | `r.md` | **Opus 4.7 synteza** | 🥈 **Bardzo dobry** | 6 krytycznych, wszystkie prawdziwe. Praktyczny health snapshot. Downgrade'uje przesadzone findings (TimescaleDB, TanStack, tRPC). Mierzalny effort: „~3h eliminuje >50% findings”. |
| **3** | `h.md` | **gpt-5.4** | 🥉 **Bardzo dobry** | Zero krytycznych — ale to zaleta, bo nie przesadza. Kluczowe realne problemy: race condition w prices, PUBLIC_API_URL mismatch (fail `npm run check`), bot lookup exact-match, auth/profile coupling. Bardzo realistyczny. |
| **4** | `b.md` | **qwen3.6-plus-free** | ⭐ Dobry | 651 linii, bardzo szczegółowy. Wszystkie główne findings prawdziwe. Minus: czasem zawyża severity (np. dead code jako HIGH, brak `services.py` w users jako HIGH). |
| **5** | `d.md` | **kimi-k2.6** | ⭐ Dobry | Konkretny polski audyt z rankingiem P0/P1/P2/P3. Dobre pokrycie frontendu (god component, brak API layer). Minus: brakuje mu security findings (root, CORS). |
| **6** | `k.md` | **opencode** | ⭐ Dobry | Obszerny, dobre pokrycie frontendu i infra. Minus: **false positive SQL injection** (`ilike(f"%\{q\}%")`) oraz bardzo długi (przycięty do 50KB). |
| **7** | `e.md` | **GLM-5.1** | ⭐ Dobry | Strategiczne spojrzenie, dużo security. Minus: rozwlekły (432 linie), część findings to „sugestie modernizacji” nie błędy. |
| **8** | `m.md` | **opencode kompleksowy** | ⭐ Dobry | Second-opinion z werdyktami. Minus: przesadza (token w `.env` jako 🔴, choć `.env` jest gitignored; fastapi-users overkill to subiektywne). |
| **9** | `f.md` | **deepseek-v4-pro** | ⚠️ Średni | 645 linii, bardzo szczegółowy. Minus: **zbyt wiele krytycznych** — np. grade choices jako HIGH, addon Lua jako CRITICAL, buttoncommon jako CRITICAL. Przesadza severity. |
| **10** | `c.md` | **qwen3.6-plus** | ⚠️ Średni | Dobre findings. Minus: `SecureAdminAuth.middlewares never attached` — trudne do weryfikacji bez głębokiej znajomości sqladmin. |
| **11** | `l.md` | **opencode subagenci** | ⚠️ Średni | Obszerny, ale przycięty. N+1 w crafting to false positive (sam autor to stwierdził w tekście). |
| **12** | `j.md` | **Gemini 3.1 Pro** | ⚠️ Średni | Dobre findings. Minus: **niedokończony** — brakuje second-opinion, skeptic, visionary, syntezy. |
| **13** | `i.md` | **deepseek-v4-pro synteza** | ⚠️ Średni | Minus: token Discorda w `.env` jako 🔴 wyciek — wątpliwe, skoro `.env` jest gitignored. |
| **14** | `g.md` | **minimax-m2.7** | ⚠️ Słabszy | Tylko 17 findings. `ingredient_item_id` jako „literówka” to subiektywna opinia, nie fakt. Mało security/infra. |
| **15** | `o.md` | **minimax-m2.7 synteza** | ⚠️ Słabszy | Price history bez auth jako 🔴 — wątpliwe (GET publiczne to może być design). Zbyt krótki. |
| **16** | `a.md` | nieznany | ⚠️ Słaby | Tylko 56 linii i 3 findings. Wszystkie prawdziwe, ale to za mało na pełny audyt. |
| **17** | `n.md` | nieznany | ⚠️ Słaby | 40 linii. Zbyt zwięzły — brak kontekstu i linii kodu. |

---

## Wzorce powtarzające się we wszystkich audytach (pewniaki)

| # | Wzorzec | Zgłaszają | Severity |
|---|---------|-----------|----------|
| 1 | **Ingest publiczny + commit per row** | a, b, c, d, e, f, h, i, j, k, l, m, p, r | 🔴 |
| 2 | **Root w kontenerach** | e, f, j, k, m, p, r | 🔴 |
| 3 | **Brak rate limitu na auth** | e, h, i, j, k, l, m, p, r | 🔴 |
| 4 | **`utcnow()` × 5** | b, c, d, e, f, g, j, k, l, m | 🟠 |
| 5 | **Martwy kod `AdminAuth`** | b, c, d, f, j, k, l, m | 🟠 |
| 6 | **Brak testów frontendu** | b, c, d, e, f, h, j, k, m, p, r | 🟠 |
| 7 | **`computeNodeCost` zduplikowany** | c, d, f, h, j, k, l | 🟡 |
| 8 | **`@ts-nocheck` + `any`** | c, d, f, h, j, k, l, m | 🟡 |
| 9 | **Brak healthchecków** | e, f, h, j, k, l, m | 🟡 |
| 10 | **HTTP client per request w bocie** | c, e, f, j, k, l, m | 🟡 |

---

## Konflikty między audytami

| Temat | Strona A (severity) | Strona B (severity) | Werdykt recenzenta |
|-------|--------------------|---------------------|-------------------|
| `bulk_ingest` partial commits | b, d, h: 🔴/🟠 „bug" | i, p, r: 🟡/💡 „design decision" | 🟡 Celowy design wg constitution — ale brak rollback w `match_or_create_item` to realny problem |
| `slowapi` EOL / overkill | m, p: 🟠 „zastąpić" | d, h: 🟢 „działa" | 🟡 Działa, ale in-memory limiter jest bezużyteczny przy `--workers 2` — to realne ograniczenie |
| fastapi-users overkill | g, m: 🟠 „custom auth ~80 LOC" | d, p: 🟢 „standard w ekosystemie" | 🟢 Uzasadnione dla MVP; przepisanie to overkill |
| `current_price` denormalizacja | d: 🟠 „premature" | p: 🟢 „zostawić wg constitution" | 🟢 Działa, jest testowane, chroni constitution — nie ruszać bez ADR |
| `price-history` bez auth | o: 🔴 „critical" | h, p: 🟡/💡 „może być design" | 🟡 GET publiczne to uzasadniony design; brak auth to nie automatycznie błąd |

---

## Podsumowanie w jednym zdaniu

14 z 14 kluczowych findings zostało potwierdzonych w kodzie. Najbardziej wartościowe audyty to **p.md** (kimi-k2.6 synteza) i **r.md** (Opus 4.7 synteza) — rzetelne severity, praktyczne quick wins, downgradują przesadzone sugestie. Najbardziej realistyczny (bez przesady) to **h.md** (gpt-5.4). Do pominięcia: `n.md`, `a.md`, `g.md` (zbyt krótkie lub subiektywne).

---

*Recenzja wykonana przez opencode-go/kimi-k2.6. Żadne zmiany w kodzie projektu nie zostały wprowadzone.*
