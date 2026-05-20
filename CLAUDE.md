# ArcheRage Market Tracker
Game marketplace + price tracker (ArcheRage MMO) | FastAPI · SvelteKit 5 · PostgreSQL · podman compose

## Quick reference
- Architecture & DB schema: `docs/ai/architecture.md`
- Stack decisions: `docs/ai/stack.md`
- Code patterns & gotchas: `docs/ai/patterns.md`
- Adding a new domain module: `docs/ai/patterns.md#new-domain`
- Roadmapa: `docs/ai/roadmap.md`
- Constitution: `docs/ai/constitution.md`

## Commands
```bash
# Backend (from backend/)
uv run fastapi dev app/main.py
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "<message>"
uv run pytest

# Docker (from repo root)
make dev-up        # db + backend + frontend
make dev-down
make dev-logs
make test          # test db + pytest
make migrate       # alembic upgrade head in container
make seed          # seed 29 items + recipe tree + 30d history

# Discord bot (from discord_bot/)
uv run python bot.py
uv run pytest -v
```

## Structure
- `backend/app/<domain>/` — models, schemas, services, router, admin (per domain)
- `frontend/src/lib/` — shared state, components, utilities
- `discord_bot/` — separate Python project, own pyproject.toml
- `infra/` — docker-compose.dev.yml + docker-compose.prod.yml + caddy + scrypty serwerowe

## Critical rules
- **NEVER `git push` bez wyraźnej instrukcji** — lokalne commity OK, zapytaj "pushować?" po skończeniu
- **NEVER modify `.env*` files**
- Przeczytaj `docs/ai/architecture.md` przed zmianami w modelach lub routingu
- Przeczytaj `docs/ai/patterns.md` przed dodaniem nowego modułu lub testu
- Wszystkie endpointy pod `/api/` — admin pod `/admin` (nie pod `/api`)
- Singleton limitera w `app/config/rate_limit.py` — NIE twórz drugiego
- `GET /api/inventory/for-recipe/{item_id}` musi być zarejestrowany PRZED `PUT /api/inventory/{item_id}`
- UUID-suffix we wszystkich nazwach itemów w testach (UniqueConstraint name+grade, DB nie jest czyszczone)
- `formatCurrency` i `LABOUR_ITEM_NAME` — importuj z shared lib, nigdy nie redefiniuj lokalnie

## Workflow
1. Nietrywalna zmiana → Plan Mode (Shift+Tab) → czekaj na zatwierdzenie
2. Po zmianach → `uv run pytest` + `svelte-check`
3. Zmiana modelu → `alembic revision --autogenerate` + zweryfikuj migrację

## External memory
See `docs/ai/progress.md` for session continuity notes.