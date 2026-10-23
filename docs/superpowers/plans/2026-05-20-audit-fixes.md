# Audit Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all Critical and Important bugs identified in the 2026-05-20 project audit — race conditions, missing error handling, missing tests, and type/dead-code cleanup.

**Architecture:** Fixes are surgical — no refactoring beyond the identified issue. Backend fixes use SQLAlchemy `insert().on_conflict_do_nothing()` for idempotent writes. Frontend fixes replace `onMount` auth guard with a `$effect` that waits for `user.loading === false`, and add error feedback to silent PUT failures.

**Tech Stack:** FastAPI · SQLModel · SQLAlchemy Core (for ON CONFLICT) · SvelteKit 5 runes · pytest-asyncio

**Skipped (separate decision needed):**
- C1 — ingest auth (architectural: API key vs token design)
- C2 — SELECT FOR UPDATE on current_price (performance impact)
- C4 — Redis rate limiter vs single worker
- C5 — prod healthchecks (infra change)
- I3 — crafting/calculate rate limit (needs design)
- I15 — Caddy security headers (infra)

---

## Files touched

| File | Change |
|---|---|
| `backend/app/profiles/services.py` | ON CONFLICT on profile insert |
| `backend/app/user_items/services.py` | ON CONFLICT on follow insert |
| `backend/app/items/router.py` | max_length=200 on `q` param |
| `backend/app/user_items/router.py` | max_length=200 on `q` param |
| `backend/tests/test_auth.py` | add logout test + UserRead field leak test |
| `backend/tests/test_user_items.py` | add GET /me tests + DELETE nonexistent test |
| `frontend/src/lib/components/ItemTable.svelte` | fix auth guard race in onMount |
| `frontend/src/lib/auth.svelte.ts` | FormData → URLSearchParams in login() |
| `frontend/src/routes/inventory/+page.svelte` | add try/catch + error state to PUT |
| `frontend/src/routes/items/[id]/+page.svelte` | surface error on failed inventory PUT |
| `frontend/src/routes/+page.svelte` | `any[]` → `ItemListItem[]` |
| `frontend/src/lib/grades.ts` | remove unused `gradeBadgeStyle` |

---

## Task 1: Backend — ON CONFLICT for profile create

Race condition: two concurrent GET /profiles/me for a new user both do SELECT → both find nothing → both INSERT → IntegrityError → 500.

**Files:**
- Modify: `backend/app/profiles/services.py`

- [ ] **Step 1: Write failing test**

Add to `backend/tests/test_profiles.py`:

```python
import asyncio

async def test_get_or_create_profile_concurrent(client: AsyncClient) -> None:
    email = f"profile-concurrent-{uuid.uuid4().hex[:8]}@test.com"
    await client.post("/api/auth/register", json={"email": email, "password": "password123"})
    await client.post("/api/auth/login", data={"username": email, "password": "password123"})

    # Two simultaneous profile fetches — must not raise 500
    r1, r2 = await asyncio.gather(
        client.get("/api/profiles/me"),
        client.get("/api/profiles/me"),
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails (or is flaky)**

```bash
cd backend && uv run pytest tests/test_profiles.py::test_get_or_create_profile_concurrent -v
```

(May pass intermittently — race is timing-dependent. The fix is still correct.)

- [ ] **Step 3: Fix `get_or_create_profile` with ON CONFLICT**

Replace `backend/app/profiles/services.py` with:

```python
from typing import Any
from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.profiles.models import Profile, utcnow
from app.profiles.schemas import ProfileUpdate


async def get_or_create_profile(session: AsyncSession, user_id: Any) -> Profile:
    stmt = (
        pg_insert(Profile)
        .values(user_id=user_id, is_private=True)
        .on_conflict_do_nothing(index_elements=["user_id"])
    )
    await session.exec(stmt)  # type: ignore[arg-type]
    await session.commit()

    result = await session.exec(select(Profile).where(Profile.user_id == user_id))
    return result.one()


async def update_profile(
    session: AsyncSession, profile: Profile, profile_in: ProfileUpdate
) -> Profile:
    updates = profile_in.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(profile, field, value)

    profile.updated_at = utcnow()
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return profile
```

- [ ] **Step 4: Run all profile tests**

```bash
cd backend && uv run pytest tests/test_profiles.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/profiles/services.py backend/tests/test_profiles.py
git commit -m "fix(profiles): replace check-then-insert with ON CONFLICT DO NOTHING"
```

---

## Task 2: Backend — ON CONFLICT for follow_item

Race condition: double-click follow → two concurrent POSTs both find no existing row → both INSERT → IntegrityError → 500.

**Files:**
- Modify: `backend/app/user_items/services.py`

- [ ] **Step 1: Write failing test**

Add to `backend/tests/test_user_items.py`:

```python
async def test_follow_concurrent_is_idempotent(
    auth_client: AsyncClient, tracked_item: Item
) -> None:
    r1, r2 = await asyncio.gather(
        auth_client.post(f"/api/user-items/{tracked_item.id}"),
        auth_client.post(f"/api/user-items/{tracked_item.id}"),
    )
    assert r1.status_code in (201, 204)
    assert r2.status_code in (201, 204)
```

Add `import asyncio` at the top of `test_user_items.py`.

- [ ] **Step 2: Run test to verify it is flaky/fails**

```bash
cd backend && uv run pytest tests/test_user_items.py::test_follow_concurrent_is_idempotent -v
```

- [ ] **Step 3: Fix `follow_item` with ON CONFLICT**

Replace the `follow_item` function in `backend/app/user_items/services.py`:

```python
from sqlalchemy.dialects.postgresql import insert as pg_insert

async def follow_item(session: AsyncSession, user_id: uuid.UUID, item_id: int) -> bool:
    """Returns True if newly followed, False if already followed."""
    item = await session.get(Item, item_id)
    if item is None:
        raise NotFoundError("Item not found")

    stmt = (
        pg_insert(UserItem)
        .values(user_id=user_id, item_id=item_id)
        .on_conflict_do_nothing()
    )
    result = await session.exec(stmt)  # type: ignore[arg-type]
    await session.commit()
    return result.rowcount == 1
```

Add `from sqlalchemy.dialects.postgresql import insert as pg_insert` at the top of the file.

- [ ] **Step 4: Run all user_items tests**

```bash
cd backend && uv run pytest tests/test_user_items.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/user_items/services.py backend/tests/test_user_items.py
git commit -m "fix(user-items): replace check-then-insert with ON CONFLICT DO NOTHING"
```

---

## Task 3: Backend — max_length on search query param

Without a max_length, a caller can send a 10MB string that triggers `ILIKE '%...%'` on the full items table.

**Files:**
- Modify: `backend/app/items/router.py`
- Modify: `backend/app/user_items/router.py`

- [ ] **Step 1: Write failing test**

Add to `backend/tests/test_items.py`:

```python
async def test_search_too_long_returns_422(client: AsyncClient) -> None:
    resp = await client.get(f"/api/items/?q={'a' * 201}")
    assert resp.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/test_items.py::test_search_too_long_returns_422 -v
```

Expected: FAIL (currently returns 200).

- [ ] **Step 3: Add max_length to items router**

In `backend/app/items/router.py`, change:

```python
q: str | None = Query(default=None),
```

to:

```python
q: str | None = Query(default=None, max_length=200),
```

- [ ] **Step 4: Add max_length to user_items router**

In `backend/app/user_items/router.py`, change:

```python
q: str | None = Query(default=None),
```

to:

```python
q: str | None = Query(default=None, max_length=200),
```

- [ ] **Step 5: Run tests**

```bash
cd backend && uv run pytest tests/test_items.py::test_search_too_long_returns_422 -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/items/router.py backend/app/user_items/router.py backend/tests/test_items.py
git commit -m "fix(items): add max_length=200 to search query param"
```

---

## Task 4: Backend — missing tests (logout, GET /user-items/me, DELETE nonexistent)

**Files:**
- Modify: `backend/tests/test_auth.py`
- Modify: `backend/tests/test_user_items.py`

- [ ] **Step 1: Add logout test to test_auth.py**

Append to `backend/tests/test_auth.py`:

```python
async def test_logout_clears_cookie(client: AsyncClient) -> None:
    email = _email()
    await client.post("/api/auth/register", json={"email": email, "password": "password123"})
    await client.post("/api/auth/login", data={"username": email, "password": "password123"})

    # Confirm logged in
    me_resp = await client.get("/api/users/me")
    assert me_resp.status_code == 200

    # Logout
    logout_resp = await client.post("/api/auth/logout")
    assert logout_resp.status_code == 204

    # Cookie must be gone — subsequent /me must 401
    me_after = await client.get("/api/users/me")
    assert me_after.status_code == 401


async def test_me_does_not_expose_superuser_flag(client: AsyncClient) -> None:
    email = _email()
    await client.post("/api/auth/register", json={"email": email, "password": "password123"})
    await client.post("/api/auth/login", data={"username": email, "password": "password123"})

    resp = await client.get("/api/users/me")
    assert resp.status_code == 200
    body = resp.json()
    assert "is_superuser" not in body
    assert "is_active" not in body
    assert "is_verified" not in body
```

- [ ] **Step 2: Add GET /user-items/me and DELETE nonexistent tests to test_user_items.py**

Append to `backend/tests/test_user_items.py`:

```python
async def test_get_followed_items_returns_paginated(
    auth_client: AsyncClient, tracked_item: Item
) -> None:
    await auth_client.post(f"/api/user-items/{tracked_item.id}")
    resp = await auth_client.get("/api/user-items/me")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert any(i["id"] == tracked_item.id for i in data["items"])


async def test_get_followed_items_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/user-items/me")
    assert resp.status_code == 401


async def test_get_followed_items_filter_by_name(
    auth_client: AsyncClient, tracked_item: Item
) -> None:
    await auth_client.post(f"/api/user-items/{tracked_item.id}")
    resp = await auth_client.get(f"/api/user-items/me?q={tracked_item.name[:4]}")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


async def test_unfollow_nonexistent_returns_204(auth_client: AsyncClient) -> None:
    resp = await auth_client.delete("/api/user-items/999999")
    assert resp.status_code == 204
```

- [ ] **Step 3: Run new tests**

```bash
cd backend && uv run pytest tests/test_auth.py tests/test_user_items.py -v
```

Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_auth.py backend/tests/test_user_items.py
git commit -m "test(auth,user-items): add logout, me exposure, GET /me, DELETE nonexistent"
```

---

## Task 5: Frontend — fix auth guard race in ItemTable

`onMount` fires before `checkMe()` finishes. The guard `!user.loading && !user.isLoggedIn` → `loading=true` → condition is false → page loads data even for unauthenticated user.

The `$effect` at line 201 already handles this correctly (returns early if `user.loading`). The `onMount` guard is redundant and broken — remove it.

**Files:**
- Modify: `frontend/src/lib/components/ItemTable.svelte`

- [ ] **Step 1: Remove the broken onMount guard**

In `ItemTable.svelte`, find (around line 178):

```svelte
onMount(() => {
    const init = async () => {
        if (requireAuth && !user.loading && !user.isLoggedIn) {
            goto('/auth');
            return;
        }

        await loadSavedIds();
        await loadItems(true);
        updateContainerPos();
    };
```

Replace with:

```svelte
onMount(() => {
    const init = async () => {
        await loadSavedIds();
        await loadItems(true);
        updateContainerPos();
    };
```

The `$effect` at line ~201 already handles redirect for `requireAuth` pages once `user.loading` settles:

```svelte
$effect(() => {
    if (user.loading) return;
    if (!user.isLoggedIn) {
        savedIds = new Set();
        return;
    }
    loadSavedIds();
});
```

For `requireAuth` pages the `$effect` in `inventory/+page.svelte` handles redirect. For `saved-items`, add an explicit redirect effect inside ItemTable when `requireAuth` is true.

Find the `$effect` that handles `user.isLoggedIn` (around line 201) and extend it:

```svelte
$effect(() => {
    if (user.loading) return;
    if (!user.isLoggedIn) {
        if (requireAuth) goto('/auth');
        savedIds = new Set();
        return;
    }
    loadSavedIds();
});
```

- [ ] **Step 2: Run svelte-check**

```bash
cd frontend && npx svelte-check --output machine 2>&1 | tail -5
```

Expected: `0 ERRORS 0 WARNINGS`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/components/ItemTable.svelte
git commit -m "fix(frontend): replace broken onMount auth guard with $effect in ItemTable"
```

---

## Task 6: Frontend — login URLSearchParams

FastAPI's OAuth2PasswordRequestForm standard is `application/x-www-form-urlencoded`. `FormData` sends `multipart/form-data` which fastapi-users accepts by accident, not by design.

**Files:**
- Modify: `frontend/src/lib/auth.svelte.ts`

- [ ] **Step 1: Replace FormData with URLSearchParams**

In `auth.svelte.ts`, find:

```typescript
export async function login(email: string, password: string): Promise<{ success: boolean; message?: string }> {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);

    const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        body: formData,
        credentials: 'include'
    });
```

Replace with:

```typescript
export async function login(email: string, password: string): Promise<{ success: boolean; message?: string }> {
    const body = new URLSearchParams();
    body.append('username', email);
    body.append('password', password);

    const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
        credentials: 'include'
    });
```

- [ ] **Step 2: Run svelte-check**

```bash
cd frontend && npx svelte-check --output machine 2>&1 | tail -5
```

Expected: `0 ERRORS 0 WARNINGS`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/auth.svelte.ts
git commit -m "fix(auth): use URLSearchParams for login (OAuth2 standard)"
```

---

## Task 7: Frontend — inventory PUT error handling

Silent failures: when `PUT /inventory/{id}` fails, the UI shows the wrong quantity with no feedback.

**Files:**
- Modify: `frontend/src/routes/inventory/+page.svelte`
- Modify: `frontend/src/routes/items/[id]/+page.svelte`

- [ ] **Step 1: Fix inventory/+page.svelte**

Find the `handleQuantityChange` function:

```typescript
function handleQuantityChange(itemId: number, value: number) {
    quantities = { ...quantities, [itemId]: value };
    clearTimeout(debounceTimers[itemId]);
    debounceTimers[itemId] = setTimeout(async () => {
        await fetch(`${API_BASE_URL}/inventory/${itemId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ quantity: value }),
        });
    }, 400);
}
```

At the top of the `<script>` block add an error state variable (near other `$state` declarations):

```typescript
let saveError: string | null = $state(null);
```

Replace `handleQuantityChange` with:

```typescript
function handleQuantityChange(itemId: number, value: number) {
    quantities = { ...quantities, [itemId]: value };
    saveError = null;
    clearTimeout(debounceTimers[itemId]);
    debounceTimers[itemId] = setTimeout(async () => {
        try {
            const resp = await fetch(`${API_BASE_URL}/inventory/${itemId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ quantity: value }),
            });
            if (!resp.ok) saveError = 'Failed to save quantity. Please refresh.';
        } catch {
            saveError = 'Failed to save quantity. Please refresh.';
        }
    }, 400);
}
```

In the template, find where the table/list is rendered and add the error alert above it:

```svelte
{#if saveError}
    <div class="alert alert-error mb-4">
        <span>{saveError}</span>
    </div>
{/if}
```

- [ ] **Step 2: Fix items/[id]/+page.svelte**

Find (around line 185):

```typescript
        try {
            await fetch(`${API_BASE_URL}/inventory/${itemId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ quantity: value }),
            });
        } catch { /* optimistic update stays */ }
```

Replace with:

```typescript
        try {
            const resp = await fetch(`${API_BASE_URL}/inventory/${itemId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ quantity: value }),
            });
            if (!resp.ok) {
                inventory = prev;
            }
        } catch {
            inventory = prev;
        }
```

This reverts the optimistic update instead of silently leaving wrong data. (`prev` must be captured before the update — check that the surrounding code captures it; if not, capture it at the start of the handler.)

- [ ] **Step 3: Run svelte-check**

```bash
cd frontend && npx svelte-check --output machine 2>&1 | tail -5
```

Expected: `0 ERRORS 0 WARNINGS`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/inventory/+page.svelte frontend/src/routes/items/\[id\]/+page.svelte
git commit -m "fix(inventory): surface PUT errors instead of silent failure"
```

---

## Task 8: Frontend — type & dead code cleanup

**Files:**
- Modify: `frontend/src/routes/+page.svelte`
- Modify: `frontend/src/lib/grades.ts`

- [ ] **Step 1: Fix `any[]` on homepage**

In `frontend/src/routes/+page.svelte`, add import:

```typescript
import type { ItemListItem } from '$lib/types';
```

Change:

```typescript
let items: any[] = $state([]);
```

to:

```typescript
let items: ItemListItem[] = $state([]);
```

- [ ] **Step 2: Remove dead `gradeBadgeStyle`**

In `frontend/src/lib/grades.ts`, delete the unused function:

```typescript
export function gradeBadgeStyle(grade: string): string {
    const c = gradeColor(grade);
    return `color: ${c}; border-color: ${c}55; text-shadow: 0 0 8px ${c}44;`;
}
```

Verify no file imports it first:

```bash
grep -r "gradeBadgeStyle" /home/dv6/GitHub/improved-octo-potato/frontend/src/
```

Expected: no output. Then delete.

- [ ] **Step 3: Run svelte-check**

```bash
cd frontend && npx svelte-check --output machine 2>&1 | tail -5
```

Expected: `0 ERRORS 0 WARNINGS`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/+page.svelte frontend/src/lib/grades.ts
git commit -m "fix(frontend): ItemListItem[] on homepage, remove dead gradeBadgeStyle"
```

---

## Self-Review

**Spec coverage:**
- C3 auth race → Task 5 ✓
- I1 profile ON CONFLICT → Task 1 ✓
- I2 follow ON CONFLICT → Task 2 ✓
- I7 max_length q → Task 3 ✓
- I9 login URLSearchParams → Task 6 ✓
- I10 silent PUT failure → Task 7 ✓
- I16 GET /user-items/me tests → Task 4 ✓
- I17 logout test → Task 4 ✓
- I18 DELETE nonexistent test → Task 4 ✓
- M6 gradeBadgeStyle dead → Task 8 ✓
- M7 any[] homepage → Task 8 ✓

**Skipped intentionally:** M8 @ts-nocheck in EChartsLineChart (needs echarts type research, separate task), I12 GRADES constant (low risk, low value), M3 SQL aggregation (perf optimization, separate task).

**Placeholder scan:** All steps have concrete code. No TBD. ✓

**Type consistency:**
- `pg_insert` from `sqlalchemy.dialects.postgresql` used consistently in Tasks 1 and 2 ✓
- `saveError: string | null` introduced and used within Task 7 ✓
- `ItemListItem` imported from `$lib/types` in Task 8 ✓
