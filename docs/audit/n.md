# synthesis

## TL;DR
1. 🟠 Ingest ma zbyt rozdzielony boundary transakcyjny i może zostawiać stan pośredni.
2. 🟠 `ItemTable.svelte` jest największym hotspotem utrzymaniowym frontendu.
3. 🟠 Caddy/front-end mają niespójność wokół portu i hostowania.
4. 🟠 Auth state na froncie jest zbyt side-effectowy i trudny do testowania.
5. 🟡 `get_inventory_for_recipe()` jest sprzężone z crafting tree bardziej niż powinno.
6. 🟡 Publiczny ingest opiera się głównie na rate limit, nie na auth.
7. 🟡 CI nie łapie pełnego deployment contract end-to-end.
8. 🟡 Wiele domain strings/map jest rozproszonych między backendem, botem i frontendem.
9. 🟢 Logger/auth i kilka martwych parametrów to czyszczenie jakościowe.
10. 🟢 Część zależności i decyzji architektonicznych jest świeża, ale nie wygląda na krytyczny problem sama w sobie.

## Krytyczne
- `backend/app/ingest/services.py` + `backend/app/prices/services.py`: write-flow powinien być traktowany jako jedna z najwyższych prioritów technicznych.
- `infra/caddy/Caddyfile` + `frontend/Dockerfile`: sprawdzić i ujednolicić kontrakt portu frontendu przed kolejnym deployem.

## Wzorce powtarzające się
- Rozproszone domenowe stringi i mapowania: backend, frontend, discord bot.
- Zbyt grube granice funkcji/komponentów: `ItemTable.svelte`, auth state, ingest services.
- Kontrakty integracyjne zależne od konwencji i kolejności: routing inventory, source `ah`, port frontendu.
- Testy istnieją, ale częściej chronią pojedyncze invarianty niż cały deploy flow.

## Konflikty opinii
- `skeptic` sugeruje, że `ItemTable` virtual scrolling może być overkill; `second-opinion` uznaje hotspot za realny problem, ale nie przesądza o konieczności usuwania scrolla.
- `dependencies` traktuje świeżość stacku jako ryzyko monitorowane, nie bug; `security` nie widzi tu bezpośredniego problemu.
- `visionary` chce wspólnego słownika domenowego; `second-opinion` uważa to za sensowny refactor, ale nie natychmiastowy defect.

## Top 3 quick wins
1. Ujednolicić kontrakt portu frontendu między Caddy i Dockerfile.
2. Usunąć martwy parametr `request` z `backend/app/prices/router.py`.
3. Rozdzielić logger zamiast `print()` w `backend/app/auth/manager.py`.

## Long-term roadmap
- Transakcyjny refactor ingestu i price update.
- Rozdzielenie `ItemTable.svelte` na controller/view.
- Centralny słownik domenowy dla grade/source/category.
- Wydzielenie czystych helperów dla crafting/inventory traversal.
- Dodatkowy smoke test deploymentowy dla całego stacku.
