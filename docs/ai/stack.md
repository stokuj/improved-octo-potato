# Stack Decisions

## Backend

| Tech | Wersja | Powód wyboru |
|---|---|---|
| FastAPI | ≥0.135 | Async-first, auto OpenAPI schema (używamy do generowania api.d.ts) |
| SQLModel | ≥0.0.38 | ORM łączący SQLAlchemy + Pydantic — jeden model dla DB i schematu |
| fastapi-users | ≥15.0.5 | Auth out-of-the-box: register/login/cookie session, unikamy pisania auth ręcznie |
| Alembic | ≥1.13 | Migracje schematu DB |
| asyncpg + psycopg[binary] | — | asyncpg dla runtime, psycopg dla alembic sync migrations |
| slowapi | ≥0.1.9 | Rate limiting (singleton w `app/config/rate_limit.py`) |
| sqladmin | ≥0.24 | Panel admina pod `/admin`, bez pisania UI |
| PostgreSQL 16 | alpine | Jedyna baza; naive UTC timestamps |
| uv | — | Szybki package manager; każdy projekt ma własny pyproject.toml + uv.lock |
| pytest-asyncio | — | Async testy z prawdziwą bazą (nie mocki) |
| ruff | — | Linter |

## Frontend

| Tech | Wersja | Powód wyboru |
|---|---|---|
| SvelteKit 5 | ≥2.57 | Runes API (`$state`, `$derived`) — brak zewnętrznego store managera |
| Tailwind CSS 4 | ≥4.2 | Utility-first CSS |
| DaisyUI 5 | ≥5.5 | Komponenty UI, theme: `night` |
| ECharts + svelte-echarts | 5.6 / 1.0 | Wykresy cen; markLine dla material cost reference |
| openapi-typescript | ≥7.13 | Generuje `src/lib/api.d.ts` z `/openapi.json`; zero ręcznych typów API |
| adapter-node | ≥5.2 | Produkcyjny build jako Node.js server |
| TypeScript strict | ≥6.0 | `lang="ts"` we wszystkich komponentach; importy z `api.d.ts` |

## Infra

| Tech | Rola |
|---|---|
| Podman Compose | Konteneryzacja (nie docker compose — używamy `podman compose`) |
| Caddy 2 | TLS termination + reverse proxy; `/api/*` i `/admin*` → backend, reszta → frontend |
| podman compose dev | 3 serwisy: db, backend (--reload), frontend (npm dev) |
| podman compose prod | 4 serwisy: db, backend (2 workers), frontend (node build), caddy |

## Decyzje odrzucone

- **Watcher daemon** — usunięty; ceny wchodzą przez Discord bot lub bezpośredni POST
- **External store (Pinia/Zustand)** — zastąpiony przez Svelte 5 runes
- **SQLite w testach** — testy biją w prawdziwy PostgreSQL (test DB: `app_test`)
- **Mock DB w testach** — historia: mocki ukryły błąd migracji produkcyjnej; od tej pory integracyjne
