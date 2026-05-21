# Recenzja audytów — GLM-5.1

**Data:** 2026-05-21
**Model recenzenta:** opencode-go/glm-5.1
**Scope:** 17 plików audytowych w `docs/audit/` (a–r)
**Metodologia:** weryfikacja subagentami (3x explore) twierdzeń z audytów vs faktyczny kod źródłowy

---

## 1. Wyniki weryfikacji

Z 50 sprawdzonych twierdzeń z audytów:

| Werdykt | Liczba | % |
|---------|--------|---|
| TRUE | 39 | 78% |
| PARTIALLY TRUE | 4 | 8% |
| FALSE | 1 | 2% |
| Brak weryfikacji runtime | 6 | 12% |

### Kluczowy błąd powielany przez większość audytów

**`SecureAdminAuth.middlewares` jest martwym kodem** — twierdzenie FALSE powielone w **9 z 17 audytów** (b, c, d, e, g, j, k, l, m).

Fakty: sqladmin's `AuthenticationBackend.__init__` sam definiuje `self.middlewares`. `BaseAdmin.__init__` czyta `authentication_backend.middlewares` i przekazuje do `Starlette(middleware=middlewares)`. `SecureAdminAuth` poprawnie nadpisuje ten atrybut, by dostosować cookie sesji (`https_only`, `same_site`). To NIE jest martwy kod.

Audyty, które poprawnie nie twierdziły o martwym kodzie middlewares: h.md (gpt-5.4), r.md (Opus 4.7).

### Pozostałe błędy

- **TypeScript `^6.0.2`** — audit p (kimi-k2.6) twierdzi ze to anomalia. Weryfikacja potwierdza: `frontend/package.json:25` ma `"typescript": "^6.0.2"`. To rzeczywiście nietypowe.
- **Caddy glob `/admin*`** — audit f (deepseek-v4) twierdzi ze `/admin*` matchuje za broadly i missuje sub-paths. Częściowo prawda, zależy od wersji Caddy.
- **Bucketing tz-aware stripping** — audity c, k twierdzą ze tzinfo jest silently stripped. Weryfikacja: tz-aware datetimes NIE są stripped — one persist w response jako `+00:00`. Prawdziwy problem to inconsistency między raw (naive) i bucketed (aware).

---

## 2. Ranking audytów

| # | Plik | Model | Linie | Ocena | Uzasadnienie |
|---|------|-------|-------|-------|-------------|
| 1 | r.md | Opus 4.7 | 142 | **9.0** | Najlepsza akcyjność — konkretne estymaty effort ("3h naprawia >50% findings"), sekcja "decline/nie rób", jedyny co poprawnie zidentyfikował split secrets i dał praktyczną roadmapę. Minimalny false-positive. |
| 2 | h.md | gpt-5.4 | 265 | **8.5** | Jedyny z dowodami runtime (uruchomił pytest i svelte-check). Świetne "Why it matters" przy każdym finding. Znalazł race condition w add_price_point i niespójności w dokumentacji. Niskie false-positive. |
| 3 | e.md | GLM-5.1 | 432 | **8.3** | Najszerszy zakres strategiczny — jedyny co poruszył CSRF, containers-as-root, CSP headers, TypeScript ^6.0.2. Dobra faza remediacji. Ale: powiela błąd SecureAdminAuth.middlewares i trochę zawyża severity. |
| 4 | k.md | opencode | ~900 | **8.0** | Najdokładniejszy multi-subagent, znalazł SQL injection przez ILIKE (unikalny), self-correcting (sam wyłapał false alarm N+1). API contract validation table. Minus: trudny do parsowania, dużo redundancji. |
| 5 | p.md | kimi-k2.6 synth | 179 | **7.8** | Znalazł TypeScript ^6.0.2 i UserRead schema mismatch. Dobry second-opinion z konfliktami. Praktyczne quick wins. Ale: powiela błąd middlewares, jest syntezą a nie audytem pierwotnym. |
| 6 | f.md | deepseek-v4-pro | 645 | **7.5** | Jedyny audytujący addon Lua — unikalny. Bardzo dokładny infra. Ale: niektóre severity zawyżone, błąd middlewares, debatable claim o Caddy glob. |
| 7 | b.md | qwen3.6-free | 651 | **7.4** | Bardzo szczegółowy (34 findings), dobre rekomendacje z kodem. Ale: błąd middlewares, trochę severity inflation, mało unikalnych findings vs inne. |
| 8 | d.md | kimi-k2.6 | 231 | **7.3** | Dobry priority ranking (P0-P3), czysta struktura, praktyczny. Znalazł brak warstwy API service. Ale: błąd middlewares, nie znalazł kilku ważnych problemów. |
| 9 | j.md | Gemini 3.1 | 299 | **7.0** | Nieukończony ale znalazł CVE PyJWT i INT overflow. Dobry dependencies analysis. Minus: brak syntezy, błąd middlewares. |
| 10 | c.md | qwen3.6-plus | 255 | **6.5** | Kompletny ale drastyczna inflacja severity — 20 "Critical" to za dużo. Błąd middlewares. Dobre frontend catches (SubmitEvent, dead bindings). |
| 11 | m.md | opencode synth | 563 | **6.5** | Dobra synteza z second-opinion, self-correcting. Ale: dziedziczy błędy subagentów, mało unikalnych findings vs k.md. |
| 12 | i.md | deepseek-v4 sub | 419 | **6.3** | Multi-perspektywa, ale duże overlapy z f.md. Znalazł crafting calculator bug. Błąd middlewares. Dużo pustych linii na końcu. |
| 13 | a.md | nieznany | 56 | **6.2** | Zwięzły, skupiony na krytycznych. Poprawny co do transaction leak i SSR state. Ale: bardzo płytki, brak infra/security. |
| 14 | o.md | minimax synth | 163 | **6.0** | Znalazł price-history bez auth. Rozsądne quick wins. Ale: price-history publiczny może być celowy. Ograniczony zakres. |
| 15 | g.md | minimax-m2.7 | 269 | **5.5** | Jedyny CRITICAL to literówka `ingredient_item_id` — to NIE jest critical (nazwa jest spójna w kodzie). Błąd middlewares. Płytka analiza. |
| 16 | l.md | multi-subagent | ~900 | **5.3** | Trudny do parsowania (combined format). Dobre API contract validation, ale duże overlapy z k.md. Błąd middlewares. |
| 17 | n.md | synthesis | 40 | **4.0** | Zbyt krótki, brak szczegółów, brak dowodów. Wszystko na poziomie ogólników. |

---

## 3. Najważniejsze findings (potwierdzone)

| # | Finding | Severity | Kto znalazł (najpierw/najlepiej) |
|---|---------|----------|----------------------------------|
| 1 | Publiczny ingest bez auth + rate limit na IP proxy | 🔴 | e, h, k, p, r |
| 2 | Containers jako root (brak USER w Dockerfile) | 🔴 | e, f, h, k, p, r |
| 3 | Hardcoded default secrets w settings | 🔴 | b, c, d, e, g, h, k, p, r |
| 4 | SQL injection przez ILIKE (`%` i `_` nie escaped) | 🟠 | k (jako jedyny) |
| 5 | Race condition w `add_price_point` (concurrent current_price) | 🟠 | h (jako jedyny z dowodem) |
| 6 | Brak rate limit na `/auth/login` i `/auth/register` | 🟠 | e, h, p, r |
| 7 | Brak security headers w Caddy (HSTS, CSP, X-Frame-Options) | 🟠 | e, f, h, k, r |
| 8 | `match_or_create_item` commituje przed `add_price_point` — brak atomowości | 🟠 | a, b, c, d, h, k |
| 9 | Silent failure w `get_inventory_for_recipe` (AppError → `{}`) | 🟠 | d, h, k |
| 10 | Brak rollback po błędzie `match_or_create_item` w `_process_row` | 🟠 | a, h, k |
| 11 | `computeNodeCost` zduplikowana w 2+ komponentach | 🟡 | b, c, d, e, f, h, k |
| 12 | `@ts-nocheck` w EChartsLineChart | 🟡 | b, c, d, e, f, h, k |
| 13 | `(row: any)` w price history mapping | 🟡 | b, c, d, e, f, h, k |
| 14 | Hardcoded CATEGORIES/GRADES w frontend | 🟡 | b, c, d, e, k |
| 15 | Zero testów frontendowych | 🟡 | b, c, d, e, h, k, p, r |
| 16 | `utcnow()` zduplikowana w 4-5 plikach | 🟡 | b, c, d, e, g, k, r |
| 17 | Nowy httpx.AsyncClient per request w Discord bocie | 🟡 | c, d, e, f, h, k |
| 18 | Brak `on_app_command_error` w Discord bocie | 🟡 | c, d, e, h, k |
| 19 | UserRead OpenAPI schema niezgodna z runtime (serializer usuwa pola) | 🟡 | j, p |
| 20 | TypeScript `^6.0.2` — nietypowa/nieistniejąca wersja | 🟡 | p |

---

## 4. Findings niepotwierdzone / false positive

| Finding | Audyt | Powód odrzucenia |
|---------|-------|-------------------|
| `SecureAdminAuth.middlewares` jest martwym kodem | b, c, d, e, g, j, k, l, m | FALSE — sqladmin czyta ten atrybut w BaseAdmin.__init__ i przekazuje do Starlette. Poprawny extension point. |
| `ingredient_item_id` to literówka | g | FALSE — nazwa jest spójnie używana w całym kodzie. Zmiana wymagałaby migracji DB za cos co jest po prostu długą nazwą, nie błędem. |
| Bucketing "silently strips" tzinfo | c, k | MISLEADING — tz-aware datetimes persistują w response jako `+00:00`. Prawdziwy problem to inconsistency między raw (naive) i bucketed (aware). |
| `ItemTable.svelte` (349 LOC) to "god component" | c, d, e, k | DEBATABLE — 349 LOC w SvelteKit z template + styles to nie jest god object. Drug-opinion w r.md zgodził się: "367 LOC w SvelteKit z styles to nie god object". |
| CORS `allow_methods=["*"]` jest krytyczne | c, e, r | LOW — z konkretnymi `allow_origins` jest to OK per CORS spec. Umiarkowane zawyżenie severity. |

---

## 5. Luki w pokryciu — czego żaden audyt nie znalazł

| Luka | Opis |
|------|-------|
| `seed.py` nie ustawia `last_price_at` | Po seedowaniu `last_price_at` jest None dla wszystkich itemów — wpływa na logikę `add_price_point`. Tylko k.md o tym wspomniał (🟡). |
| `asyncio_default_test_loop_scope = "session"` | Testy dzielą jeden event loop — potencjalny source flakiness. Tylko k.md o tym wspomniał. |
| Frontend `data-sveltekit-preload-data="hover"` bezużyteczne | Bez load functions preload nie działa. Tylko e.md o tym wspomniał. |
| `docker-compose.prod.yml` CORS_ORIGINS interpolation | Interpolacja `${APP_DOMAIN}` wewnątrz JSON string może nie zadziałać. Tylko l.md o tym wspomniał. |

---

## 6. Kryteria oceny

| Kryterium | Waga | Opis |
|-----------|------|------|
| **Accuracy** | 30% | Odsetek twierdzeń potwierdzonych przez weryfikację |
| **Uniqueness** | 20% | Findings unikalne dla danego audytu vs powielone z innych |
| **Actionability** | 20% | Konkretne rekomendacje z effort estymatami |
| **Severity calibration** | 15% | Wyważone severity vs inflacja/deflacja |
| **Runtime evidence** | 15% | Dowody z uruchomienia (testy, typecheck, build) |
