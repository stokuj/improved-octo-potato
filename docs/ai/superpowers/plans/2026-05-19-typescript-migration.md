# TypeScript Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the SvelteKit frontend from JavaScript to TypeScript, replacing all JSDoc typedefs with generated API types from FastAPI's OpenAPI schema.

**Architecture:** Install `openapi-typescript`, generate `src/lib/api.d.ts` from the running FastAPI server, expose clean aliases via `src/lib/types.ts`, rename all `.js` → `.ts`, add `lang="ts"` to all Svelte files, replace JSDoc annotations with proper TypeScript types.

**Tech Stack:** TypeScript (already in devDeps), `openapi-typescript`, SvelteKit 5, Svelte 5 runes

---

## File Map

| File | Action |
|---|---|
| `frontend/jsconfig.json` | Rename → `tsconfig.json`, add `include` array (keep `*.js` during transition) |
| `frontend/package.json` | Add `openapi-typescript` devDep, add `gen:types` script, update `check` to reference `tsconfig.json` |
| `frontend/src/lib/api.d.ts` | **Create (generated)** — run `npm run gen:types` against live backend |
| `frontend/src/lib/types.ts` | **Create** — schema aliases consumed by the whole app |
| `frontend/src/lib/index.js` | Rename → `index.ts` (empty barrel) |
| `frontend/src/lib/config.js` | Rename → `config.ts` |
| `frontend/src/lib/crafting.js` | Rename → `crafting.ts` |
| `frontend/src/lib/mockData.js` | Rename → `mockData.ts`, add local interfaces |
| `frontend/src/lib/currency.js` | Rename → `currency.ts`, remove JSDoc param/return annotations |
| `frontend/src/lib/grades.js` | Rename → `grades.ts`, type `GRADE_COLORS` as `Record<string,string>` |
| `frontend/src/lib/auth.svelte.js` | Rename → `auth.svelte.ts`, type `$state`, import `UserRead`/`ProfileRead` from `$lib/types` |
| `src/lib/components/ItemTable.svelte` | `lang="ts"`, type actual props (`apiEndpoint`, `requireAuth`, `showOnlySaved`), inline types |
| `src/lib/components/charts/EChartsLineChart.svelte` | `lang="ts"`, keep `// @ts-nocheck`, type props |
| `src/lib/components/crafting/InventoryModal.svelte` | `lang="ts"`, replace `IngredientNode` typedef with `CraftNode` |
| `src/lib/components/crafting/RecipeCard.svelte` | `lang="ts"`, replace both typedefs |
| `src/lib/components/crafting/RecipeTree.svelte` | `lang="ts"`, replace typedef, type snippet params |
| `src/routes/+layout.svelte` | `lang="ts"` |
| `src/routes/+page.svelte` | `lang="ts"`, inline `@type` annotations |
| `src/routes/auth/+page.svelte` | `lang="ts"`, type `handleSubmit(e: SubmitEvent)` |
| `src/routes/inventory/+page.svelte` | `lang="ts"`, replace typedefs, fix `debounceTimers` (plain, not `$state`) |
| `src/routes/items/+page.svelte` | `lang="ts"` only (no JSDoc, trivial) |
| `src/routes/items/[id]/+page.svelte` | `lang="ts"`, replace 4 typedefs, type all functions |
| `src/routes/saved-items/+page.svelte` | `lang="ts"` (1-line script block) |
| `src/routes/settings/+page.svelte` | `lang="ts"`, type `handleSave(e: SubmitEvent)` |
| `src/routes/about/+page.svelte` | **Skip** — no script block |

---

## Task 1: Install openapi-typescript and update package.json / tsconfig

**Files:**
- Modify: `frontend/package.json`
- Rename: `frontend/jsconfig.json` → `frontend/tsconfig.json`

- [ ] **Step 1: Install openapi-typescript**

```bash
cd frontend
npm install -D openapi-typescript@latest
```

Expected: `openapi-typescript` appears in `devDependencies` in `package.json`.

- [ ] **Step 2: Add gen:types script and fix check script**

In `frontend/package.json`, update `"scripts"`:
```json
"scripts": {
    "dev": "vite dev",
    "build": "vite build",
    "preview": "vite preview",
    "prepare": "svelte-kit sync || echo ''",
    "check": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json",
    "check:watch": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json --watch",
    "gen:types": "openapi-typescript http://localhost:8000/openapi.json -o src/lib/api.d.ts"
},
```

- [ ] **Step 3: Rename jsconfig.json → tsconfig.json**

Delete `frontend/jsconfig.json` and create `frontend/tsconfig.json`:
```json
{
    "extends": "./.svelte-kit/tsconfig.json",
    "compilerOptions": {
        "allowJs": true,
        "checkJs": true,
        "esModuleInterop": true,
        "forceConsistentCasingInFileNames": true,
        "resolveJsonModule": true,
        "skipLibCheck": true,
        "sourceMap": true,
        "strict": true,
        "moduleResolution": "bundler"
    },
    "include": ["src/**/*.ts", "src/**/*.svelte", "src/**/*.d.ts", "src/**/*.js"]
}
```

> **Note:** `src/**/*.js` is kept in `include` during the migration so JS files continue to be type-checked. Remove it after all files are renamed to `.ts` in Task 3.

- [ ] **Step 4: Commit**

```bash
cd frontend
git rm jsconfig.json
git add package.json package-lock.json tsconfig.json
git commit -m "chore: add openapi-typescript, rename jsconfig→tsconfig"
```

---

## Task 2: Generate api.d.ts and write types.ts

**Files:**
- Create: `frontend/src/lib/api.d.ts` (generated)
- Create: `frontend/src/lib/types.ts`

- [ ] **Step 1: Start the backend**

```bash
# from repo root
make dev-up
# or without Docker:
cd backend && uv run fastapi dev app/main.py
```

Wait until `http://localhost:8000/docs` loads.

- [ ] **Step 2: Generate api.d.ts**

```bash
cd frontend
npm run gen:types
```

Expected: `src/lib/api.d.ts` created. Verify it contains `export type components = { schemas: { CraftResult: ..., InventoryItem: ..., ItemRead: ... } }`.

- [ ] **Step 3: Write src/lib/types.ts**

Create `frontend/src/lib/types.ts`:
```ts
import type { components } from './api'

// Items
export type ItemRead       = components['schemas']['ItemRead']
export type ItemListItem   = components['schemas']['ItemListItem']
export type PaginatedItems = components['schemas']['PaginatedItems']

// Prices
export type PricePointRead  = components['schemas']['PricePointRead']
export type PriceBucketRead = components['schemas']['PriceBucketRead']

// Crafting
export type CraftResult  = components['schemas']['CraftResult']
export type CraftNode    = components['schemas']['CraftNode']
export type CraftSummary = components['schemas']['CraftSummary']

// Inventory
export type InventoryItem = components['schemas']['InventoryItem']

// Auth — fastapi-users generates these schema names; verify in api.d.ts
export type UserRead    = components['schemas']['UserRead']
export type ProfileRead = components['schemas']['ProfileRead']

// Local types (not from API)
export interface ChartPoint {
    t: string
    price: number
}

export interface NodeOverride {
    mode: 'craft' | 'buy'
    expanded: boolean
}
```

> **Important:** Import uses `'./api'` (no extension) — required for `verbatimModuleSyntax` compatibility. Do NOT write `'./api.d.ts'`.
>
> **Verify schema names:** After generating `api.d.ts`, search it for `UserRead` and `ProfileRead` to confirm fastapi-users uses those exact names. If they differ (e.g. `UserRead_1`), adjust the aliases above.

- [ ] **Step 4: Run check**

```bash
cd frontend
npm run check 2>&1 | head -30
```

Expected: errors only about unconverted `.js`/`.svelte` files. No errors in `types.ts` itself.

- [ ] **Step 5: Commit**

```bash
git add src/lib/api.d.ts src/lib/types.ts
git commit -m "feat(types): generate api.d.ts, add types.ts aliases"
```

---

## Task 3: Rename lib files to .ts

**Files:**
- Rename: `src/lib/index.js` → `src/lib/index.ts`
- Rename: `src/lib/config.js` → `src/lib/config.ts`
- Rename: `src/lib/crafting.js` → `src/lib/crafting.ts`
- Rename: `src/lib/mockData.js` → `src/lib/mockData.ts`
- Rename: `src/lib/currency.js` → `src/lib/currency.ts`
- Rename: `src/lib/grades.js` → `src/lib/grades.ts`
- Rename: `src/lib/auth.svelte.js` → `src/lib/auth.svelte.ts`

- [ ] **Step 1: Rename index.ts, config.ts, crafting.ts (no content changes)**

```bash
cd frontend
git mv src/lib/index.js src/lib/index.ts
git mv src/lib/config.js src/lib/config.ts
git mv src/lib/crafting.js src/lib/crafting.ts
```

- [ ] **Step 2: Rename and update mockData.ts**

```bash
git mv src/lib/mockData.js src/lib/mockData.ts
```

Edit `src/lib/mockData.ts`:
```ts
interface MockItem {
    id: number
    name: string
    description: string
    price: number
}

interface MockUser {
    username: string
    email: string
}

export const mockItems: MockItem[] = [
    { id: 1, name: "Two-handed Sword", description: "Heavy and powerful", price: 15000 },
    { id: 2, name: "Oak Shield", description: "Solid defense", price: 8000 },
    { id: 3, name: "Health Potion", description: "Heals wounds", price: 2500 }
];

export const mockUser: MockUser = {
    username: "TestUser",
    email: "test@example.com"
};
```

- [ ] **Step 3: Rename and update currency.ts**

```bash
git mv src/lib/currency.js src/lib/currency.ts
```

Edit `src/lib/currency.ts` — replace entire content:
```ts
export function splitCurrency(copper: number | null | undefined): { gold: number; silver: number; bronze: number } | null {
    if (copper == null || !Number.isFinite(copper)) return null;
    const abs = Math.round(Math.abs(copper));
    return {
        gold: Math.floor(abs / 10000),
        silver: Math.floor((abs % 10000) / 100),
        bronze: abs % 100,
    };
}

export function formatCurrency(copper: number | null | undefined): string {
    if (copper == null || !Number.isFinite(copper)) return '--';
    if (copper === 0) return '0b';
    const sign = copper < 0 ? '-' : '';
    const c = splitCurrency(copper);
    if (!c) return '--';
    const g = c.gold > 0 ? `${c.gold}g ` : '';
    const s = (c.silver > 0 || c.gold > 0) ? `${c.silver.toString().padStart(2, '0')}s ` : '';
    const b = `${c.bronze.toString().padStart(2, '0')}b`;
    return `${sign}${g}${s}${b}`.trim();
}
```

- [ ] **Step 4: Rename and update grades.ts**

```bash
git mv src/lib/grades.js src/lib/grades.ts
```

Edit `src/lib/grades.ts` — replace entire content:
```ts
export const GRADE_COLORS: Record<string, string> = {
    'All':        '#9ca3af',
    'Grand':      '#9ca3af',
    'Rare':       '#60a5fa',
    'Arcane':     '#34d399',
    'Heroic':     '#c084fc',
    'Unique':     '#fb923c',
    'Celestial':  '#fbbf24',
    'Divine':     '#f472b6',
    'Epic':       '#818cf8',
    'Legendary':  '#f59e0b',
    'Mythic':     '#f87171',
    'Eternal':    '#22d3ee',
};

export function gradeColor(grade: string): string {
    return GRADE_COLORS[grade] ?? '#9ca3af';
}

export function gradeBadgeStyle(grade: string): string {
    const c = gradeColor(grade);
    return `color: ${c}; border-color: ${c}55; text-shadow: 0 0 8px ${c}44;`;
}
```

- [ ] **Step 5: Rename and update auth.svelte.ts**

```bash
git mv src/lib/auth.svelte.js src/lib/auth.svelte.ts
```

Edit `src/lib/auth.svelte.ts` — replace entire content:
```ts
import { goto } from '$app/navigation';
import { API_BASE_URL } from '$lib/config.js';
import type { UserRead, ProfileRead } from '$lib/types';

interface UserState {
    data: UserRead | null
    profile: ProfileRead | null
    isLoggedIn: boolean
    loading: boolean
}

export const user = $state<UserState>({
    data: null,
    profile: null,
    isLoggedIn: false,
    loading: true
});

const API_URL = API_BASE_URL;

export async function fetchProfile(): Promise<void> {
    try {
        const response = await fetch(`${API_URL}/profiles/me`, { credentials: 'include' });
        if (response.ok) {
            user.profile = await response.json();
        }
    } catch (e) {
        console.error("Error fetching profile:", e);
    }
}

export async function checkMe(): Promise<void> {
    try {
        const response = await fetch(`${API_URL}/users/me`, { credentials: 'include' });
        if (response.ok) {
            user.data = await response.json();
            user.isLoggedIn = true;
            await fetchProfile();
        } else {
            user.data = null;
            user.profile = null;
            user.isLoggedIn = false;
        }
    } catch (e) {
        console.error("Session check error:", e);
    } finally {
        user.loading = false;
    }
}

export async function login(email: string, password: string): Promise<{ success: boolean; message?: string }> {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);

    const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        body: formData,
        credentials: 'include'
    });

    if (response.ok) {
        await checkMe();
        goto('/');
        return { success: true };
    } else {
        const error = await response.json();
        return { success: false, message: error.detail || 'Login error' };
    }
}

export async function register(email: string, password: string): Promise<{ success: boolean; message?: string }> {
    const response = await fetch(`${API_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
        credentials: 'include'
    });

    if (response.ok) {
        return await login(email, password);
    } else {
        const error = await response.json();
        return { success: false, message: error.detail || 'Registration error' };
    }
}

export async function updateProfile(profileData: Partial<Pick<ProfileRead, 'display_name' | 'is_private'>>): Promise<{ success: boolean; message?: string }> {
    try {
        const response = await fetch(`${API_URL}/profiles/me`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(profileData),
            credentials: 'include'
        });
        if (response.ok) {
            user.profile = await response.json();
            return { success: true };
        } else {
            const error = await response.json();
            return { success: false, message: error.detail || 'Profile update error' };
        }
    } catch (e) {
        return { success: false, message: 'Network error occurred' };
    }
}

export async function logout(): Promise<void> {
    await fetch(`${API_URL}/auth/logout`, { method: 'POST', credentials: 'include' });
    user.data = null;
    user.profile = null;
    user.isLoggedIn = false;
    goto('/auth');
}
```

> **Note:** The import `from '$lib/config.js'` with `.js` extension still works after renaming to `config.ts` — SvelteKit's `moduleResolution: "bundler"` resolves `.js` imports to `.ts` files. No change needed.

- [ ] **Step 6: Remove src/**/*.js from tsconfig include (all lib files are now .ts)**

Edit `frontend/tsconfig.json` — remove `"src/**/*.js"` from the `include` array:
```json
"include": ["src/**/*.ts", "src/**/*.svelte", "src/**/*.d.ts"]
```

- [ ] **Step 7: Run check**

```bash
cd frontend
npm run check 2>&1 | head -50
```

Expected: errors only in unconverted `.svelte` route/component files. No errors in `.ts` lib files.

- [ ] **Step 8: Commit**

```bash
git add src/lib/
git commit -m "refactor(lib): rename .js→.ts, add TypeScript annotations"
```

---

## Task 4: Convert Svelte components to lang="ts"

**Files:**
- Modify: `src/lib/components/ItemTable.svelte`
- Modify: `src/lib/components/charts/EChartsLineChart.svelte`
- Modify: `src/lib/components/crafting/InventoryModal.svelte`
- Modify: `src/lib/components/crafting/RecipeCard.svelte`
- Modify: `src/lib/components/crafting/RecipeTree.svelte`

- [ ] **Step 1: Convert ItemTable.svelte**

Change `<script>` → `<script lang="ts">`.

Add import:
```ts
import type { ItemListItem } from '$lib/types';
```

Replace the `@typedef` block and all `/** @type {X} */` annotations. The actual props of this component are `apiEndpoint`, `requireAuth`, `showOnlySaved` — NOT an `items` array (the component fetches its own data):

```ts
let {
    apiEndpoint = '/items/',
    requireAuth = false,
    showOnlySaved = false
}: {
    apiEndpoint?: string
    requireAuth?: boolean
    showOnlySaved?: boolean
} = $props();
```

Replace state variable annotations (remove `/** @type {X} */` lines, add inline types):
```ts
let items: ItemListItem[] = $state([]);
let total: number = $state(0);
let fetchError: string | null = $state(null);
let savingIds: Set<number> = $state(new Set());
let savedIds: Set<number> = $state(new Set());
let containerRef: HTMLDivElement | undefined;
```

The component also has a local `splitCurrency` function near the bottom (around line 236) that duplicates `$lib/currency.ts`. Type its parameter:
```ts
function splitCurrency(copper: number | null | undefined) {
```
(The duplicate can be removed later in a cleanup pass — for now, just type it to satisfy the compiler.)

Replace `/** @type {ItemRow[]} */` cast inside `loadMore`:
```ts
const data = await resp.json() as ItemListItem[];
```

- [ ] **Step 2: Convert EChartsLineChart.svelte**

Change `<script>` → `<script lang="ts">`.

**Keep the `// @ts-nocheck` directive** — the ECharts options object is intentionally `any`-typed and removing this directive would require typing the entire ECharts configuration, which is out of scope. With `lang="ts"` + `// @ts-nocheck`, the file compiles cleanly.

Add explicit types to props (the `// @ts-nocheck` directive doesn't prevent Svelte from parsing the `$props()` call for component interface generation):
```ts
import type { ChartPoint } from '$lib/types';

let { points = [], height = 400, materialCost = null }: {
    points?: ChartPoint[]
    height?: number
    materialCost?: number | null
} = $props();
```

Remove the `/** @type {any} */` JSDoc comment (it's in the middle of the `$derived.by` block — `// @ts-nocheck` makes it redundant).

- [ ] **Step 3: Convert InventoryModal.svelte**

Change `<script>` → `<script lang="ts">`.

Remove the `@typedef` block. Add import:
```ts
import type { CraftNode } from '$lib/types';
```

Replace the `$props()` annotation:
```ts
let { open, nodes, batchSize, inventory, onUpdate, onClose }: {
    open: boolean
    nodes: CraftNode[]
    batchSize: number
    inventory: Record<number, number>
    onUpdate: (inv: Record<number, number>) => void
    onClose: () => void
} = $props();
```

Replace `/** @type {IngredientNode[]} */` cast with `as CraftNode[]`.

Replace `/** @type {HTMLInputElement} */` cast with `(e.target as HTMLInputElement)`.

- [ ] **Step 4: Convert RecipeCard.svelte**

Change `<script>` → `<script lang="ts">`.

Remove both `@typedef` blocks. Add import:
```ts
import type { CraftResult, CraftNode, NodeOverride } from '$lib/types';
```

Replace the `$props()` type annotation:
```ts
let { craftTree, batchSize, nodeOverrides, inventory, materialCost, profit, onBatchChange, onToggleMode, onToggleExpand, onSetInventory }: {
    craftTree: CraftResult
    batchSize: number
    nodeOverrides: Record<number, NodeOverride>
    inventory: Record<number, number>
    materialCost: number
    profit: number | null
    onBatchChange: (n: number) => void
    onToggleMode: (id: number) => void
    onToggleExpand: (id: number) => void
    onSetInventory: (id: number, value: number) => void
} = $props();
```

Replace `/** @type {string[]} */` inline annotation with `: string[]`.

Replace `/** @type {HTMLInputElement} */` cast with `(e.target as HTMLInputElement)`.

- [ ] **Step 5: Convert RecipeTree.svelte**

Change `<script>` → `<script lang="ts">`.

Remove the `@typedef` block. Add import:
```ts
import type { CraftNode, NodeOverride } from '$lib/types';
```

Replace the `$props()` annotation:
```ts
let { nodes, batchSize, nodeOverrides, inventory, onToggleMode, onToggleExpand, onSetInventory }: {
    nodes: CraftNode[]
    batchSize: number
    nodeOverrides: Record<number, NodeOverride>
    inventory: Record<number, number>
    onToggleMode: (id: number) => void
    onToggleExpand: (id: number) => void
    onSetInventory: (id: number, value: number) => void
} = $props();
```

In the `{#snippet treeRow(...)}` declaration, add TypeScript parameter types:
```svelte
{#snippet treeRow(node: CraftNode, depth: number, scale: number)}
```

Replace `/** @type {HTMLInputElement} */` cast with `(e.target as HTMLInputElement)`.

- [ ] **Step 6: Run check**

```bash
cd frontend
npm run check 2>&1 | head -50
```

Expected: errors only in route files. No errors in component files.

- [ ] **Step 7: Commit**

```bash
git add src/lib/components/
git commit -m "refactor(components): convert to lang=\"ts\", remove JSDoc typedefs"
```

---

## Task 5: Convert route files to lang="ts"

**Files:**
- Modify: `src/routes/+layout.svelte` — `lang="ts"` only
- Modify: `src/routes/+page.svelte` — `lang="ts"`, inline `@type` annotations
- Modify: `src/routes/auth/+page.svelte` — `lang="ts"`, type `handleSubmit(e: SubmitEvent)`
- Modify: `src/routes/inventory/+page.svelte` — `lang="ts"`, replace typedefs, fix `debounceTimers`
- Modify: `src/routes/items/+page.svelte` — `lang="ts"` only (no JSDoc in this file)
- Modify: `src/routes/items/[id]/+page.svelte` — `lang="ts"`, replace 4 typedefs, type all functions
- Modify: `src/routes/saved-items/+page.svelte` — `lang="ts"` only
- Modify: `src/routes/settings/+page.svelte` — `lang="ts"`, type `handleSave(e: SubmitEvent)`
- **Skip: `src/routes/about/+page.svelte`** — no script block, nothing to do

- [ ] **Step 1: Convert +layout.svelte, items/+page.svelte, saved-items/+page.svelte**

These three files have no JSDoc — change the script tag only:

```html
<script lang="ts">
```

- [ ] **Step 2: Convert +page.svelte (root)**

Change `<script>` → `<script lang="ts">`.

Replace `/** @type {any[]} */` and `/** @type {string|null} */` annotations with inline types:
```ts
let items: any[] = $state([]);
let error: string | null = $state(null);
```

- [ ] **Step 3: Convert auth/+page.svelte**

Change `<script>` → `<script lang="ts">`.

Find `handleSubmit` and replace the JSDoc param with inline TypeScript:
```ts
// Before:
/** @param {SubmitEvent} e */
async function handleSubmit(e) {

// After:
async function handleSubmit(e: SubmitEvent) {
```

- [ ] **Step 4: Convert settings/+page.svelte**

Change `<script>` → `<script lang="ts">`.

Same pattern as auth — type `handleSave`:
```ts
async function handleSave(e: SubmitEvent) {
```

- [ ] **Step 5: Convert inventory/+page.svelte**

Change `<script>` → `<script lang="ts">`.

Remove `@typedef` blocks for `ItemRow` and `InventoryRow`. Add import:
```ts
import type { ItemListItem, InventoryItem } from '$lib/types';
```

Replace state variable annotations:
```ts
let allItems: ItemListItem[] = $state([]);
let quantities: Record<number, number> = $state({});
```

**Critical:** `debounceTimers` must remain a plain object (not `$state`) — it is intentionally non-reactive:
```ts
let debounceTimers: Record<number, ReturnType<typeof setTimeout>> = {};
```

Inside `onMount`, replace the fetch casts:
```ts
const data = await resp.json() as ItemListItem[];
// and
const inv = await invResp.json() as InventoryItem[];
quantities = Object.fromEntries(inv.map((r) => [r.item_id, r.quantity]));
```

Replace `/** @type {HTMLInputElement} */` cast with `(e.target as HTMLInputElement)`.

Replace `/** @type {InventoryRow[]} */` inline cast with `as InventoryItem[]`.

- [ ] **Step 6: Convert items/[id]/+page.svelte**

Change `<script>` → `<script lang="ts">`.

Remove all 4 `@typedef` blocks (lines 11-14). Add imports:
```ts
import type { ItemRead, CraftResult, ChartPoint, NodeOverride } from '$lib/types';
```

Replace state variable annotations:
```ts
let item: ItemRead | null = $state(null);
let error: string | null = $state(null);
let chartPoints: ChartPoint[] = $state([]);
let craftTree: CraftResult | null = $state(null);
let craftError: boolean | null = $state(null);
let batchSize: number = $state(1);
let nodeOverrides: Record<number, NodeOverride> = $state({});
let inventory: Record<number, number> = $state({});
```

Type `computeNodeCost` — replace the `@param` JSDoc block with inline TS:
```ts
function computeNodeCost(node: CraftNode, scale: number = batchSize): number {
```

Add `CraftNode` to the import line above.

Type the remaining functions — replace `/** @param {X} */` JSDoc with inline params:
```ts
function timeAgo(iso: string): string {
function handleRangeChange(key: string): void {
function handleBatchChange(n: number): void {
function handleToggleMode(id: number): void {
function handleToggleExpand(id: number): void {
async function handleSetInventory(itemId: number, value: number): Promise<void> {
```

Inside `loadHistory`, replace inline JSDoc casts:
```ts
.map((row: any) => ({ t: row.bucket_start || row.captured_at, price: row.last_price ?? row.price } as ChartPoint))
.filter((row: ChartPoint) => row.t && Number.isFinite(row.price))
.sort((a: ChartPoint, b: ChartPoint) => new Date(a.t).getTime() - new Date(b.t).getTime())
```

In the template, replace the `/** @type {[string, number][]} */` inline cast:
```svelte
{@const statRows = [['min', stats.min], ['max', stats.max], ['avg', stats.avg], ['last', stats.last]] as [string, number][]}
```

- [ ] **Step 7: Run check — final**

```bash
cd frontend
npm run check
```

Expected: **zero errors**. Fix any remaining type errors before committing.

Common fixes:
- Variable inferred as `never` → add explicit type annotation
- `$state()` infers wrong type → use `$state<Type>(...)` generic form
- API response shape mismatch → check exact field names in `api.d.ts`

- [ ] **Step 8: Commit**

```bash
git add src/routes/
git commit -m "refactor(routes): convert to lang=\"ts\", remove JSDoc typedefs"
```

---

## Task 6: Final verification and cleanup

- [ ] **Step 1: Run full check**

```bash
cd frontend
npm run check
```

Expected: `svelte-check` with **0 errors, 0 warnings**.

- [ ] **Step 2: Verify no JSDoc typedefs remain**

```bash
grep -rn "@typedef" frontend/src/
```

Expected: no output.

- [ ] **Step 3: Verify no .js lib files remain**

```bash
ls frontend/src/lib/*.js 2>/dev/null || echo "OK — no .js files"
```

Expected: `OK — no .js files`

- [ ] **Step 4: Final commit**

Stage only the src directory (avoid accidentally staging untracked repo files):
```bash
git add frontend/src/ frontend/package.json frontend/package-lock.json frontend/tsconfig.json
git commit -m "chore: TypeScript migration complete — zero svelte-check errors"
```

---

## Reference: Common Svelte 5 + TypeScript Patterns

```ts
// Typed $state
let x = $state<Type>(initialValue)

// Typed $props() destructuring
let { foo, bar }: { foo: string; bar: number } = $props()

// Casting event target
(e.target as HTMLInputElement).value

// Casting fetch response
const data = await resp.json() as SomeType

// Plain (non-reactive) variable — no $state
let timers: Record<number, ReturnType<typeof setTimeout>> = {}

// Snippet with typed params (Svelte 5)
{#snippet mySnippet(item: CraftNode, depth: number)}

// Import extension: use './api' not './api.d.ts'
import type { components } from './api'
```
