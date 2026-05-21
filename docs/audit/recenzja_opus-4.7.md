# Recenzja audytów — Opus 4.7

**Data:** 2026-05-21
**Recenzent:** Claude Opus 4.7 (`claude-opus-4-7`)
**Zakres:** 17 plików w `docs/audit/` (a.md – r.md)
**Metoda:** odczyt każdego audytu + weryfikacja kluczowych twierdzeń 3 równoległymi subagentami Explore (read-only) przeciw aktualnej bazie kodu `main @ d0175bf`.

---

## 1. Wynik weryfikacji kluczowych twierdzeń

| # | Twierdzenie | Werdykt |
|---|---|---|
| 1 | `match_or_create_item` commit per-row + brak rollback | ✅ TRUE (`ingest/services.py:46,88`) |
| 2 | Duplikat `authentication_backend` w `admin_auth.py:46,67` | ✅ TRUE |
| 3 | Hardcoded secret defaults w `settings.py` | ✅ TRUE |
| 4 | CORS `allow_methods=["*"]` + `allow_headers=["*"]` | ✅ TRUE |
| 5 | `/api/items/{id}/price-history` bez auth | ✅ TRUE |
| 6 | `/auth/login`, `/auth/register` bez rate limitu | ✅ TRUE |
| 7 | Publiczny `POST /api/ingest/prices` bez auth | ✅ TRUE |
| 8 | `utcnow()` zduplikowane ×4 modułów | ✅ TRUE |
| 9 | Global `$state` w `auth.svelte.ts` + adapter-node SSR | ✅ TRUE |
| 10 | TypeScript `^6.0.2` (anomalna wersja) | ✅ TRUE (`package.json:25`) |
| 11 | `UserRead` schema niezgodna z serializerem (`is_superuser`/`is_active`/`is_verified`) | ✅ TRUE |
| 12 | `EChartsLineChart.svelte` `@ts-nocheck` | ✅ TRUE |
| 13 | `RecipeTree.svelte` recursja bez maxDepth | ✅ TRUE |
| 14 | `computeNodeCost` zduplikowane w 2 plikach | ✅ TRUE |
| 15 | Zero testów frontendu | ✅ TRUE |
| 16 | Wszystkie 3 Dockerfile bez `USER` | ✅ TRUE |
| 17 | Caddyfile bez security headers + admin API on | ✅ TRUE |
| 18 | Discord bot poza docker-compose | ✅ TRUE |
| 19 | slowapi `get_remote_address` = jeden bucket za Caddy (brak `--proxy-headers`) | ✅ TRUE |
| 20 | `discord_bot/.env` z jawnym tokenem (m.md) | ❌ FALSE (plik nie istnieje) |
| 21 | `ingredient_item_id` jako "literówka CRITICAL" (g.md) | ❌ FALSE (świadoma konwencja, używana spójnie) |
| 22 | `npm run check` fails na `PUBLIC_API_URL` (h.md F6) | ⚠️ PARTIAL (obecnie przechodzi) |
| 23 | cookie `<0.7.0` CVE (o.md) | ⚠️ PARTIAL (lockfile=0.6.0 jest vulnerable, ale fix dostępny) |
| 24 | PyJWT CVE (r.md) | ⚠️ PARTIAL (brak explicit dep w `pyproject.toml` — transitive) |

**Podsumowanie:** ~20/24 zweryfikowanych twierdzeń to TRUE. Większość krytycznych ustaleń jest realna i potwierdzona w kodzie.

---

## 2. Ranking audytów

Kryteria: (A) trafność twierdzeń weryfikowalnych w kodzie, (B) waga znalezisk, (C) jakość syntezy / rozwiązywanie konfliktów, (D) konkretność (ścieżki + effort), (E) coverage (backend + frontend + infra + bot).

| Pozycja | Plik | Model | Ocena | Mocne strony | Słabości |
|---|---|---|---|---|---|
| 🥇 **1** | **r.md** | Opus 4.7 (synth) | **9.5/10** | Synteza z second-opinion, downgrade przesadzonych findings (visionary), tabela A–H z effortem (~3h = 50% findings), werdykty w konfliktach, health snapshot per domena | Brak detali per-finding (są w źródłowych raportach, ale tu nie zalinkowane) |
| 🥈 **2** | **p.md** | kimi-k2.6 (synth) | **9.0/10** | Identyfikuje 2 unikalne TRUE które inni przegapili: TS ^6.0.2 i UserRead OpenAPI drift; bardzo zorganizowany; eksplicytna sekcja konfliktów + werdyktów | Zaufanie do "hardcoded secrets = 🔴" mimo że istnieje validator >=32 chars (r.md trafniej daje 🟡) |
| 🥉 **3** | **a.md** | (nieoznaczony) | **8.5/10** | Najgęstszy signal/noise (56 linii, 2 TRUE krytyki, oba potwierdzone); precyzyjne `file:line` | Wąski zakres — pomija infra/security/bot |
| **4** | **h.md** | gpt-5.4 | **8.0/10** | Najlepszy frontend audit (F1–F6 trafne, każdy z `why it matters`); explicytna "Review Progress" checklist | F6 (PUBLIC_API_URL) okazał się partial; brak severity Critical — pomija ingest/auth |
| **5** | **e.md** | GLM-5.1 | **7.5/10** | Strategiczna perspektywa (S1–S5); poprawnie wskazuje anon ingest jako CRITICAL; identyfikuje auth→profiles coupling | Niektóre "Modern Python gaps" są nice-to-have nie problem |
| **6** | **o.md** | minimax-m2.7 (synth) | **7.5/10** | Dobra tabela top-10, eksplicytne konflikty + resolution; rozpoznaje że "skeptic zawyża severity" | Cookie CVE wspomniany — częściowo (lockfile faktycznie ma 0.6.0 = vulnerable) |
| **7** | **c.md** | qwen3.6-plus | **7.0/10** | Zwarte exec summary z liczbami, ~20 findings, większość TRUE; konkretne `file:line` | Brak syntezy/priorytetyzacji między obszarami |
| **8** | **d.md** | kimi-k2.6 | **7.0/10** | Solidny backend deep-dive PL; trafnie wyłapuje cross-domain coupling, routing overlap | Brak frontend/infra coverage |
| **9** | **b.md** | qwen3.6-plus-free | **6.5/10** | Najszczegółowsze raporty B-001…B-???, wszystkie TRUE | 651 linii — rozdmuchany; brak rankingu/syntezy; severity drift (utcnow dup = HIGH?) |
| **10** | **k.md** | opencode | **6.0/10** | Wielo-subagentowa szerokość (12 perspektyw) | 1673 linie — kosztowna w czytaniu; dużo redundancji |
| **11** | **m.md** | opencode | **5.5/10** | Pretensjonalna synteza ze "154 findings" | Discord token w .env = FALSE; price-history "DoS bez LIMIT" przesadzone |
| **12** | **f.md** | deepseek-v4-pro | **5.5/10** | Tabela severity z licznikami; szczegółowa | Severity inflation: brak `profiles/admin.py` jako HIGH ×3, empty lifespan jako HIGH — to nie HIGH |
| **13** | **n.md** | (nieoznaczony synth) | **5.0/10** | Minimalna ale trafna lista | Zbyt ogólne ("ItemTable hotspot") bez `file:line`; ledwie synteza |
| **14** | **l.md** | (nieoznaczony) | **4.5/10** | Bardzo dokładny context (stack, mapa warstw) | 2001 linii w dużej mierze opisu, niska gęstość findings |
| **15** | **i.md** | deepseek-v4-pro | **4.0/10** | Context + plan audytu | Słabo actionable — to bardziej draft procesu niż wnioski |
| **16** | **g.md** | minimax-m2.7 | **3.5/10** | Krótki, śledzi konkretne pliki | "ingredient_item_id typo CRITICAL" błędne (świadoma konwencja); "DELETE bez flush" miesza `exec()` z `execute()` |
| **17** | **j.md** | Gemini 3.1 Pro | **2.0/10** | (brak — niedokończony) | Sam autor: "brakuje perspektyw: second-opinion, skeptic, visionary oraz finalnej syntezy" |

---

## 3. Wnioski meta

### Konsensus krytyczny (≥4 audytów + kod potwierdza)
- publiczny ingest bez auth
- duplikat `authentication_backend`
- commit-per-row w ingest / brak rollback
- brak rate-limit na `/auth/*`
- root w Dockerfile (×3)
- brak headerów bezpieczeństwa w Caddy
- slowapi za Caddy bez `--proxy-headers` = jeden globalny bucket
- zero testów frontendu

### Najlepszy "single source"
**r.md** (synteza Opus 4.7) — jako jedyna jawnie obniża przesadzone severity (Visionary's TimescaleDB/tRPC/WebSocket) i daje effort breakdown na konkretne fixy A–H.

### Najlepszy odkrywca unikalnych TRUE
**p.md** — wyłapał TS `^6.0.2` i UserRead OpenAPI drift, których nie widać w innych raportach.

### Najsłabsze
- **j.md** — explicitly niedokończony
- **g.md** — technicznie błędne CRITICAL ("typo" + mylenie SQLModel `exec`/`execute`)

### Wzorzec drift across audits
Audytorzy systematycznie przeszacowują severity dla code-smell:
- duplikacja `utcnow()` → HIGH (realnie LOW)
- empty `lifespan` → HIGH (realnie INFO)
- brak `profiles/admin.py` → HIGH (subiektywne, nie krytyczne)

Realne 🔴 Critical to ~5–7 issue, nie 9–20 jak deklarują niektóre raporty (m.md, f.md, k.md).

### Najczęściej powtarzane FALSE / przesadzone twierdzenia
- "TimescaleDB potrzebny" (visionary w wielu) — przy 29 itemach × 30 dni zwykły Postgres + index wystarcza
- "tRPC / TanStack Query" — SvelteKit `load()` rozwiązuje to natywnie
- "Real-time WebSocket/SSE krytyczny" — przy skali projektu (~5 użytkowników) to over-design
- "Cookie CVE krytyczny" — patch dostępny, faktycznie low effort fix
- "fastapi-users over-engineering" — minimum viable, ręczna implementacja nie zaoszczędzi LOC

---

## 4. Rekomendowana kolejność czytania

Jeśli ktoś ma czas tylko na 1 plik: **r.md**.
Jeśli na 2: **r.md** + **p.md** (dla TS ^6.0.2 i OpenAPI drift).
Jeśli na 3: dodaj **h.md** (frontend deep-dive).
Pozostałe pomijaj — duplikują ustalenia.
