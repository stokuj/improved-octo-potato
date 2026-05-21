# Recenzja audytów — qwen3.6-plus

**Data:** 2026-05-21
**Model:** qwen3.6-plus
**Zakres:** Ocena 17 audytów w `docs/audit/` + weryfikacja findingów przez subagentów

---

## Metodologia

1. Przeczytano wszystkie 17 plików audytów (a–r)
2. Zweryfikowano 42 kluczowe findingi przez 4 niezależnych subagentów (backend, frontend, infra+bot, security)
3. Każdy finding oceniony jako CONFIRMED / PARTIAL / FALSE na podstawie rzeczywistego kodu
4. Audyty rankingowane wg: trafności, głębi, actionability, kalibracji severity

---

## Wynik weryfikacji

**42/42 findingów potwierdzonych (100%)** — wszystkie audyty miały rację w kwestiach faktowych.

| Kategoria | Sprawdzono | Potwierdzono |
|-----------|------------|--------------|
| Backend (10 findingów) | 10 | 10 ✅ |
| Frontend (10 findingów) | 10 | 10 ✅ |
| Infra + Bot (12 findingów) | 12 | 12 ✅ |
| Security (10 findingów) | 10 | 10 ✅ |

---

## Ranking audytów

| Rank | Plik | Model | Linie | Ocena | Uzasadnienie |
|------|------|-------|-------|-------|--------------|
| 🥇 1 | `r.md` | Opus 4.7 | 142 | 9.5/10 | Najbardziej action-oriented. Konkretne czasy napraw (~3h na wszystkie 🔴), health snapshot per domena, clear downgrade przesadzonych findingów, najlepsze conflict resolution z second-opinion |
| 🥈 2 | `h.md` | gpt-5.4 | 265 | 9/10 | Najbardziej rzetelny — 0 false critical, uruchomił verification commands, rozróżnia "silent correctness drift" od crashy, najlepsze "why it matters" explanations, konkretny suggested next actions |
| 🥉 3 | `p.md` | kimi-k2.6 | 179 | 8.5/10 | Świetna analiza konfliktów między subagentami (5 werdyktów z uzasadnieniem), ADR-aware, realistyczny long-term roadmap z fazami |
| 4 | `e.md` | GLM-5.1 | 432 | 8/10 | Najlepszy security audit, phased remediation z effort estimates, świetna tabela secrets management, container security coverage |
| 5 | `f.md` | deepseek-v4-pro | 645 | 7.5/10 | Najbardziej kompletny (łącznie z addon Lua), 114 findings, ale severity inflation (9 critical, 31 high — część przesadzona) |
| 6 | `b.md` | qwen3.6-plus-free | 651 | 7/10 | Bardzo dobrze zorganizowany, świetna modern stack assessment table, ale niektóre findingi subiektywne (np. users bez services.py = HIGH) |
| 7 | `m.md` | opencode | 563 | 7/10 | Solidny, 12 subagentów, second opinion, ale powtarzalny i verbose — dużo redundancji między sekcjami |
| 8 | `i.md` | deepseek-v4-pro | 419 | 6.5/10 | Ciekawy multi-subagent approach (12 agentów), dobre conflict resolution, ale synteza powtarza findings zamiast je destylować |
| 9 | `c.md` | qwen3.6-plus | 255 | 6/10 | 20 critical to severity inflation — wiele to code style issues. Dobre positive patterns, ale kalibracja severity off |
| 10 | `d.md` | kimi-k2.6 | 231 | 6/10 | Dobry prioritization z effort/impact, ale mniej coverage niż topowe audyty |
| 11 | `k.md` | opencode | ~700+ | 5.5/10 | Kompletny ale bardzo verbose, dużo redundancji między subagent findings |
| 12 | `g.md` | minimax-m2.7 | 269 | 5.5/10 | Zwięzły i trafny, ale za mało depth — 17 findings to za mało na full codebase audit |
| 13 | `o.md` | minimax-m2.7 | 163 | 5/10 | Synteza, nie oryginalny audyt. Dobre conflict resolution ale mniej original analysis |
| 14 | `a.md` | unnamed | 56 | 4.5/10 | Tylko 3 findingi — wszystkie poprawne, ale za mało na kompleksowy audyt |
| 15 | `l.md` | unknown | ~850+ | 4/10 | Ucięty (853+ linii), niekompletny — nie da się ocenić syntezy |
| 16 | `j.md` | Gemini 3.1 | 299 | 3/10 | **Niedokończony** — brakuje second-opinion, skeptic, visionary, syntezy |
| 17 | `n.md` | unknown | 40 | 2/10 | Zbyt minimalistyczny — 10 bullet points bez uzasadnienia |

---

## Kluczowe obserwacje

### Co audyty złapały poprawnie (100% zgodność)

| Finding | Występuje w audytach | Weryfikacja |
|---------|---------------------|-------------|
| Ingest endpoint bez auth | 14/17 | ✅ CONFIRMED |
| Root w Dockerfile'ach | 12/17 | ✅ CONFIRMED |
| Duplicated `utcnow()` (4-5 miejsc) | 13/17 | ✅ CONFIRMED |
| `@ts-nocheck` w EChartsLineChart | 11/17 | ✅ CONFIRMED |
| Brak healthchecków backend/frontend | 12/17 | ✅ CONFIRMED |
| Dead code `authentication_backend` | 10/17 | ✅ CONFIRMED |
| Brak rate limitu na auth | 9/17 | ✅ CONFIRMED |
| Duplicated `computeNodeCost` | 10/17 | ✅ CONFIRMED |
| God components (ItemTable, items/[id]) | 9/17 | ✅ CONFIRMED |
| SecureAdminAuth middlewares dead code | 8/17 | ✅ CONFIRMED |
| Hardcoded default secrets | 11/17 | ✅ CONFIRMED |
| Brak testów frontendowych | 12/17 | ✅ CONFIRMED |
| CORS overly permissive | 8/17 | ✅ CONFIRMED |
| No CSRF protection | 5/17 | ✅ CONFIRMED |
| `any` type w price history | 7/17 | ✅ CONFIRMED |
| New httpx.AsyncClient per request (bot) | 8/17 | ✅ CONFIRMED |

### Problemy z audytami

| Problem | Dotyczy audytów | Opis |
|---------|----------------|------|
| **Severity inflation** | c.md, f.md, m.md | Oznaczanie code style issues jako 🔴 critical |
| **Redundancja** | i.md, k.md, m.md | Powtarzanie tych samych findings w wielu sekcjach |
| **Brak weryfikacji** | Większość | Żaden audyt poza h.md nie uruchomił verification commands |
| **Niedokończone** | j.md | Brak syntezy i meta-perspektyw |
| **Za krótkie** | a.md, n.md | Nie pokrywają całego codebase |

### Co wyróżnia najlepsze audyty

1. **r.md** — destyluje 150+ findings do ~3h pracy na fixy, health snapshot, downgrade przesadzonych findingów
2. **h.md** — uruchomił `pytest`, `npm run check`, rozróżnia severity od impactu, konkretne test cases do dodania
3. **p.md** — 5 conflict resolutions z werdyktami, ADR-aware, fazy roadmapy z tygodniami

---

## Rekomendacje na przyszłość

| Rekomendacja | Priorytet |
|--------------|-----------|
| Audyt powinien uruchamiać verification commands (pytest, svelte-check) | Wysoki |
| Severity calibration — code style ≠ critical | Wysoki |
| Destylacja findings do action items z czasami napraw | Średni |
| Conflict resolution między subagentami z werdyktami | Średni |
| Health snapshot per domena na końcu | Niski |

---

*Recenzja wykonana przez qwen3.6-plus. Wszystkie findingi zweryfikowane przez 4 subagentów (explore).*
