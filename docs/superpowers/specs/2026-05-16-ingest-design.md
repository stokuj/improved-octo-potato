# Ingest domain — design spec

**Status:** ready for review  
**Data:** 2026-05-16  
**Cel:** zbieranie cen z domu aukcyjnego ArcheRage do bazy projektu

---

## Decyzje podjęte w brainstormingu

| Decyzja | Wybór |
|---|---|
| Trigger zbierania | opportunistic (gracz otwiera AH) + manual button "Save now" |
| Mapowanie itemków | po `name + grade`, auto-create jeśli brak |
| Auth endpointu | brak na MVP, rate limit po stronie API |
| Format pliku addon↔watcher | JSONL (JSON Lines) |
| Liczba addonów | dev: 2-3 warianty równolegle dla iteracji, prod: 1 |

---

## Sekcja 1 — Architektura ogólna

```
┌─────────────────────────┐
│ ArcheRage (Windows)     │
│                         │
│  ┌──────────────────┐   │
│  │ pricetracker     │   │   1. User otwiera AH lub klika
│  │ (addon Lua)      │───┼──→  "Save now"
│  └────────┬─────────┘   │
│           │             │   2. Addon zapisuje JSONL
│           ▼             │
│  prices.jsonl           │
└───────────┬─────────────┘
            │
            │ (lokalny plik na PC)
            ▼
┌─────────────────────────┐
│ Python watcher (PC)     │   3. Watcher widzi nowe linie
│                         │      i POSTuje do API
│  - obserwuje plik       │
│  - parsuje JSONL        │
│  - POST /api/ingest    ─┼──→  HTTPS
│  - oznacza co wysłał    │
└─────────────────────────┘
                                ┌──────────────────────┐
                                │ Backend (FastAPI)    │
                                │                      │
                                │  /api/ingest/prices  │
                                │     │                │
                                │     ▼                │
                                │  match name+grade    │
                                │  → Item.id           │
                                │  (auto-create        │
                                │   jeśli brak)        │
                                │     │                │
                                │     ▼                │
                                │  add_price_point()   │
                                │     │                │
                                │     ▼                │
                                │  PostgreSQL          │
                                └──────────────────────┘
```

### Granice komponentów

| Komponent | Gdzie działa | Język | Odpowiedzialność |
|---|---|---|---|
| `pricetracker` (addon) | proces gry, Windows | Lua | przechwytuje wyniki AH, zapisuje JSONL do lokalnego pliku |
| `watcher` | PC gracza, w tle | Python | obserwuje plik, parsuje, POSTuje do backendu |
| `app/ingest/` (endpoint) | serwer (produkcja) | Python/FastAPI | mapuje name+grade → Item, tworzy PricePoint |

Każdy komponent jest niezależny — można testować osobno, można zamienić jeden bez ruszania pozostałych (np. addon na inny silnik gry, watcher na webhook, endpoint na inny format).

---

## Sekcja 2 — Komponenty

### `addon/pricetracker/` (Lua, w grze)

```
pricetracker/
├── toc.g                # spis plików ładowanych przez grę
├── apitypes.lua         # stałe UIEVENT_TYPE, API_TYPE (kopia z globals)
├── window.lua           # widget okna (kopia z globals)
├── button.lua           # widget przycisku (kopia z globals)
└── pricetracker.lua     # główna logika (~200 linii)
```

Odpowiedzialność:
- Hookuje `AUCTION_ITEM_SEARCHED` — przechwytuje wyniki gdy gracz przegląda AH
- Mały przycisk "Save now" w rogu ekranu — przy kliknięciu robi sweep ustalonej listy
- Dla każdego wyniku liczy najniższe `directPriceStr` i appenduje linię do `prices.jsonl`
- Pisze do chat systemowego (`X2Chat:DispatchChatMessage`) "Saved N prices" — tylko przy manualnym Save now

### `watcher/` (Python, na PC gracza)

```
watcher/
├── pyproject.toml
├── watcher.py          # główna pętla
├── config.py           # PATH_TO_JSONL, API_URL
└── README.md           # jak uruchomić na Windows
```

Odpowiedzialność:
- Czyta `prices.jsonl` od ostatniej pozycji (offset w `.watcher_state`)
- Dla każdej nowej linii: POST do `/api/ingest/prices`
- Retry przy błędach sieci (exponential backoff)
- Biblioteki: `httpx` + `watchdog` (cross-platform file watch)

### `backend/app/ingest/` (FastAPI domain)

```
backend/app/ingest/
├── __init__.py
├── schemas.py          # PriceIngestRow (request), IngestResponse
├── services.py         # match_or_create_item(), bulk_ingest()
└── router.py           # POST /api/ingest/prices
```

Odpowiedzialność:
- Przyjmuje listę `PriceIngestRow` (batch up to 100)
- Dla każdego: szuka `Item WHERE name=? AND grade=?`, tworzy jeśli brak
- Woła istniejące `prices.services.add_price_point(item_id, price, source="ah")`
- Zwraca raport: ile dodanych, ile auto-created, ile pominiętych

## Sekcja 3 — Data flow + format JSONL

### Format linii JSONL

```json
{"name":"Egg","grade":1,"price":15000,"ts":"2026-05-16T18:30:00","source":"ah"}
```

| Pole | Typ | Skąd | Opis |
|---|---|---|---|
| `name` | string | `info.name` | nazwa itemka z gry |
| `grade` | int | `info.grade` | 1=uncommon … 6=epic |
| `price` | int | `min(directPriceStr)` | najniższa cena kup-teraz, w miedzi |
| `ts` | string | `GetServerTimeTable()` | ISO 8601, czas serwera gry |
| `source` | string | stała | "ah" (MVP), w przyszłości np. "merchant" |

Cena trzymana **w miedzi** (najmniejsza jednostka). Konwersja do gold/silver/copper tylko na frontendzie. Zero floating point issues.

### Flow

1. **Addon (Lua)** — w handlerze `AUCTION_ITEM_SEARCHED`:
   - iteruje wyniki, szuka `min(directPriceStr) > 0`
   - jeśli znalazł — appenduje linię do `prices.jsonl` (atomowy write)

2. **Watcher (Python)** — pętla:
   - czyta nowe linie od `offset` (zapamiętany w `.watcher_state`)
   - paczkuje do batchy ≤100
   - `POST /api/ingest/prices` z `{"rows": [...]}`
   - na sukces: aktualizuje offset i zapisuje state
   - na błąd: exponential backoff, retry (offset zostaje)

3. **Endpoint `POST /api/ingest/prices`** — request:
   ```json
   {"rows": [{"name":"Egg","grade":1,"price":15000,"ts":"...","source":"ah"}, ...]}
   ```

   Response (200):
   ```json
   {"accepted": 12, "auto_created": 2, "skipped": 0, "errors": []}
   ```

4. **Service** — dla każdego row:
   - `match_or_create_item(name, grade)` → `Item.id`
   - `add_price_point(item_id, price, source, captured_at=ts)`
   - akumuluje statystyki

## Sekcja 4 — Error handling

Zasada: **żaden błąd nie zatrzymuje pipeline'u**. Pomijamy złe rekordy, nie blokujemy reszty.

### Warstwa addon (Lua)

| Sytuacja | Reakcja |
|---|---|
| Plik się nie otwiera | `if f then ... end` — silent skip, nie wieszamy gry |
| 0 wyników z AH | Nic nie zapisujemy (to nie błąd) |
| `directPriceStr == "0"` (tylko bid) | Pomijamy |
| `name == nil` / puste | Pomijamy linię |

Addon ma być cicho. Komunikaty (`X2Chat:DispatchChatMessage`) tylko dla manualnego "Save now".

### Warstwa watcher (Python)

| Sytuacja | Reakcja |
|---|---|
| Plik nie istnieje | Czekaj, sprawdzaj co 2s |
| Linia ma malformed JSON | Log warning, inkrement offset, idź dalej |
| Network error / timeout | Exponential backoff (2→4→8→max 60s), **offset bez zmian** |
| 4xx z backendu | Log warning, inkrement offset (linia zła, retry nie pomoże) |
| 5xx z backendu | Retry jak network error |
| Plik truncated (`size < offset`) | Wykryj, zresetuj offset do 0 |
| Crash watchera | Wznowienie z `.watcher_state`, dane nie giną |
| Duplicate przy retry | Akceptowalne — `PricePoint` to time-series |

### Warstwa backend (FastAPI)

Walidacja Pydantic per row:

```python
class PriceIngestRow(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    grade: int = Field(ge=1, le=6)
    price: int = Field(gt=0)
    ts: datetime
    source: str = Field(min_length=1, max_length=32)
```

| Sytuacja | Reakcja |
|---|---|
| Request malformed | 422 (FastAPI default) |
| Pojedynczy row nie spełnia walidacji | Pomijamy, do `errors[]`, response 200 |
| `ts` w przyszłości (>1h) | Pomijamy |
| Błąd DB na pojedynczym row | Pomijamy ten row, log, idziemy dalej |
| Batch >100 rows | 422 |
| Rate limit (per IP, np. 60 req/min) | 429 — `slowapi` lub własny middleware; do skonfigurowania w implementation plan |

### Idempotencja

MVP: akceptujemy duplikaty. `PricePoint` to time-series, identyczna cena w odstępie 1s jest legalna. Jeśli wykażemy że to problem — dodamy unique constraint `(item_id, source, captured_at)`.

### Raport response

```json
{
  "accepted": 18,
  "auto_created": 3,
  "skipped": 2,
  "errors": [
    {"row_index": 5, "reason": "price must be > 0"},
    {"row_index": 12, "reason": "grade out of range"}
  ]
}
```

## Sekcja 5 — Testing

Trzy warstwy, trzy strategie. Lua addonu nie da się porządnie testować jednostkowo (środowisko = gra) — manual plan. Backend i watcher: pełna automatyzacja.

### Backend (`backend/tests/test_ingest.py`)

Styl istniejącej apki: pytest async, fresh engine z NullPool. Pokrywamy każdą ścieżkę error handlingu.

| Test | Co weryfikuje |
|---|---|
| `test_ingest_creates_pricepoint_for_existing_item` | Item w seedzie, ingest tworzy `PricePoint` z poprawnym `item_id` |
| `test_ingest_auto_creates_unknown_item` | Brak Item → auto-create z `category=OTHER`, `auto_created=1` |
| `test_ingest_match_by_name_and_grade` | Dwa Itemy z tym samym name, innym grade → właściwy match |
| `test_ingest_skips_invalid_grade` | `grade=99` → do `errors[]`, reszta batcha przechodzi |
| `test_ingest_skips_negative_price` | `price=-100` → do `errors[]`, response 200 |
| `test_ingest_rejects_future_timestamp` | `ts = now + 2h` → do `errors[]` |
| `test_ingest_rejects_batch_over_100` | 101 rows → 422 |
| `test_ingest_partial_success_returns_200` | 5 dobrych + 2 złe → 200, `accepted=5, skipped=2` |
| `test_ingest_idempotent_for_duplicate_rows` | Ten sam row dwa razy → dwa `PricePoint` (akceptowalne) |
| `test_ingest_empty_batch` | `{"rows": []}` → 200, `accepted=0`, brak crasha |

### Watcher (`watcher/tests/test_watcher.py`)

Bez gry — tymczasowe pliki (`tmp_path`), `respx`/`httpx_mock` do API.

| Test | Co weryfikuje |
|---|---|
| `test_reads_lines_from_offset` | Plik ma 10 linii, offset=3, czyta linie 4-10 |
| `test_advances_offset_after_successful_post` | Po 200 state zapisuje nowy offset |
| `test_preserves_offset_on_network_error` | `ConnectError`, offset bez zmian, retry |
| `test_advances_offset_on_4xx` | 422 → offset idzie dalej |
| `test_retries_on_5xx` | 500 trzy razy, czwarty 200 → success |
| `test_detects_file_truncation` | `truncate(0)` → reset offsetu |
| `test_handles_malformed_json_line` | "not json" → skip, log warning, offset += len |
| `test_resumes_from_state_file` | Start z `.watcher_state` offset=500 |
| `test_batches_max_100_per_request` | 250 linii → 3 requesty (100+100+50) |

### Addon Lua — manual (plan w `addon/pricetracker/TESTING.md`)

1. **Smoke** — addon się ładuje (brak błędów w `ArcheRage.log`, widać przycisk "Save now")
2. **Opportunistic capture** — wyszukaj "Egg" na AH → linia w `prices.jsonl` z sensownymi wartościami
3. **Manual sweep** — klik "Save now" → kilka linii w pliku, toast w grze
4. **End-to-end** — watcher loguje "Posted 1 row, accepted=1", `PricePoint` w bazie
5. **Manual sweep — komunikat** — klik "Save now" → chat systemowy pokazuje "Saved N prices"

### CI

- Backend tests → istniejący `backend.yml` (nic nowego)
- Watcher tests → nowy `.github/workflows/watcher.yml`: `uv sync` + `pytest` w katalogu `watcher/`, bez bazy
