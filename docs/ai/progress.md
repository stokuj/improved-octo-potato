# Progress

Notatki ciągłości między sesjami. Aktualizuj na końcu każdej sesji.

## Stan na 2026-05-20

### Obecna gałąź: `feature/user-inventory`

Gałąź jest **kompletna** — 17 commitów ponad main. Zawiera:
- Backend `user_inventory/` — model, schemas, services, router, 3 endpointy
- Migracje alembic — 2 nowe (unique constraint + user_inventory)
- Testy — 261 linii `test_inventory.py`, TDD
- Frontend — strona `/inventory` (177 linii), integracja API w RecipeTree
- TypeScript migration — `api.d.ts` (1617 linii), wszystkie `.js→.ts`, `lang="ts"`
- Audyt — naprawione findingi z code review (atomic upsert, AppError handling itp.)

**Status: gotowy do merge do main. Nie jest jeszcze zpushowany.**

### Co zrobiono w tej sesji (2026-05-20)

- Przeniesiono `docs/architecture.md` → `docs/ai/architecture.md`
- Zaktualizowano architecture.md (usunięto watcher, poprawiono ścieżkę auth.svelte)
- Utworzono brakujące pliki: `stack.md`, `patterns.md`, `roadmap.md`, `constitution.md`, `progress.md`
- Analiza całego projektu przez 4 równoległych agentów (backend, frontend, infra/bot, git)

### Następne kroki

1. Merge `feature/user-inventory` → `main` (po decyzji użytkownika)
2. Pricetracker Lua addon (osobne repo, nie zaczęte)
3. Cleanup: `mockData.ts`, `InventoryModal.svelte`, `aiosqlite` dependency
