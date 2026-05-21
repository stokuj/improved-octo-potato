# Code Audit Report — minimax-m2.7

**Date:** 2026-05-20
**Auditor:** minimax-m2.7 (opencode agent)
**Scope:** backend (FastAPI/SQLModel), frontend (SvelteKit 5), discord_bot, infra

---

## Severity Index

| Sigla | Znaczenie |
|---|---|
| 🔴 CRITICAL | Bug lub security issue wymagający natychmiastowej naprawy |
| 🟠 HIGH | Zły pattern lub smell, napraw w następnej okazji |
| 🟡 MEDIUM | Kode smell, optymalizacja lub shortcut warty uwagi |
| 🟢 INFO | Drobny szczegół lub future consideration |

---

## 🔴 CRITICAL

### 1. `Ingredient` → `ingredient_item_id` typo w modelu

**File:** `backend/app/crafting/models.py:19`

```python
ingredient_item_id: int = Field(foreign_key="item.id", index=True)
```

`ingredient_item_id` jest literówką. Poprawna angielska nazwa to `ingredient_id` lub `item_id`. Jest spójnie używany w routerze i services (np. `ingredient_item_id` w `build_node`), więc jeśli zmienisz nazwę kolumny w modelu, musisz zaktualizować wszystkie odwołania w całym projekcie.

**Rekomendacja:** Zmiana na `ingredient_id` wymaga migracji bazy danych. Jeśli baza jest już w prod — napraw literówkę lokalnie w services/routerze, ale nie ruszaj modelu, żeby nie zepsuć danych.

---

## 🟠 HIGH

### 2. Hardkodowane secrets w settings

**File:** `backend/app/config/settings.py:14-15`

```python
auth_secret: str = "temporary-development-secret-must-be-32-chars"
admin_session_secret: str = "temporary-admin-session-secret-must-be-32-chars"
```

To są defaulty fallbackowe — jeśli .env nie zostanie załadowany (np. w kontenerze), aplikacja startuje z hardkodowanym secretem. Dla prod to jest ryzykowne.

**Rekomendacja:** Dodać validator który w non-dev mode (lub gdy zmienna jest pusta) rzuca wyjątek zamiast używać fallbacku. Zmienić default na `None` i rzucić `ValidationError` jeśli None w prod.

---

### 3. DELETE bez flush w `user_inventory/services.py`

**File:** `backend/app/user_inventory/services.py:45-50`

```python
await session.exec(
    delete(UserInventory).where(...)
)
await session.commit()
return
```

`session.exec()` dla DELETE nie zwraca liczby affected rows. Jeśli delete się nie powiedzie (np. constraint violation), to nie wiesz czy wiersz został usunięty. Dla poprawnej semantyki powinno być `session.execute()` z `await session.commit()`.

**Rekomendacja:** Zamień `session.exec(...)` na `await session.execute(...)` dla spójności z upsert użytym poniżej.

---

### 4. Race condition w `get_inventory_for_recipe`

**File:** `backend/app/user_inventory/services.py:79-92`

```python
all_recipes = await load_all_recipes(session)
if item_id not in all_recipes:
    return {}
all_items = await load_all_items(session)
try:
    tree = build_craft_tree(item_id, 1, {}, all_recipes, all_items)
```

Ładuje wszystkie przepisy i wszystkie itemy w osobnych query. Jeśli w międzyczasie ktoś doda nowy przepis, `all_recipes` jest outdated. W praktyce mało risk, bo te dane rzadko się zmieniają, ale architektonicznie jest to Data Clump.

**Rekomendacja:** Przenieś `load_all_recipes` i `load_all_items` do jednej transakcji lub cacheuj je na czas requesta.

---

## 🟡 MEDIUM

### 5. Brak paginacji w `/saved-items`

**File:** brak paginacji

`/saved-items` (UserItems) zwraca całą listę bez paginacji. Dla userów z setkami obserwowanych itemów to może byćproblem (network, render).

**Rekomendacja:** Dodać `offset/limit` tak jak w `/items`.

---

### 6. `splitCurrency` redefinicja w `ItemTable.svelte`

**File:** `frontend/src/lib/components/ItemTable.svelte:7`

```typescript
import { splitCurrency } from '$lib/currency.js';
```

Wg `patterns.md` `formatCurrency` i `LABOUR_ITEM_NAME` muszą być importowane z shared lib, nigdy nie redefiniowane lokalnie. Jednak `splitCurrency` jest importowana poprawnie. Todo: "ItemTable.svelte ma historyczny bug (lokalna kopia splitCurrency)" — ten bug był naprawiony. Informacyjnie: wzorzec jest respektowany.

---

### 7. Duplikacja logiki `computeNodeCost` w dwóch miejscach

**Files:**
- `frontend/src/lib/components/crafting/RecipeTree.svelte:19`
- `frontend/src/routes/items/[id]/+page.svelte:36`

Ta sama funkcja `computeNodeCost` jest zdefiniowana zarówno w `RecipeTree.svelte` jak i w `+page.svelte`. Są prawie identyczne.

**Rekomendacja:** Wyeksportować `computeNodeCost` do `$lib/crafting.ts` jako helper i używać go w obu miejscach.

---

### 8. `async_session_maker` importowany dwa razy

**Files:**
- `backend/app/config/db.py:14` (definiuje)
- `backend/app/auth/manager.py:8` (importuje z db)

`auth/manager.py` używa `async_session_maker` do tworzenia sesji w `on_after_register`. To działa, ale jest to cross-module import który zwiększa coupling.Wg architecture: "Cross-module imports przez services, nie bezpośrednio między modelami." — tutaj manager importuje bezpośrednio z config/db.

**Rekomendacja:** Przenieść logikę tworzenia Profilu do `profiles/services.py` i wywoływać stamtąd.

---

### 9. Brak `max_length` na `avatar_url` w Profile

**File:** `backend/app/profiles/models.py`

`Profile.avatar_url` nie ma `max_length`, co pozwala na bardzo długie stringi w DB.

**Rekomendacja:** Dodać `max_length=500` lub podobnie.

---

### 10. `GRADE_CHOICES` duplikowany w discord_bot i backend

**Files:**
- `backend/app/ingest/grade_map.py`
- `discord_bot/cogs/prices.py:10`

Te same grade'y są zdefiniowane w dwóch osobnych miejscach. Jeśli ArcheRage doda nowy grade, trzeba zmienić w dwóch miejscach.

**Rekomendacja:** Stworzyć wspólny plik `shared/grades.py` w backendu i importować w discordzie. Lub traktować discord_bot jako zupełnie niezależny projekt z własną definicją.

---

### 11. Brak testów rate limitera

**File:** `docs/ai/roadmap.md:35`

"Rate limit testy — Brak testów dla slowapi limitera"

**Rekomendacja:** Dodać test który weryfikuje że `60/minute` limit jest faktycznie respektowany.

---

### 12. Zbędny `aiosqlite` w dependencies

**File:** `backend/pyproject.toml`

`aiosqlite` jest listowany ale nigdzie nie jest używany. Przynajmniej warto to sprawdzić i usunąć jeśli nie jest potrzebny.

---

## 🟢 INFO

### 13. `/saved-items` brak early redirect

**File:** `frontend/src/routes/saved-items/+page.svelte`

Wg roadmap: "Brak early redirect przed fetch (drobne UX)" — strona może flashować loader zanim sprawdzi auth.

---

### 14. Brak `/users/{id}` testów

**File:** `docs/ai/roadmap.md`

Admin endpoint bez pokrycia testami.

---

### 15. `mockData.ts` martwy plik

**File:** `frontend/src/lib/` (szukany ale nie znaleziony)

Wg roadmap: mockData.ts jest do usunięcia.

---

### 16. `InventoryModal.svelte` bez importera

**File:** `frontend/src/lib/components/` (szukany ale nie znaleziony)

Komponent bez podłączonego importera — do integracji lub usunięcia.

---

### 17. Brak UV w backendzie

**File:** `backend/pyproject.toml`

Projekt używa `uv` do zarządzania zależnościami (w compose: `uv run ...`) ale w samym `pyproject.toml` nie ma toolu `uv` skonfigurowanego (brak `[tool.uv]` section). W praktyce działa bo `uv` jest installed globalnie lub w obrazie.

---

### 18. Cookie `Secure` w dev vs prod

**File:** `backend/app/config/settings.py:16`

`cookie_secure: bool = False` — w prod compose ustawia `COOKIE_SECURE: "true"` przez env, ale w dev jest False. To jest poprawne dla dev/prod split, ale warto żeby developer wiedział że na localhost to nie działa (brak HTTPS).

---

## ARCHITECTURE REVIEW

### ✅ Co jest dobrze zrobione

1. **Modułowa struktura** — `app/<domain>/` z podziałem na models/services/router/admin jest konsekwentny i jasny
2. **Singleton rate limitera** — jeden globalny limiter w `config/rate_limit.py`, używany przez wszystkie routery
3. **Cross-module imports przez services** — z wyjątkiem `auth/manager.py` (patrz punkt 8), wszystkie cross-module idą przez services
4. **Naive UTC w DB** — wszystkie datetime są timezone-naive, `utcnow()` stripuje tzinfo
5. **Partial success w ingest** — 200 z `errors[]` zamiast 4xx, watcher może retry
6. **SvelteKit 5 runes** — `$state`, `$derived`, `$effect` zamiast store'ów, nowoczesne
7. **Tailwind v4 + daisyUI** — aktualny stack
8. **TypeScript auto-generation** — `api.d.ts` generowany z openapi.json, nie ręcznie
9. **Separate Python projects** — backend i discord_bot mają osobne pyproject.toml

### ⚠️ Co wymaga uwagi

1. **Spaghetti w `items/[id]/+page.svelte`** — 367 linii, mnóstwo logiki inline (computeNodeCost, statystyki, loadery). Duża strona zbyt dużo robiąca. Warto wyekstrahować do mniejszych komponentów.
2. **`LABOUR_ITEM_NAME` jako string constant** — jeśli nazwa itemu "labour" zmieni się w grze, trzeba zmieniać everywhere. Lepszy pattern: item_id jako stała.
3. **Brak cache layer** — `load_all_recipes` i `load_all_items` są wywoływane per-request, bez żadnego cache. Dla małego datasetu OK, ale nie skaluje się.
4. **Ingredient.quantity bez default** — `RecipeIngredient.quantity` ma `ge=1` ale nie ma default, więc przy tworzeniu trzeba zawsze podawać. To jest OK ale warto wiedzieć.

---

## SUMMARY

| Category | Count |
|---|---|
| 🔴 CRITICAL | 1 |
| 🟠 HIGH | 3 |
| 🟡 MEDIUM | 9 |
| 🟢 INFO | 4 |

**Najważniejsze akcje do wykonania:**
1. Naprawić literówkę `ingredient_item_id` (lub zaakceptować i zostawić)
2. Dodać validator na secrets żeby nie startowało z fallbackami w prod
3. Zamienić `session.exec()` na `session.execute()` dla DELETE w user_inventory
4. Wyekstrahować `computeNodeCost` do shared lib
5. Rozbić `items/[id]/+page.svelte` na mniejsze komponenty

---

*Audit zakończony. Kolejne kroki: zaproponować fix dla każdego CRITICAL/HIGH itemu.*