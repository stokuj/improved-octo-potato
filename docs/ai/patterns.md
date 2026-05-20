# Code Patterns & Gotchas

## Nowy moduł domenowy (backend) {#new-domain}

Struktura każdego modułu w `app/<domain>/`:
```
models.py    — SQLModel table classes
schemas.py   — Pydantic request/response schemas
services.py  — logika biznesowa (funkcje async, przyjmują session)
router.py    — FastAPI APIRouter, importuje services
admin.py     — sqladmin ModelAdmin (jeśli potrzebny panel)
__init__.py  — pusty
```

Rejestracja w `app/main.py`:
```python
from app.<domain>.router import router as domain_router
app.include_router(domain_router, prefix="/api/<domain>", tags=["<domain>"])
```

## Kolejność rejestracji routerów

`GET /api/inventory/for-recipe/{item_id}` **musi być zarejestrowany PRZED** `PUT /api/inventory/{item_id}`.
FastAPI dopasowuje ścieżki w kolejności rejestracji — `for-recipe` zostałby wchłonięty przez `{item_id}`.

## Rate limiter — singleton

`app/config/rate_limit.py` eksportuje jeden `limiter`. **Nigdy nie twórz drugiego.**
Użycie w routerze:
```python
from app.config.rate_limit import limiter
@router.post("/")
@limiter.limit("60/minute")
async def endpoint(request: Request, ...):
```

## Auth dependencies

```python
from app.auth.dependencies import current_active_user, current_superuser
# current_active_user — wymagane zalogowanie
# current_superuser   — tylko superuser
```

## Ingest — partial success contract

`POST /api/ingest/prices` zawsze zwraca 200 z `errors[]`. Nigdy 4xx dla złych wierszy.
Tylko 429 (rate limit) i 5xx triggerują retry po stronie klienta.
Po nieudanym `add_price_point` zawsze rób `session.rollback()` — bez tego session jest trucizna dla kolejnych wierszy w batchu.

## UserInventory upsert

- `quantity > 0` → `ON CONFLICT DO UPDATE` (atomic)
- `quantity = 0` → `DELETE` bezpośrednio
- Nigdy SELECT-then-delete

## Testy — UUID suffix w nazwach itemów

DB nie jest czyszczona między testami (rollback per-test). `UniqueConstraint(name, grade)` na `Item`.
Każdy test musi używać unikalnych nazw — dodaj UUID suffix:
```python
suffix = str(uuid.uuid4())[:8]
item_name = f"Iron Ore {suffix}"
```

## Testy — prawdziwa baza, bez mocków

Testy biją w PostgreSQL `app_test`. Historia: mocki ukryły błąd produkcyjnej migracji.
Conftest tworzy tabele przez `create_all` (alembic nie jest odpalany w testach).

## Frontend — importy ze shared lib

`formatCurrency` i `LABOUR_ITEM_NAME` importuj **wyłącznie** z `$lib/currency` i `$lib/crafting`.
Nigdy nie redefiniuj lokalnie — `ItemTable.svelte` ma historyczny bug (lokalna kopia `splitCurrency`).

## Frontend — auth state

`src/lib/auth.svelte.ts` to globalny singleton (`$state user`). Sprawdzany raz w `+layout.svelte`.
Wszystkie fetche używają `credentials: 'include'` (JWT w cookie).

## Frontend — typy API

`src/lib/api.d.ts` jest **auto-generowany** przez `openapi-typescript` z `/openapi.json`.
Nie edytuj ręcznie. `src/lib/types.ts` re-eksportuje stamtąd + dodaje lokalne typy (`ChartPoint`, `NodeOverride`).

## Naive UTC w DB

Nigdy nie zapisuj timezone-aware datetime. Strip `tzinfo` przed zapisem:
```python
dt.replace(tzinfo=None)
```

## CraftResult.batch_profit

To profit dla całego batcha (market_price × output_qty × multiplier − total_material_cost), **nie** per single craft.

## Podman, nie Docker

Projekt używa `podman compose`, nie `docker compose`. Makefile ma odpowiednie targets.
