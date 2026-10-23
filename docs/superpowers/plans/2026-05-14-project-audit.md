# Project Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kompleksowy audyt backendu: konfiguracja, nowy endpoint cen z aktualizacją `current_price`, pełen zestaw testów integracyjnych, zastąpienie mockData w frontendzie.

**Architecture:** Faza 1 naprawia konfigurację (CORS, Python), Faza 2 dodaje brakujący POST endpoint dla cen i logikę aktualizacji `current_price`, Faza 3 dodaje pytest z testami integracyjnymi na PostgreSQL, Faza 4 zastępuje `mockData.js` prawdziwym API.

**Tech Stack:** FastAPI, SQLModel, PostgreSQL, pytest + pytest-asyncio + httpx, SvelteKit 5

---

## Mapa plików

| Plik | Akcja | Powód |
|---|---|---|
| `backend/.python-version` | Modify | 3.14 RC → 3.13 stable |
| `backend/app/config/settings.py` | Modify | Dodać `cors_origins` |
| `backend/app/main.py` | Modify | Użyć `settings.cors_origins` |
| `backend/app/prices/schemas.py` | Modify | Dodać `PricePointCreate` |
| `backend/app/prices/services.py` | Modify | Dodać `add_price_point()` |
| `backend/app/prices/router.py` | Modify | Dodać POST route |
| `backend/pyproject.toml` | Modify | Dodać dev deps pytest |
| `backend/tests/conftest.py` | Create | Fixtures: engine, client |
| `backend/tests/test_auth.py` | Create | Testy auth flow |
| `backend/tests/test_items.py` | Create | Testy GET items |
| `backend/tests/test_prices.py` | Create | Testy POST cen + current_price |
| `backend/tests/test_user_items.py` | Create | Testy follow/unfollow |
| `backend/tests/test_profiles.py` | Create | Testy profilu |
| `frontend/src/routes/+page.svelte` | Modify | mockData → fetch /items |

---

## Task 1: Konfiguracja — Python 3.13 + CORS do settings

**Files:**
- Modify: `backend/.python-version`
- Modify: `backend/app/config/settings.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Zmień wersję Pythona**

Zawartość `backend/.python-version`:
```
3.13
```

- [ ] **Step 2: Dodaj `cors_origins` do Settings**

W `backend/app/config/settings.py` zastąp istniejącą zawartość:
```python
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/app"
    async_database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/app"
    )
    auth_secret: str = "temporary-development-secret-must-be-32-chars"
    admin_session_secret: str = "temporary-admin-session-secret-must-be-32-chars"
    cookie_secure: bool = False
    sql_echo: bool = False
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    @field_validator("auth_secret", "admin_session_secret")
    @classmethod
    def validate_secrets(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("Secret must be at least 32 characters long")
        return v


settings = Settings()
```

- [ ] **Step 3: Użyj `settings.cors_origins` w main.py**

W `backend/app/main.py` zmień linię z `allow_origins`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Dodaj import na górze:
```python
from app.config.settings import settings
```

- [ ] **Step 4: Zrestartuj serwer dev i sprawdź że startuje**

```bash
cd backend
uv run fastapi dev app/main.py
```

Oczekiwane: serwer startuje bez błędów, `INFO: Application startup complete.`

- [ ] **Step 5: Commit**

```bash
git add backend/.python-version backend/app/config/settings.py backend/app/main.py
git commit -m "config: move CORS origins to settings, downgrade to Python 3.13"
```

---

## Task 2: Endpoint POST /items/{item_id}/prices + aktualizacja current_price

**Files:**
- Modify: `backend/app/prices/schemas.py`
- Modify: `backend/app/prices/services.py`
- Modify: `backend/app/prices/router.py`

- [ ] **Step 1: Dodaj `PricePointCreate` do schemas**

W `backend/app/prices/schemas.py` dodaj na końcu:
```python
from pydantic import Field as PydanticField


class PricePointCreate(BaseModel):
    source: str = PydanticField(min_length=1, max_length=40)
    price: int = PydanticField(ge=0)
    captured_at: datetime
```

- [ ] **Step 2: Dodaj `add_price_point()` do services**

W `backend/app/prices/services.py` zmień istniejącą linię importu schemas na:
```python
from app.prices.schemas import PriceBucketRead, PricePointCreate, PricePointRead
```

Następnie dodaj funkcję na końcu pliku:
```python
async def add_price_point(
    session: AsyncSession,
    item_id: int,
    data: PricePointCreate,
) -> PricePoint:
    item = await session.get(Item, item_id)
    if item is None:
        raise NotFoundError("Item not found")

    point = PricePoint(
        item_id=item_id,
        source=data.source,
        price=data.price,
        captured_at=data.captured_at,
    )
    session.add(point)

    item.current_price = data.price
    item.updated_at = datetime.now(timezone.utc)
    session.add(item)

    await session.commit()
    await session.refresh(point)
    return point
```

- [ ] **Step 3: Dodaj POST route do router.py**

W `backend/app/prices/router.py` zastąp istniejące importy z `app.prices`:
```python
from app.prices.schemas import PriceBucketRead, PricePointCreate, PricePointRead
from app.prices import services
```

(usuń starą linię `from app.prices.services import get_item_price_history` i zmień wywołanie w istniejącym route na `services.get_item_price_history(...)`)

Na końcu pliku dodaj:
```python
@router.post(
    "/{item_id}/prices",
    response_model=PricePointRead,
    status_code=201,
)
async def create_price_point(
    item_id: int,
    data: PricePointCreate,
    session: AsyncSession = Depends(get_async_session),
) -> PricePointRead:
    point = await services.add_price_point(session, item_id, data)
    return PricePointRead(
        item_id=point.item_id,
        source=point.source,
        price=point.price,
        captured_at=point.captured_at,
    )
```

- [ ] **Step 4: Sprawdź endpoint w Swagger**

Uruchom serwer i przejdź na `http://localhost:8000/docs`. Sprawdź że `POST /items/{item_id}/prices` jest widoczny.

- [ ] **Step 5: Commit**

```bash
git add backend/app/prices/schemas.py backend/app/prices/services.py backend/app/prices/router.py
git commit -m "feat: add POST price endpoint, update Item.current_price on ingest"
```

---

## Task 3: Infrastruktura testów

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

**Wymagania wstępne:** Uruchomiony PostgreSQL (przez `docker compose up db -d`). Utwórz bazę testową:
```bash
docker exec -it improved-octo-potato-db-1 psql -U postgres -c "CREATE DATABASE app_test;"
```

- [ ] **Step 1: Dodaj dev dependencies do pyproject.toml**

W `backend/pyproject.toml` dodaj sekcję:
```toml
[dependency-groups]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "httpx>=0.27",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

Zainstaluj:
```bash
cd backend
uv sync --group dev
```

- [ ] **Step 2: Utwórz `backend/tests/__init__.py`**

Plik pusty:
```python
```

- [ ] **Step 3: Utwórz `backend/tests/conftest.py`**

```python
import os

# Musi być PRZED importami z app — pydantic-settings czyta env przy imporcie
os.environ["ASYNC_DATABASE_URL"] = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/app_test"
)
os.environ["DATABASE_URL"] = (
    "postgresql+psycopg://postgres:postgres@localhost:5432/app_test"
)
os.environ["AUTH_SECRET"] = "test-secret-must-be-at-least-32-characters-here"
os.environ["ADMIN_SESSION_SECRET"] = "test-admin-secret-must-be-32-chars-here"

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

# Import modeli — rejestruje metadata w SQLModel
from app.items.models import Item  # noqa: F401
from app.prices.models import PricePoint  # noqa: F401
from app.profiles.models import Profile  # noqa: F401
from app.user_items.models import UserItem  # noqa: F401
from app.users.models import User  # noqa: F401
from app.main import app

_TEST_URL = os.environ["ASYNC_DATABASE_URL"]


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    engine = create_async_engine(_TEST_URL)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await engine.dispose()


@pytest.fixture()
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
```

- [ ] **Step 4: Sprawdź że pytest zbiera testy bez błędów**

```bash
cd backend
uv run pytest --collect-only
```

Oczekiwane: `no tests ran` lub lista testów (jeśli już są), żadnych ImportError.

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/tests/
git commit -m "test: add pytest infrastructure with PostgreSQL test database"
```

---

## Task 4: Testy auth

**Files:**
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Napisz testy**

Utwórz `backend/tests/test_auth.py`:
```python
import uuid
from httpx import AsyncClient


def _email() -> str:
    return f"user-{uuid.uuid4().hex[:8]}@test.com"


async def test_register_creates_user(client: AsyncClient) -> None:
    email = _email()
    resp = await client.post("/auth/register", json={"email": email, "password": "password123"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == email
    assert data["is_active"] is True


async def test_register_duplicate_returns_400(client: AsyncClient) -> None:
    email = _email()
    await client.post("/auth/register", json={"email": email, "password": "password123"})
    resp = await client.post("/auth/register", json={"email": email, "password": "password123"})
    assert resp.status_code == 400


async def test_login_sets_cookie(client: AsyncClient) -> None:
    email = _email()
    await client.post("/auth/register", json={"email": email, "password": "password123"})
    resp = await client.post(
        "/auth/login",
        data={"username": email, "password": "password123"},
    )
    assert resp.status_code == 200
    assert "fastapiusers_token" in resp.cookies


async def test_login_wrong_password_returns_400(client: AsyncClient) -> None:
    email = _email()
    await client.post("/auth/register", json={"email": email, "password": "password123"})
    resp = await client.post(
        "/auth/login",
        data={"username": email, "password": "wrongpassword"},
    )
    assert resp.status_code == 400


async def test_me_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/users/me")
    assert resp.status_code == 401


async def test_me_returns_user_after_login(client: AsyncClient) -> None:
    email = _email()
    await client.post("/auth/register", json={"email": email, "password": "password123"})
    await client.post("/auth/login", data={"username": email, "password": "password123"})
    resp = await client.get("/users/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == email
```

- [ ] **Step 2: Uruchom i sprawdź wynik**

```bash
cd backend
uv run pytest tests/test_auth.py -v
```

Oczekiwane: 6 testów PASSED.

> **Jeśli `fastapiusers_token` nie jest nazwą cookie:** uruchom `test_login_sets_cookie` z `print(resp.cookies)` żeby zobaczyć faktyczną nazwę i popraw asercję.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_auth.py
git commit -m "test: add auth integration tests (register, login, me)"
```

---

## Task 5: Testy items

**Files:**
- Create: `backend/tests/test_items.py`

Wymaganie: w bazie testowej muszą być jakieś itemy. Dodamy je przez fixtures.

- [ ] **Step 1: Napisz testy**

Utwórz `backend/tests/test_items.py`:
```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from app.items.models import Item, ItemCategory, ItemGrade
import os

_TEST_URL = os.environ["ASYNC_DATABASE_URL"]


@pytest.fixture()
async def db_session():
    engine = create_async_engine(_TEST_URL)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture()
async def sample_item(db_session: AsyncSession) -> Item:
    item = Item(
        name="Test Sword",
        category=ItemCategory.WEAPONS,
        grade=ItemGrade.RARE,
        current_price=5000,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


async def test_get_items_returns_list(client: AsyncClient, sample_item: Item) -> None:
    resp = await client.get("/items/")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


async def test_get_items_filter_by_category(client: AsyncClient, sample_item: Item) -> None:
    resp = await client.get("/items/", params={"category": ItemCategory.WEAPONS})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["category"] == ItemCategory.WEAPONS for i in items)


async def test_get_items_filter_by_name(client: AsyncClient, sample_item: Item) -> None:
    resp = await client.get("/items/", params={"q": "Test Sword"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(i["name"] == "Test Sword" for i in data["items"])


async def test_get_item_by_id(client: AsyncClient, sample_item: Item) -> None:
    resp = await client.get(f"/items/{sample_item.id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Sword"


async def test_get_item_not_found(client: AsyncClient) -> None:
    resp = await client.get("/items/99999999")
    assert resp.status_code == 404
```

- [ ] **Step 2: Uruchom testy**

```bash
cd backend
uv run pytest tests/test_items.py -v
```

Oczekiwane: 5 testów PASSED.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_items.py
git commit -m "test: add items integration tests (list, filter, detail, not-found)"
```

---

## Task 6: Testy cen i aktualizacji current_price

**Files:**
- Create: `backend/tests/test_prices.py`

- [ ] **Step 1: Napisz testy**

Utwórz `backend/tests/test_prices.py`:
```python
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from app.items.models import Item, ItemCategory, ItemGrade
import os

_TEST_URL = os.environ["ASYNC_DATABASE_URL"]


@pytest.fixture()
async def db_session():
    engine = create_async_engine(_TEST_URL)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture()
async def price_item(db_session: AsyncSession) -> Item:
    item = Item(
        name="Price Test Item",
        category=ItemCategory.CONSUMABLES,
        grade=ItemGrade.GRAND,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


async def test_post_price_point_returns_201(client: AsyncClient, price_item: Item) -> None:
    resp = await client.post(
        f"/items/{price_item.id}/prices",
        json={
            "source": "market",
            "price": 12345,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["price"] == 12345
    assert data["source"] == "market"


async def test_post_price_updates_current_price(
    client: AsyncClient, price_item: Item, db_session: AsyncSession
) -> None:
    await client.post(
        f"/items/{price_item.id}/prices",
        json={
            "source": "market",
            "price": 99999,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    await db_session.refresh(price_item)
    assert price_item.current_price == 99999


async def test_post_price_for_missing_item_returns_404(client: AsyncClient) -> None:
    resp = await client.post(
        "/items/99999999/prices",
        json={
            "source": "market",
            "price": 100,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert resp.status_code == 404


async def test_get_price_history_raw(client: AsyncClient, price_item: Item) -> None:
    await client.post(
        f"/items/{price_item.id}/prices",
        json={
            "source": "auction",
            "price": 500,
            "captured_at": "2026-01-01T12:00:00Z",
        },
    )
    resp = await client.get(
        f"/items/{price_item.id}/price-history",
        params={"source": "auction", "interval": "raw"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["price"] == 500
```

- [ ] **Step 2: Uruchom testy**

```bash
cd backend
uv run pytest tests/test_prices.py -v
```

Oczekiwane: 4 testy PASSED.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_prices.py
git commit -m "test: add price ingestion tests, verify current_price update"
```

---

## Task 7: Testy user_items

**Files:**
- Create: `backend/tests/test_user_items.py`

Uwaga: `follow_item` w services.py już obsługuje duplikaty — sprawdza przed insertem i zwraca `False`, router zwraca 204. Nie ma ryzyka 500. Testy weryfikują to zachowanie.

- [ ] **Step 1: Napisz testy**

Utwórz `backend/tests/test_user_items.py`:
```python
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from app.items.models import Item, ItemCategory, ItemGrade
import os

_TEST_URL = os.environ["ASYNC_DATABASE_URL"]


def _email() -> str:
    return f"ui-{uuid.uuid4().hex[:8]}@test.com"


@pytest.fixture()
async def db_session():
    engine = create_async_engine(_TEST_URL)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture()
async def tracked_item(db_session: AsyncSession) -> Item:
    item = Item(
        name="Tracked Item",
        category=ItemCategory.ARMOR,
        grade=ItemGrade.HEROIC,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


@pytest.fixture()
async def auth_client(client: AsyncClient) -> AsyncClient:
    email = _email()
    await client.post("/auth/register", json={"email": email, "password": "password123"})
    await client.post("/auth/login", data={"username": email, "password": "password123"})
    return client


async def test_follow_item_returns_201(auth_client: AsyncClient, tracked_item: Item) -> None:
    resp = await auth_client.post(f"/user-items/{tracked_item.id}")
    assert resp.status_code == 201


async def test_follow_duplicate_returns_204(auth_client: AsyncClient, tracked_item: Item) -> None:
    await auth_client.post(f"/user-items/{tracked_item.id}")
    resp = await auth_client.post(f"/user-items/{tracked_item.id}")
    assert resp.status_code == 204


async def test_get_followed_ids_contains_item(auth_client: AsyncClient, tracked_item: Item) -> None:
    await auth_client.post(f"/user-items/{tracked_item.id}")
    resp = await auth_client.get("/user-items/ids")
    assert resp.status_code == 200
    assert tracked_item.id in resp.json()


async def test_unfollow_item_returns_204(auth_client: AsyncClient, tracked_item: Item) -> None:
    await auth_client.post(f"/user-items/{tracked_item.id}")
    resp = await auth_client.delete(f"/user-items/{tracked_item.id}")
    assert resp.status_code == 204


async def test_unfollow_removes_from_ids(auth_client: AsyncClient, tracked_item: Item) -> None:
    await auth_client.post(f"/user-items/{tracked_item.id}")
    await auth_client.delete(f"/user-items/{tracked_item.id}")
    resp = await auth_client.get("/user-items/ids")
    assert tracked_item.id not in resp.json()


async def test_follow_requires_auth(client: AsyncClient, tracked_item: Item) -> None:
    resp = await client.post(f"/user-items/{tracked_item.id}")
    assert resp.status_code == 401
```

- [ ] **Step 2: Uruchom testy**

```bash
cd backend
uv run pytest tests/test_user_items.py -v
```

Oczekiwane: 6 testów PASSED.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_user_items.py
git commit -m "test: add user items integration tests (follow, unfollow, auth guard)"
```

---

## Task 8: Testy profiles

**Files:**
- Create: `backend/tests/test_profiles.py`

- [ ] **Step 1: Napisz testy**

Utwórz `backend/tests/test_profiles.py`:
```python
import uuid
import pytest
from httpx import AsyncClient


def _email() -> str:
    return f"prof-{uuid.uuid4().hex[:8]}@test.com"


@pytest.fixture()
async def auth_client(client: AsyncClient) -> AsyncClient:
    email = _email()
    await client.post("/auth/register", json={"email": email, "password": "password123"})
    await client.post("/auth/login", data={"username": email, "password": "password123"})
    return client


async def test_profile_auto_created_after_register(auth_client: AsyncClient) -> None:
    resp = await auth_client.get("/profiles/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_private"] is True


async def test_update_profile_display_name(auth_client: AsyncClient) -> None:
    resp = await auth_client.patch(
        "/profiles/me", json={"display_name": "TestPlayer", "is_private": False}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["display_name"] == "TestPlayer"
    assert data["is_private"] is False


async def test_profile_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/profiles/me")
    assert resp.status_code == 401
```

- [ ] **Step 2: Sprawdź endpoint `/profiles/me`**

Upewnij się że taki endpoint istnieje — sprawdź `backend/app/profiles/router.py`. Jeśli nie ma `GET /profiles/me`, dodaj go (patrz krok 2b poniżej). Jeśli jest — przejdź do Step 3.

**Step 2b (jeśli endpoint nie istnieje):** Sprawdź router profiles i dodaj brakujące endpointy zgodnie ze wzorcem innych routerów (GET /profiles/me, PATCH /profiles/me używając `get_or_create_profile` i `update_profile` z services.py).

- [ ] **Step 3: Uruchom testy**

```bash
cd backend
uv run pytest tests/test_profiles.py -v
```

Oczekiwane: 3 testy PASSED.

- [ ] **Step 4: Uruchom cały suite testów**

```bash
cd backend
uv run pytest -v
```

Oczekiwane: wszystkie testy PASSED (łącznie ~24).

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_profiles.py
git commit -m "test: add profiles integration tests (auto-create, update, auth guard)"
```

---

## Task 9: Frontend — zastąpienie mockData prawdziwym API

**Files:**
- Modify: `frontend/src/routes/+page.svelte`

`mockData.js` jest używany tylko w `+page.svelte` (sekcja "Hot Deals"). Zastępujemy go wywołaniem `GET /items?limit=3`.

- [ ] **Step 1: Zastąp mockData fetchem w +page.svelte**

Zastąp całą zawartość `frontend/src/routes/+page.svelte`:
```svelte
<script>
    import { API_BASE_URL } from '$lib/config.js';

    let items = $state([]);
    let loading = $state(true);
    let error = $state(null);

    async function loadHotItems() {
        try {
            const resp = await fetch(`${API_BASE_URL}/items/?limit=3`);
            if (!resp.ok) throw new Error('Failed to fetch items');
            const data = await resp.json();
            items = data.items;
        } catch (e) {
            error = 'Could not load items.';
        } finally {
            loading = false;
        }
    }

    loadHotItems();
</script>

<div class="space-y-12">
    <!-- Hero section -->
    <section class="hero bg-gradient-to-br from-base-200 to-base-300 rounded-box p-12 shadow-inner overflow-hidden relative">
        <div class="absolute -right-20 -top-20 w-64 h-64 bg-primary/10 rounded-full blur-3xl"></div>
        <div class="absolute -left-20 -bottom-20 w-64 h-64 bg-secondary/10 rounded-full blur-3xl"></div>

        <div class="hero-content text-center relative z-10">
            <div class="max-w-2xl">
                <h1 class="text-6xl font-black text-primary tracking-tighter">AA Tracker <span class="text-base-content">Svelte</span></h1>
                <p class="py-6 text-xl text-base-content/70 font-medium">
                    The fastest item price tracker from <span class="text-secondary font-bold">Item House</span>. Monitor the market, track changes, and optimize your inventory.
                </p>
                <div class="flex gap-4 justify-center">
                    <a href="/items" class="btn btn-primary btn-lg shadow-xl hover:scale-105 transition-all">Browse Market</a>
                    <a href="/auth" class="btn btn-outline btn-lg hover:scale-105 transition-all">Join Us</a>
                </div>
            </div>
        </div>
    </section>

    <!-- Market Overview -->
    <section class="space-y-4">
        <div class="flex justify-between items-center px-2">
            <h2 class="text-2xl font-black uppercase tracking-widest opacity-80">Hot Deals</h2>
            <a href="/items" class="link link-primary no-underline font-bold text-sm">See all &rarr;</a>
        </div>

        {#if loading}
            <div class="flex justify-center py-12">
                <span class="loading loading-spinner loading-lg text-primary"></span>
            </div>
        {:else if error}
            <div class="alert alert-error">
                <span>{error}</span>
            </div>
        {:else if items.length === 0}
            <div class="text-center py-12 opacity-50">No items found.</div>
        {:else}
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {#each items as item}
                    <a href="/items/{item.id}" class="card bg-base-100 shadow-md border border-base-200 hover:border-primary/50 transition-all cursor-pointer overflow-hidden">
                        <div class="card-body p-6">
                            <div class="flex justify-between items-start">
                                <h3 class="card-title text-primary">{item.name}</h3>
                                <div class="badge badge-ghost badge-sm font-bold">{item.grade}</div>
                            </div>
                            <p class="text-sm opacity-60 italic">{item.category}</p>
                            <div class="divider my-1 opacity-20"></div>
                            <div class="flex justify-between items-end">
                                <div class="text-2xl font-black text-secondary">
                                    {item.current_price != null ? item.current_price.toLocaleString() : '—'}
                                    <span class="text-xs font-normal opacity-50">silver</span>
                                </div>
                                <button class="btn btn-xs btn-primary btn-outline">Track</button>
                            </div>
                        </div>
                    </a>
                {/each}
            </div>
        {/if}
    </section>
</div>
```

- [ ] **Step 2: Uruchom dev server i sprawdź stronę główną**

```bash
cd frontend
npm run dev
```

Otwórz `http://localhost:5173`. Strona powinna:
- Pokazać spinner podczas ładowania
- Pokazać itemy z API (lub "No items found." jeśli baza pusta)
- Pokazać komunikat błędu jeśli backend nie działa

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/+page.svelte
git commit -m "feat: replace mockData with real API fetch on home page"
```

---

## Weryfikacja końcowa

- [ ] Uruchom cały suite testów backendu: `cd backend && uv run pytest -v`
- [ ] Uruchom serwer i frontend, sprawdź stronę główną z działającym backbendem
- [ ] Sprawdź że `mockData.js` nie jest importowany w żadnym `.svelte` (poza samym plikiem)

```bash
grep -r "mockData" frontend/src --include="*.svelte"
```

Oczekiwane: brak wyników.
