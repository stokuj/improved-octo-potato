# Crafting — decyzje projektowe

## Model danych

- Jeden item = jedna receptura (nie wielość ścieżek)
- Składniki receptury to wyłącznie Item-y z bazy (powiązane przez `item_id`)
- Receptury wchodzą przez ręczny SQL (z Google Docs), nie przez UI/admin
- `output_qty` — ile sztuk wychodzi z jednego craftu (mnożnik po stronie UI)

## Kalkulator

**Endpoint:** `GET /api/crafting/{item_id}/calculate`  
**Endpoint:** `GET /api/crafting/` — lista wszystkich receptur z wyliczoną marżą

### Odpowiedź kalkulatora (drzewo, pełna głębokość)

```
{
  ingredient_costs: [
    {
      item_id, name, qty_needed, unit_price, total_cost,
      recipe: <ten sam kształt rekurencyjnie, null jeśli brak receptury>
    }
  ],
  total_material_cost: int,
  output_qty: int,
  crafts_possible: int | null,   # jeśli user podał qty w inwentarzu
  market_price: int | null,
  profit_per_craft: int | null   # market_price * output_qty − total_material_cost
}
```

- Backend zawsze zwraca **pełne drzewo** (wszystkie poziomy)
- Hard limit: **10 poziomów głębokości** — przy cyklu/przekroczeniu → 400 z info który składnik tworzy cykl
- UI pokazuje `+` tylko gdy składnik sam ma recepturę w bazie; brak receptury = składnik finalny (np. Iron Ore)

## UI

- Zakładka "Crafting" na stronie `/items/[id]` — widoczna tylko jeśli item ma recepturę
- **Globalny mnożnik** (ile razy craftować) skaluje całe drzewo
- **Ilości z inwentarza** wpisywane inline per składnik — od razu widać czy masz wystarczająco
- Każdy składnik z recepturą ma `+` do rozwinięcia poddrzewa; można wybrać czy kupić składnik czy craftować go samemu

## Roadmap

- v1: kalkulator bez persystencji inwentarza (ilości wpisywane jednorazowo w formularzu)
- v2: `UserInventory` (user_id, item_id, quantity) — pre-fill z zapisanego inwentarza użytkownika
  - Endpoint kalkulatora zaprojektować tak, żeby ilości przychodziły jako request body (nie z sesji), co ułatwi podpięcie persystencji później
