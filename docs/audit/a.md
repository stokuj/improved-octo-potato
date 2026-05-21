# Codebase Architecture & Frontend Audit

## Summary
The project correctly applies FastAPI + SQLModel, Svelte 5 `$state` runes, and Discord bot isolation. However, there are a few critical architectural flaws concerning backend transactions (`AsyncSession` state leakage), SSR state leaks in SvelteKit, and API contract mismatches (duplicate/unused logic).

## Critical Issues

1. **Transaction Leakage in Ingestion (`backend/app/ingest/services.py:87`)**
   - The `match_or_create_item` uses `session.execute(pg_insert(...))` which autobegins a transaction. If this query fails (e.g. IntegrityError due to malformed constraint or DB crash), an `Exception` is raised. The caller `_process_row` catches this exception, but **does not issue `await session.rollback()`**. This leaves the `AsyncSession` in a failed state (`Failed to execute... current transaction is aborted, commands ignored until end of transaction block`). Because `/api/ingest/prices` does batch insertion, this poisons the session, causing *all subsequent rows in the batch to fail*. 
   - **Fix:** Add `await session.rollback()` inside the `except Exception as e:` block for `match_or_create_item`.

2. **Global State Leak in SSR (`frontend/src/lib/auth.svelte.ts:10`)**
   - The application exports a global rune: `export const user = $state<UserState>({...})`.
   - `frontend/svelte.config.js` uses `adapter-node`, meaning Server-Side Rendering (SSR) is active.
   - SvelteKit documentation explicitly warns against using `$state` at the top level of a module in SSR apps, because this state will be shared across all concurrent requests to the server, potentially leaking authenticated user sessions to other users.
   - **Fix:** Refactor auth state to use `setContext`/`getContext` or disable SSR for auth-dependent layouts if the app is strictly an SPA.

## Important Issues

1. **Dead Code & API Mismatch in Crafting Calculator (`backend/app/crafting/calculator.py:46`)**
   - The backend `build_craft_tree` function calculates `total_material_cost` and `batch_profit` based on a static "buy all direct ingredients" strategy and sends it in the `CraftResult`.
   - The frontend ignores these fields entirely. Instead, the frontend uses `$derived` (`frontend/src/routes/items/[id]/+page.svelte:55`) to recursively recalculate `materialCost` and `profit` using `computeNodeCost` to support dynamic user overrides ("buy" vs "craft" mode) and user inventory reductions.
   - **Fix:** Remove `batch_profit`, `total_material_cost`, and `has_missing_prices` from the backend `CraftResult` schema and calculator to simplify the backend (Deletion Test: deleting this logic removes complexity but keeps all functionality intact on the frontend).

## 1. Backend Architecture (FastAPI + SQLModel)
- **Module Depth:** The separation into `items`, `prices`, `crafting`, and `ingest` is solid. `user_inventory/services.py` executes an atomic `ON CONFLICT DO UPDATE` or `DELETE`, matching the architecture guidelines perfectly. 
- **Timezones:** Naive UTC is handled correctly via `_normalize_ts`.
- **Limiter:** Singleton pattern for `limiter` is respected.

## 2. Frontend Architecture (SvelteKit 5)
- **Svelte 5 Runes:** Migration to `$state` and `$derived` is clean. 
- **OpenAPI Types:** Generics from `api.d.ts` are heavily utilized, ensuring types are always synchronized.

## 3. Discord Bot
- The bot resides in a separate Python project (`discord_bot/`), satisfying decoupling rules.

## 4. Infrastructure & Code Smells
- Clean separation with `uv run`. Ruff checks pass. 

## 5. Tests
- **Coverage & Execution:** `pytest` correctly executes 94 integration tests against a real PostgreSQL DB. Test setup and tear-down logic matches the `docs/ai/patterns.md` guidelines.
- **SQLModel Warnings:** Squelching `DeprecationWarning` regarding `session.execute()`. While harmless (used mostly for `rowcount` checks or `fastapi-users`), adopting `session.exec()` where possible would clean up test output logs.

---
## Final Conclusion

The project's architectural constraints laid out in the AI constitution have mostly been correctly implemented. SvelteKit 5 runes are used properly, domain modules are separated gracefully, and Discord bot decouples correctly from the backend by calling the ingest API instead of directly touching DB logic.

However, the architecture has **two highly impactful leaks**:
1. **Transaction leak on the backend** — failing to `rollback()` after an exception in `match_or_create_item` breaks the `AsyncSession` for the rest of the batch insert in `prices`.
2. **State leak on the frontend** — exporting a global `$state` inside `auth.svelte.ts` on a server running `adapter-node` creates a cross-request memory and session leak.

**Actionable next steps:**
- Implement `session.rollback()` in `backend/app/ingest/services.py:90`.
- Refactor `user` state out of a global variable in `frontend/src/lib/auth.svelte.ts` or disable SSR for pages accessing this state using `export const ssr = false;`.
- Remove redundant recursive calculation fields (`batch_profit`, `total_material_cost`) from the backend API's `CraftResult` as the frontend handles dynamic re-calculation anyway.
