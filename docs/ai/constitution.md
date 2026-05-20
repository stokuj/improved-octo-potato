# Constitution

Zasady niezmienne projektu. Zmieniaj tylko po przemyślanej decyzji i z komentarzem dlaczego.

## API

- Wszystkie endpointy pod `/api/` — admin pod `/admin` (nie pod `/api`)
- Ingest endpoint (`/api/ingest/prices`) jest **bez auth** — tylko rate limit 60/min
- Partial success: ingest zawsze zwraca 200 z `errors[]`, nigdy 4xx dla złych wierszy
- `source='ah'` musi być używane spójnie przez seed, bota i frontend chart

## Baza danych

- **Naive UTC** wszędzie — nigdy timezone-aware datetime w DB
- `Item.current_price` aktualizowany **w tej samej transakcji** co nowy PricePoint
- `UserInventory` upsert: quantity > 0 → ON CONFLICT UPDATE; quantity = 0 → DELETE
- Po failed `add_price_point` zawsze `session.rollback()` — bez tego session trucizna dla batcha

## Kod

- Rate limiter (`slowapi.Limiter`) — **jeden singleton** w `app/config/rate_limit.py`
- `formatCurrency` i `LABOUR_ITEM_NAME` — importuj z shared lib, nigdy nie redefiniuj lokalnie
- Cross-module imports przez services, nie bezpośrednio między modelami
- `GET /api/inventory/for-recipe/{item_id}` rejestrowany PRZED `PUT /api/inventory/{item_id}`

## Testy

- Testy biją w prawdziwy PostgreSQL (`app_test`) — bez mocków bazy
- UUID suffix we wszystkich nazwach itemów w testach (UniqueConstraint name+grade)
- DB nie jest czyszczona między testami — każdy test musi być izolowany przez unikalne dane

## Git & Workflow

- Nigdy nie commituj bezpośrednio do `main`
- Nigdy nie pushuj bez wyraźnej instrukcji od użytkownika
- Format: `typ(scope): opis` (feat, fix, chore, docs, refactor)
- Nietrywalna zmiana → Plan Mode → czekaj na zatwierdzenie

## Infra

- Podman Compose (nie docker compose)
- Caddy jako TLS terminator + reverse proxy
- Dev: 3 serwisy (db, backend --reload, frontend dev)
- Prod: 4 serwisy (db, backend 2 workers, frontend node, caddy)
