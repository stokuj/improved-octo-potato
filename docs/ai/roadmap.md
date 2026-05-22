# Roadmap

## Zrealizowane

| Ficzer | Opis |
|---|---|
| Auth | Rejestracja, logowanie, cookie session (fastapi-users) |
| Items | Lista z paginacją/filtrami, szczegół, search case-insensitive |
| Price history | ECharts line chart, interwały raw/5m/1h/1d, markLine material cost |
| Saved Items | Follow/unfollow (user_items), watchlist page |
| Crafting system | Receptury, kalkulator profitu, RecipeTree, RecipeCard |
| Ingest API | Bulk endpoint `/api/ingest/prices`, grade mapping, partial-success |
| Discord bot | Slash commands `/price` i `/addprice`, 21 testów |
| Item detail redesign | Dwukolumnowy layout, profit hero card, full-width recipe tree |
| Recipe UX | Inline "Have" column, Total Labour footer, usunięty Follow z recipe view |
| User Inventory | Model, 3 endpointy, strona `/inventory`, integracja z recipe tree |
| TypeScript migration | `api.d.ts` z openapi-typescript, rename `.js→.ts`, `lang="ts"` wszędzie |
| Settings page | Edycja display_name, is_private |
| Admin panel | sqladmin pod `/admin` |
| Seed data | 29 itemów + drzewo receptur + 30d historia cen |
| Infra | Podman compose dev + prod, Caddy, Makefile |
| Test suite expansion | +28 backend, +38 frontend, +20 e2e Playwright specs (2026-05-22) |

## W trakcie / do merge

| Gałąź | Zawartość |
|---|---|
| `feature/user-inventory` | Kompletny user inventory + TypeScript migration — gotowy do merge do main |

## Planowane

| Ficzer | Priorytet | Uwagi |
|---|---|---|
| pricetracker_folio (Lua addon) | wysoki | Addon do ArcheRage zapisujący ceny do JSONL; osobne repo |
| Watcher daemon | średni | Zastąpiony botem, ale dla automatyzacji może wrócić |
| `aiosqlite` cleanup | niski | Zależność bez użycia — relikt z early dev |
| `mockData.ts` cleanup | niski | Martwy plik w frontend lib |
| `InventoryModal.svelte` | niski | Komponent bez importera — usunąć lub podpiąć |
| Avatar URL walidacja | niski | Brak max_length na Profile.avatar_url |
| `/saved-items` redirect | niski | Brak early redirect przed fetch (drobne UX) |
