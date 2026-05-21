# Independent Project Audit - gpt-5.4

`Started 2026-05-20 20:57, branch audit/gpt-5.4, worktree .worktrees/audit-gpt-5.4, scope backend/frontend/discord_bot/infra/tests/workflow/docs, verification status Complete (frontend check failed)`

## Severity Legend
- `Critical` - data integrity, security, consistency, or major delivery risk
- `Important` - architecture, maintainability, test, or DX issues with meaningful impact
- `Minor` - local inconsistencies, dead code, or lower-impact complexity

## Review Progress
- [x] Backend reviewed
- [x] Frontend reviewed
- [x] Discord bot reviewed
- [x] Infra reviewed
- [x] Tests/workflow/docs reviewed
- [x] Verification commands run

## Executive Summary
The audit found no `Critical` issues, but it did find a broad set of `Important` problems across backend transaction boundaries, frontend UX/data-contract handling, Discord bot API coupling, and CI/infrastructure coverage. The highest-risk themes are silent correctness drift rather than immediate crashes: ingest and price writes have transactional/concurrency gaps, multiple frontend and bot flows hide real failures behind empty or misleading states, and CI/docs do not fully protect or describe the deployed system. Verification was mostly healthy (`backend` and `discord_bot` tests passed), but the frontend quality gate is currently red because `npm run check` fails on an unresolved `PUBLIC_API_URL` env export mismatch.

## Findings
### Critical
No findings in this severity band.
### Important

#### F1
- **Severity:** Important
- **Area:** Frontend
- **Location:** `frontend/src/routes/+layout.svelte:4-11`, `frontend/src/routes/+layout.svelte:80-86`
- **Problem:** The root layout ties rendering of every page to the global `user.loading` flag and calls `checkMe()` unconditionally on mount. Until the auth probe finishes, even public pages like `/`, `/about`, and `/items` are replaced with a full-page spinner.
- **Why it matters:** This makes auth/loading state leak across unrelated pages. A slow or failing `/users/me` request delays the whole app shell, hides already-public content, and makes route behavior depend on a global session check rather than on each page's actual auth needs.
- **Suggested simplification or fix:** Render public children immediately and limit auth gating to routes that actually require it. Keep the navbar/user menu reactive, but move redirects/loading guards into auth-only pages or grouped protected layouts instead of blocking the entire root layout.

#### F2
- **Severity:** Important
- **Area:** Frontend
- **Location:** `frontend/src/lib/components/charts/EChartsLineChart.svelte:2-90`, `frontend/src/routes/items/[id]/+page.svelte:120-126`
- **Problem:** The chart component disables TypeScript entirely with `@ts-nocheck`, and the item page converts history rows with `(row: any)` plus a forced `ChartPoint` cast. That bypasses the generated API schema right where raw server data is reshaped for charting.
- **Why it matters:** This removes type checking from one of the more data-heavy UI paths, so API shape drift or nullable fields can break the chart silently instead of surfacing as compile-time errors. It also makes the frontend's contract with generated OpenAPI types weaker than the rest of the app.
- **Suggested simplification or fix:** Replace the untyped mapping with a small typed adapter based on the generated price-history response shape, and keep `EChartsLineChart.svelte` typed instead of opting the whole file out with `@ts-nocheck`.

#### F3
- **Severity:** Important
- **Area:** Frontend
- **Location:** `frontend/src/routes/items/[id]/+page.svelte:36-57`, `frontend/src/lib/components/crafting/RecipeTree.svelte:19-33`, `frontend/src/lib/components/crafting/RecipeCard.svelte:35-56`
- **Problem:** The frontend repeats the same crafting-tree business rules in multiple places: `computeNodeCost()` exists both in the route and in `RecipeTree`, and the same output-quantity / inventory-adjusted recursion is repeated again in `sumLabour()`.
- **Why it matters:** Profit, material-cost, subtree subtotal, and labour numbers now depend on several hand-kept implementations staying perfectly aligned. Any fix to rounding, inventory handling, or craft-vs-buy rules can easily update one view and leave the others inconsistent.
- **Suggested simplification or fix:** Move the tree traversal rules into one shared helper in `$lib` and derive route summary values plus row subtotals from the same typed utility instead of re-implementing the recursion per component.

#### F4
- **Severity:** Important
- **Area:** Frontend
- **Location:** `frontend/src/routes/inventory/+page.svelte:42-74`, `frontend/src/routes/inventory/+page.svelte:33-40`
- **Problem:** The inventory route downloads the first `/items/` page, then loops through every remaining page sequentially to build a full client-side catalogue before it can render quantity inputs and local filters.
- **Why it matters:** This page is doing too much work locally. Load time grows with total item count, failures in later pages leave a partial catalogue with no explicit error, and the route has to own paging, aggregation, and filtering logic that would be simpler if the backend exposed a focused inventory-edit view or search endpoint.
- **Suggested simplification or fix:** Start with a smaller frontend change: stop eagerly walking every page on load, and instead reuse the existing paginated `/items/` API as the user searches, filters, or scrolls so the route only fetches the slice it currently needs. If that still proves awkward for the inventory UX, a more focused backend endpoint can be a later follow-up rather than the first step.

#### F5
- **Severity:** Important
- **Area:** Frontend
- **Location:** `frontend/src/routes/items/[id]/+page.svelte:131-160`, `frontend/src/routes/inventory/+page.svelte:42-74`
- **Problem:** Several fetch paths silently collapse real failures into empty-looking UI states. `loadCraftTree()` turns a network exception into `hasRecipe = false`, while `inventory/+page.svelte` returns early on non-OK responses without setting any error state.
- **Why it matters:** Users and developers cannot distinguish "this item has no recipe" from "the recipe request failed", or "inventory is empty" from "part of the catalogue failed to load". That hides operational problems behind believable business states and makes frontend behavior harder to debug.
- **Suggested simplification or fix:** Reserve empty states for confirmed domain cases only. Track request failures separately, surface an explicit error banner/retry path, and avoid setting `hasRecipe = false` unless the backend actually returned the semantic 404 case.

#### F6
- **Severity:** Important
- **Area:** Frontend
- **Location:** `frontend/src/lib/config.ts:1`
- **Problem:** Frontend verification currently fails at type-check time because `config.ts` imports `PUBLIC_API_URL` from `$env/static/public`, but the generated env module does not export that symbol in the current repo setup.
- **Why it matters:** This is an immediate CI/local DX break: after installing dependencies, `npm run check` still cannot complete, so the frontend quality gate is red before any application code runs. It also means environment-variable expectations are not aligned with SvelteKit's configured public env surface.
- **Suggested simplification or fix:** Align the frontend config with the actual SvelteKit public env contract. Either define/expose `PUBLIC_API_URL` in the expected environment setup, or change `config.ts` to read the public variable name that the project actually provides and documents.

#### D1
- **Severity:** Important
- **Area:** Discord Bot
- **Location:** `discord_bot/cogs/prices.py:10-27`, `discord_bot/cogs/prices.py:51-77`
- **Problem:** The bot duplicates the backend's ingest grade rules locally via `GRADE_CHOICES` and `GRADE_INT_TO_STR`, then matches `/items/` results by assuming the backend will serialize `grade` with the same capitalized strings (`"Basic"`, `"Grand"`, etc.).
- **Why it matters:** Grade mapping is already a backend-owned domain rule (`backend/app/ingest/grade_map.py`). Any enum rename, serialization change, or new grade added on the backend can make the bot reject valid items or post prices under stale assumptions even though the API itself is still functioning.
- **Suggested simplification or fix:** Keep the lookup flow if needed, but stop owning grade semantics in two places. The minimal fix is to expose one backend-owned representation for grades that the bot can consume directly, so the bot no longer hardcodes the ingest-to-display mapping or compares against enum display strings.

#### D2
- **Severity:** Important
- **Area:** Discord Bot
- **Location:** `discord_bot/cogs/prices.py:44-77`
- **Problem:** `lookup_item()` calls the paginated `/items/` listing with `q=<name>&limit=20` and treats the first page as the complete search space for exact resolution. If the backend search ordering changes or the exact item falls beyond the first 20 matches, the bot returns `not found` even though the item exists.
- **Why it matters:** This is a hidden contract with backend ranking and pagination rather than with a stable API guarantee. Bot correctness now depends on search heuristics in a general list endpoint, which is brittle and hard to notice in tests because the mocked payloads always return the desired item on page one.
- **Suggested simplification or fix:** Keep grade ownership aside and fix the lookup contract itself: use a backend endpoint or filter combination that expresses exact resolution directly, for example exact `name + grade` lookup or an item ID selected from autocomplete. The bot should not infer exactness from one page of fuzzy search results.

#### D3
- **Severity:** Important
- **Area:** Discord Bot
- **Location:** `discord_bot/cogs/prices.py:145-152`, `discord_bot/cogs/prices.py:195-202`
- **Problem:** The command handlers catch `KeyError` and `ValueError` from response parsing together with `httpx.HTTPError` and always tell the user `Backend connection error`. A backend payload shape change, missing field, or unexpected value is therefore reported exactly like a transient transport failure.
- **Why it matters:** This hides contract drift between the bot and backend right at the integration boundary. Operators lose the distinction between "backend is unreachable" and "backend responded with a shape the bot no longer understands," which slows diagnosis and encourages retrying a request that will never succeed until code is updated.
- **Suggested simplification or fix:** Parse backend responses explicitly and separate transport failures from contract-validation failures. Even a small typed adapter plus a distinct log/error path for malformed responses would make boundary issues visible without exposing raw internals to Discord users.

#### D4
- **Severity:** Important
- **Area:** Discord Bot
- **Location:** `discord_bot/bot.py:10-20`, `infra/compose/docker-compose.dev.yml:1-62`, `infra/compose/docker-compose.prod.yml:1-63`
- **Problem:** The bot defaults `API_URL` to `http://backend:8000/api`, which only works from inside the Compose network, but neither dev nor prod Compose defines a `discord_bot` service on that network.
- **Why it matters:** Bot-to-backend connectivity now depends on an undocumented manual override. Running `uv run python bot.py` on the host will fail against the default URL, while the infrastructure files suggest the main runtime topology but omit the bot entirely. That makes the integration easy to misconfigure and harder to reproduce across environments.
- **Suggested simplification or fix:** Make the runtime story explicit in one direction: either add the bot as a first-class service in Compose/prod deployment, or change the default URL to the documented local-host path and require an explicit container-network override when the bot is actually colocated with backend.

#### I1
- **Severity:** Important
- **Area:** Infra
- **Location:** `infra/compose/docker-compose.dev.yml:20-58`, `infra/compose/docker-compose.prod.yml:18-58`
- **Problem:** Only Postgres has a healthcheck. `backend`, `frontend`, and `caddy` rely on plain container start order (`depends_on`) rather than readiness, even though backend startup runs migrations first and frontend/Caddy immediately depend on it serving traffic.
- **Why it matters:** This leaves a startup window where dependent services are "up" from Compose's point of view but not actually ready. In dev that means flaky first loads; in prod Caddy can start proxying to backend/frontend before either has finished booting, turning normal restarts or migrations into user-visible 502s.
- **Suggested simplification or fix:** Add lightweight HTTP healthchecks for backend and frontend, then gate dependents on `condition: service_healthy` instead of bare start ordering. If Caddy stays ungated, at least document that it may begin accepting traffic before upstreams are ready.

#### I2
- **Severity:** Minor
- **Area:** Infra
- **Location:** `infra/caddy/Caddyfile:1-27`
- **Problem:** The production edge configuration proxies requests but does not set any explicit security headers such as HSTS, `X-Content-Type-Options`, or a baseline `Referrer-Policy`.
- **Why it matters:** TLS termination at Caddy is the natural place to enforce browser-facing defaults consistently for both frontend and backend responses. Without them, the deployment leaves common hardening steps to framework defaults or omission, which is a weak production baseline for the single public entrypoint.
- **Suggested simplification or fix:** Add a small `header` block in Caddy for shared browser protections, starting with HSTS (if the domains are HTTPS-only), `X-Content-Type-Options nosniff`, and an explicit `Referrer-Policy`. Keep it centralized there rather than scattering equivalent logic across app layers.

#### I3
- **Severity:** Minor
- **Area:** Infra
- **Location:** `infra/caddy/Caddyfile:11-21`
- **Problem:** The production proxy exposes `/docs`, `/redoc`, and `/openapi.json` on the public site by default, with no path-level restriction or environment switch to disable those documentation/schema surfaces outside local or operator-focused usage.
- **Why it matters:** Public API docs and schema endpoints make service capabilities easier to enumerate and bake a "documentation stays internet-visible" assumption into the edge layer. That is a different operational choice from exposing the authenticated admin panel, and it should be explicit rather than the default public routing behavior.
- **Suggested simplification or fix:** Keep the change minimal: gate the docs/schema handlers behind one environment flag, or remove them from the public Caddy routes by default and enable them only when production documentation exposure is intentionally desired.

#### B1
- **Severity:** Important
- **Area:** Backend
- **Location:** `backend/app/ingest/services.py:20-56`
- **Problem:** `match_or_create_item()` commits the transaction immediately after the item upsert, before `_process_row()` calls `add_price_point()`. When the later price insert fails, `_process_row()` rolls back only the second step, so a skipped ingest row can still leave behind a newly created `Item`.
- **Why it matters:** This splits one logical ingest operation across multiple transactions. It breaks the intended request flow, creates orphaned auto-created items from failed rows, and makes rollback behavior depend on where the failure happened rather than on the row outcome.
- **Suggested simplification or fix:** Keep item creation and price-point insertion in the same transaction. `match_or_create_item()` should flush/reselect without committing, and the caller should commit once after both steps succeed.

#### B2
- **Severity:** Important
- **Area:** Backend
- **Location:** `backend/app/prices/services.py:100-123`
- **Problem:** `add_price_point()` loads `Item`, decides in Python whether `captured_at >= item.last_price_at`, and then commits both rows. Two concurrent requests can read the same stale `last_price_at`, both decide they should win, and the request that commits last can overwrite `current_price` with an older price.
- **Why it matters:** `Item.current_price` is a denormalized summary field that other features read as authoritative. This race condition can silently regress the visible current price even though the append-only `PricePoint` history is correct.
- **Suggested simplification or fix:** Make the `Item` update conditional in SQL inside the same transaction, for example with `UPDATE ... WHERE last_price_at IS NULL OR last_price_at <= :captured_at`, or lock the row with `SELECT ... FOR UPDATE` before applying the comparison.

#### B4
- **Severity:** Important
- **Area:** Backend
- **Location:** `backend/app/user_inventory/services.py:84-89`
- **Problem:** `get_inventory_for_recipe()` catches `AppError` from `build_craft_tree()` and returns `{}`. A broken recipe graph, missing dependency data, or other domain error becomes indistinguishable from "this recipe has no relevant inventory".
- **Why it matters:** This swallows real backend failures at the service boundary and makes debugging data problems much harder. Clients get a successful empty response instead of an error that reflects the actual failure mode.
- **Suggested simplification or fix:** Only return `{}` for the explicit "no recipe" case already checked above. Let unexpected crafting errors propagate through the normal exception mapping, or catch a narrower exception that truly represents an empty result.

#### B5
- **Severity:** Important
- **Area:** Backend
- **Location:** `backend/app/auth/manager.py:18-29`
- **Problem:** `on_after_register()` opens a brand-new session and recreates profile bootstrap logic inline instead of delegating to the profiles service.
- **Why it matters:** Ownership of profile creation is split between auth and profiles, and user registration now spans separate transactions with separate logic paths. That makes auth/profile behavior harder to reason about and increases the chance that the two code paths drift.
- **Suggested simplification or fix:** Keep one profile-bootstrap implementation, but make it usable without an internal commit so registration can decide the transaction boundary explicitly. Minimally, extract the insert-or-ignore logic into a helper that works on the provided session and let the outer caller choose whether to commit.

#### B6
- **Severity:** Important
- **Area:** Backend
- **Location:** `backend/app/admin_auth.py:20-23`
- **Problem:** Admin login catches broad `Exception` and converts every failure into `False`, the same result as bad credentials.
- **Why it matters:** DB failures, dependency breakage, and programming errors are silently reclassified as authentication failures. That removes observability around admin auth problems and makes incident diagnosis much harder.
- **Suggested simplification or fix:** Catch only the specific authentication exception you expect, or let unexpected exceptions propagate so FastAPI/Starlette can log and surface them through normal error handling.

#### T1
- **Severity:** Important
- **Area:** Workflow
- **Location:** `.github/workflows/frontend.yml:15-36`, `frontend/package.json:6-14`
- **Problem:** Frontend CI only runs `svelte-check`. The repo has no frontend test script and the workflow never runs `vite build`, so production build breakage, SSR/import issues, and route-level runtime regressions can merge as long as types still pass.
- **Why it matters:** `svelte-check` is useful but it is not a release gate for the actual artifact users deploy. In a SvelteKit app, build-time failures often come from adapter, server/client boundary, or generated code paths that static type checking alone does not exercise.
- **Suggested simplification or fix:** Keep the workflow small but meaningful: add `npm run build` to CI and introduce one explicit frontend test entrypoint (`npm test`, even if initially narrow) so the workflow validates both the shipped bundle and at least a minimal behavior layer.

#### T2
- **Severity:** Important
- **Area:** Workflow
- **Location:** `.github/workflows/docker.yml:3-17`, `Makefile:2-3`, `infra/compose/docker-compose.dev.yml`, `infra/compose/docker-compose.prod.yml`, `infra/caddy/Caddyfile`
- **Problem:** The Docker workflow is barely wired to the infrastructure it is supposed to protect. On pull requests it runs only when `backend/Dockerfile` or `frontend/Dockerfile` change, and even on pushes it ignores `infra/compose/**`, `infra/caddy/**`, and other runtime-defining files.
- **Why it matters:** The repo's deployment story lives in Compose and Caddy as much as in the Dockerfiles. A broken proxy route, compose command, volume mount, or service definition can land with green CI because the one workflow named `docker build` never sees those changes.
- **Suggested simplification or fix:** Expand the path filters to include `infra/**` and other deployment-defining files, or rename the workflow to reflect that it only validates Dockerfiles. If the goal is real deployment protection, make CI react to the files that actually define runtime topology.

#### T3
- **Severity:** Important
- **Area:** Tests
- **Location:** `backend/tests/test_ingest.py:30-389`, `docs/ai/architecture.md:69-74`, `docs/ai/constitution.md:14-18`
- **Problem:** The ingest tests cover happy paths and partial-success behavior, but they never assert the documented atomicity boundary: if `match_or_create_item()` succeeds and the subsequent price insert fails, the row should not leave behind a newly created item.
- **Why it matters:** This is a data-integrity invariant the docs call out explicitly. Without a regression test, the suite can stay green while failed ingest rows still create orphaned `Item` records that look valid to later readers.
- **Suggested simplification or fix:** Add one focused integration test that forces `add_price_point()` to fail after auto-create and then asserts both the report shape and that no new `Item` persisted for that row.

#### T4
- **Severity:** Important
- **Area:** Tests
- **Location:** `backend/tests/test_prices.py:54-248`, `backend/app/prices/services.py:100-123`, `docs/ai/architecture.md:70`
- **Problem:** The price tests verify ordinary writes and reads, but they never cover the concurrent update case around `Item.current_price`, even though the service computes recency in application code before commit.
- **Why it matters:** `Item.current_price` is a denormalized field that other features read as authoritative. If concurrent writes can overwrite it with an older value, the append-only history may still be correct while the main marketplace value silently regresses.
- **Suggested simplification or fix:** Add one deterministic service-level regression test with two independent sessions and controlled interleaving: let request A read the item, let request B commit a newer timestamp first, then finish request A and assert `Item.current_price` and `last_price_at` still reflect the newer sample. That keeps the race reproducible without relying on flaky timing from generic parallel requests.

#### T5
- **Severity:** Important
- **Area:** Tests
- **Location:** `backend/tests/test_ingest.py:182-389`, `backend/tests/test_prices.py:54-80`, `backend/app/ingest/router.py:12-18`, `backend/app/prices/router.py:46-59`, `docs/ai/patterns.md:45-49`
- **Problem:** The suite does not assert `429` behavior for either of the two rate-limited write endpoints, even though the repo documents rate limiting as part of the public ingest contract and applies the same limiter to authenticated price writes.
- **Why it matters:** These endpoints are part of the repo's abuse-control boundary. A limiter misconfiguration, missing middleware wiring, or decorator drift can ship unnoticed because current tests only cover nominal request/response behavior.
- **Suggested simplification or fix:** Add one small integration test per limited endpoint that makes enough repeated requests to confirm the limiter trips and returns `429`, even if the threshold is lowered or overridden in test configuration to keep the test cheap.

#### T6
- **Severity:** Important
- **Area:** Tests
- **Location:** `backend/tests/test_auth.py:9-107`, `backend/app/admin_auth.py:12-43`
- **Problem:** Auth coverage stops at `/api/auth/*` and `/api/users/me`; there is no smoke test for the separate `/admin` session flow, superuser-only gate, or failure path around `AdminAuth`.
- **Why it matters:** The admin panel is a distinct authentication surface with different session handling from the user JWT-cookie flow. It can regress independently while the ordinary auth tests stay green, leaving the only privileged UI path unguarded by automation.
- **Suggested simplification or fix:** Add one narrow admin-auth test that logs in as a superuser through `/admin`, verifies access to a protected admin page, and confirms a non-superuser cannot authenticate there.

#### T7
- **Severity:** Minor
- **Area:** Tests
- **Location:** `backend/tests/test_consistency.py:14-30`
- **Problem:** The cross-file consistency checks assert raw source text such as `const SOURCE = 'ah'` inside a specific Svelte file instead of verifying the observable behavior through an API or shared contract boundary.
- **Why it matters:** This kind of test is tightly coupled to implementation details and creates false safety. A harmless refactor like moving the constant, renaming a variable, or deriving the source indirectly will fail the test even if behavior is unchanged, while other real mismatches can still slip through if the literal string happens to remain in the file.
- **Suggested simplification or fix:** Keep the cross-file/frontend-contract check, but anchor it to a small shared artifact instead of raw page text. For example, move the chart source token into one frontend helper/config module and have the consistency test read that single file or exported constant shape, while a separate API-level assertion still verifies that `source='ah'` is the backend-visible source used for price-history queries.

#### T8
- **Severity:** Important
- **Area:** Docs
- **Location:** `docs/ai/architecture.md:41-46`, `docs/ai/architecture.md:69-80`, `docs/ai/progress.md:7-29`, `docs/ai/superpowers/specs/2026-05-17-discord-bot-design.md:17-18`
- **Problem:** The developer docs disagree with each other and with the repo state on key workflow facts. `architecture.md` still describes watcher-driven ingestion and says auth lives in `src/lib/auth.svelte.js`, `progress.md` still presents `feature/user-inventory` as the current branch and says audit fixes are already done, and the Discord bot design spec still says the bot is a Compose service even though the infra files do not define one.
- **Why it matters:** These are exactly the docs a maintainer would read before touching tests, workflows, or runtime setup. Conflicting guidance turns basic tasks like reproducing the stack or understanding ingest flow into archaeology, and it weakens trust in the invariants the code relies on.
- **Suggested simplification or fix:** Separate active runbooks from historical design docs more explicitly. Update `architecture.md` and `progress.md` to match the current repo, and mark older superpowers specs/plans as historical when their deployment assumptions no longer reflect reality.

### Minor

#### B3
- **Severity:** Minor
- **Area:** Backend
- **Location:** `backend/app/user_inventory/services.py:8-9`, `backend/app/crafting/services.py:28-36`
- **Problem:** `get_inventory_for_recipe()` depends on three crafting internals at once: `load_all_recipes()`, `load_all_items()`, and `build_craft_tree()`. That reproduces the same orchestration already present in `crafting.services.calculate()` instead of calling one crafting-owned entry point.
- **Why it matters:** The coupling cost is already visible in code: both modules must know the exact recipe-map and item-map shape expected by `build_craft_tree()`. If crafting changes how trees are prepared or validated, inventory must be updated in lockstep even though it only needs ingredient IDs.
- **Suggested simplification or fix:** Keep the behavior, but expose one small crafting service helper for "build recipe tree" or "get ingredient item ids for recipe" so inventory stops depending on multiple low-level crafting functions and data shapes.

## Strengths Worth Keeping
- Most routers stay thin and delegate real work into service functions, which keeps the HTTP layer readable and makes request flow easy to trace.
- `user_inventory.upsert_inventory()` and `user_items.follow_item()` already use PostgreSQL conflict handling instead of naive read-then-write logic, which is the right direction for concurrency-sensitive writes.
- `frontend/src/lib/types.ts` keeps most frontend DTOs aliased to generated OpenAPI schemas instead of redefining them locally, which is the right baseline for contract consistency.
- `frontend/src/lib/components/ItemTable.svelte` is reused by both `/items` and `/saved-items`, avoiding duplicate list markup and keeping watchlist behavior close to the main market table.
- The backend CI workflow does more than just run tests: `ruff`, `uv lock --check`, `pytest`, and `alembic check` together provide a solid baseline for Python dependency, schema, and migration discipline.
- The `docs/ai/architecture.md`, `docs/ai/patterns.md`, and `docs/ai/constitution.md` set is a good idea worth keeping: it captures non-obvious invariants like router ordering, `source='ah'`, and the limiter singleton close to the repo instead of leaving them tribal.

## Verification Run
- `backend`: `uv run pytest` -> PASS (`94 passed, 156 warnings in 12.53s`). Warning theme: repeated SQLModel / fastapi-users deprecation guidance recommending `session.exec()` instead of `session.execute()` in some places.
- `frontend`: initial `npm run check` -> FAIL (`svelte-kit: not found`) before dependencies were installed.
- `frontend`: `npm install` -> PASS.
- `frontend`: rerun `npm run check` -> FAIL with `/frontend/src/lib/config.ts:1:10 Error: Module '"$env/static/public"' has no exported member 'PUBLIC_API_URL'.`
- `discord_bot`: `uv run pytest -v` -> PASS (`21 passed in 1.15s`).

## Suggested Next Actions
1. Fix the two backend correctness risks first: make ingest item creation plus price insertion atomic (`B1`) and make `current_price` updates concurrency-safe (`B2`), then add the missing regression tests (`T3`, `T4`).
2. Restore the frontend verification gate by aligning `PUBLIC_API_URL` with the actual SvelteKit public env contract (`F6`), and add `npm run build` plus a real frontend test entrypoint to CI (`T1`).
3. Remove silent failure masking in user-facing flows: separate domain-empty states from request failures in the frontend (`F5`) and distinguish transport errors from payload/contract errors in the Discord bot (`D3`).
4. Reduce duplicated business rules and brittle cross-service contracts by centralizing crafting-tree calculations in shared frontend helpers (`F3`) and moving Discord grade/exact item lookup semantics behind a backend-owned contract (`D1`, `D2`).
5. Tighten runtime/deployment reliability by making the Discord bot runtime topology explicit (`D4`), adding service readiness checks in Compose (`I1`), and expanding Docker workflow coverage to `infra/**` and related deployment-defining files (`T2`).
6. Bring maintainer-facing docs back in sync with the repo (`T8`) so architecture, progress notes, and bot deployment assumptions stop contradicting current code and infrastructure.
