# Project Audit Design

**Date:** 2026-05-14  
**Goal:** Kompleksowy audyt projektu (portfolio/demo) z priorytetem backendu  
**Approach:** Backend First, Frontend Later  

---

## Context

Projekt to game marketplace/price tracker (prawdopodobnie MMO). Stack: FastAPI + SQLModel + PostgreSQL + SvelteKit 5. Aktualny stan: działający szkielet, brak testów, kilka niekompletnych elementów logiki biznesowej i konfiguracji.

---

## Faza 1 — Fundamenty backendu

**Cel:** Usunąć techniczny dług konfiguracyjny zanim dotkniemy logiki.

1. **Python 3.13 stable** — `backend/.python-version` wskazuje na 3.14 (RC). Downgrade do 3.13 zapobiega problemom z zależnościami i niestabilnością interpretera.
2. **CORS origins do settings** — `app/main.py` ma hardcoded `["http://localhost:5173", "http://127.0.0.1:5173"]`. Przenieść do `Settings` jako `cors_origins: list[str]`, wczytywane z env.
3. **`cookie_secure` default** — aktualnie `False` w settings. Zmienić domyślny komentarz/dokumentację żeby było jasne, że produkcja wymaga `True`.

---

## Faza 2 — Logika biznesowa

**Cel:** Naprawić niekompletne flow biznesowe.

### `Item.current_price` — denormalizacja bez aktualizacji

`Item` ma pole `current_price` (nullable int), ale `PricePoint` przechowuje historię cen. Aktualnie nie ma kodu, który aktualizuje `current_price` po dodaniu nowego `PricePoint`.

**Naprawa:** W `prices/services.py`, po zapisaniu nowego `PricePoint`, wykonać `UPDATE item SET current_price = :price, updated_at = now() WHERE id = :item_id`. Operacja atomowa w tej samej sesji.

### `UserItem` — obsługa unique constraint na poziomie API

Unique constraint `(user_id, item_id)` istnieje w bazie, ale naruszenie go zwraca nieobsłużony `IntegrityError` → HTTP 500. 

**Naprawa:** W `user_items/services.py` sprawdzić czy rekord istnieje przed insertem (lub złapać `IntegrityError` i zwrócić HTTP 409 Conflict).

---

## Faza 3 — Testy backendu

**Cel:** Pokrycie testami kluczowych flow — testy jako specyfikacja zachowania.

### Setup

- Dodać do `pyproject.toml`: `pytest`, `pytest-asyncio`, `httpx`
- Testowa baza: PostgreSQL (osobna baza `app_test`) lub SQLite in-memory jako fallback dla szybkich testów jednostkowych
- Fixture `async_client` — `AsyncClient` z `httpx` skierowany na testową aplikację FastAPI
- Fixture `db_session` — async session z rollbackiem po każdym teście

### Zakres testów

| Moduł | Co testować |
|---|---|
| `auth` | register → auto-login; login z błędnym hasłem → 400; logout → cookie cleared |
| `items` | GET /items z filtrowaniem po `category`, `grade`, `q`; GET /items/{id} nieistniejącego → 404 |
| `prices` | POST /prices → `PricePoint` zapisany + `Item.current_price` zaktualizowany |
| `user_items` | POST → 201; ponowny POST tego samego → 409; DELETE → 204 |
| `profiles` | Auto-created po rejestracji; PATCH /profiles/me → zaktualizowany |

---

## Faza 4 — Frontend (domknięcie)

**Cel:** Zastąpić mockData prawdziwym API, dodać podstawową obsługę błędów.

1. **`src/lib/mockData.js`** — zidentyfikować które routy z niego korzystają i zastąpić wywołaniami fetch do backendu
2. **Stany ładowania** — dodać `loading` state do komponentów które odpytują API (ItemTable, strona items/[id])
3. **Obsługa błędów** — wyświetlać komunikat użytkownikowi gdy fetch zwróci błąd (zamiast cichego fail)

---

## Kryteria ukończenia

- [ ] `backend/.python-version` → 3.13
- [ ] CORS origins w `Settings`, nie hardcoded
- [ ] `Item.current_price` aktualizuje się po dodaniu `PricePoint`
- [ ] `POST /user-items` z duplikatem zwraca 409, nie 500
- [ ] `pytest` przechodzi bez błędów, pokrywa 4 moduły
- [ ] `mockData.js` nie jest używany w żadnym aktywnym route
