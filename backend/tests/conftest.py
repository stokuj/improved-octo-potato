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

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

# Import modeli — rejestruje metadata w SQLModel
from app.items.models import Item, ItemCategory, ItemGrade  # noqa: F401
from app.prices.models import PricePoint  # noqa: F401
from app.profiles.models import Profile  # noqa: F401
from app.user_items.models import UserItem  # noqa: F401
from app.users.models import User  # noqa: F401
from app.crafting.models import Recipe, RecipeIngredient  # noqa: F401
from app.user_inventory.models import UserInventory  # noqa: F401
from app.config.db import async_session_maker
from app.config.rate_limit import limiter
from app.config.settings import settings as settings_singleton
from app.main import app

_TEST_URL = os.environ["ASYNC_DATABASE_URL"]


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    # NullPool disables connection reuse between tests — prevents leaked state
    engine = create_async_engine(_TEST_URL, poolclass=NullPool)
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


# --- New fixtures (Task 0.0) -------------------------------------------------


@pytest.fixture()
async def async_client() -> AsyncClient:
    """Fresh AsyncClient using ASGITransport — alias name expected by newer tests."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.fixture()
async def session():
    """Per-test AsyncSession from the app's async_session_maker.

    Note: DB is shared across tests (created once by setup_database).
    Use UUID-suffixed unique names to avoid UniqueConstraint collisions.
    """
    async with async_session_maker() as s:
        yield s


@pytest.fixture()
def session_factory():
    """Returns the async_sessionmaker callable for tests needing multiple sessions."""
    return async_session_maker


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset slowapi limiter state before and after each test to prevent cross-test bleed."""
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture()
async def sample_user(session) -> User:
    """Create a User with UUID-suffixed email and a valid bcrypt password hash.

    Real hash so password-verification code paths (auth/login) can run without
    UnknownHashError. Cleartext is intentionally not exposed — tests that need
    to log in should create their own user with a known password.
    """
    from fastapi_users.password import PasswordHelper

    suffix = uuid.uuid4().hex[:8]
    user = User(
        email=f"user-{suffix}@test.local",
        hashed_password=PasswordHelper().hash(f"pwd-{suffix}"),
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture()
async def sample_item(session) -> Item:
    """Create an Item with UUID-suffixed name (UniqueConstraint name+grade)."""
    suffix = uuid.uuid4().hex[:8]
    item = Item(
        name=f"sample-item-{suffix}",
        category=ItemCategory.CRAFTING,
        grade=ItemGrade.BASIC,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@pytest.fixture()
async def sample_leaf_item(session) -> Item:
    """Distinct Item fixture used as a leaf (no recipe) ingredient."""
    suffix = uuid.uuid4().hex[:8]
    item = Item(
        name=f"leaf-item-{suffix}",
        category=ItemCategory.OTHER,
        grade=ItemGrade.BASIC,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@pytest.fixture()
async def item_with_broken_recipe(session) -> Item:
    """Item + Recipe + RecipeIngredient referencing a non-existent ingredient_item_id.

    PG enforces FK constraints; we bypass via `session_replication_role = replica`
    (requires superuser — test DB connects as `postgres`, which qualifies).
    """
    suffix = uuid.uuid4().hex[:8]
    item = Item(
        name=f"broken-recipe-item-{suffix}",
        category=ItemCategory.CRAFTING,
        grade=ItemGrade.BASIC,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)

    recipe = Recipe(item_id=item.id, output_qty=1)
    session.add(recipe)
    await session.commit()
    await session.refresh(recipe)

    # Bypass FK to insert dangling ingredient reference
    conn = await session.connection()
    await conn.execute(text("SET session_replication_role = replica"))
    try:
        await conn.execute(
            text(
                "INSERT INTO recipeingredient (recipe_id, ingredient_item_id, quantity)"
                " VALUES (:rid, :iid, :qty)"
            ),
            {"rid": recipe.id, "iid": 10**9, "qty": 1},
        )
        await session.commit()
    finally:
        conn2 = await session.connection()
        await conn2.execute(text("SET session_replication_role = DEFAULT"))
        await session.commit()

    return item


@pytest.fixture()
def ingest_token(monkeypatch) -> str:
    """Provide an INGEST_TOKEN env var + settings attribute for ingest endpoints.

    NOTE: `settings.ingest_token` attribute is added in Task 0.6. We use
    `raising=False` so this fixture is forward-compatible — env var is the
    source of truth until the settings field lands.
    """
    token = f"test-ingest-{uuid.uuid4().hex}"
    monkeypatch.setenv("INGEST_TOKEN", token)
    monkeypatch.setattr(settings_singleton, "ingest_token", token, raising=False)
    return token


@pytest.fixture()
async def sample_superuser(session) -> User:
    """Create a superuser with UUID-suffixed email and bcrypt password hash."""
    from fastapi_users.password import PasswordHelper

    suffix = uuid.uuid4().hex[:8]
    user = User(
        email=f"super-{suffix}@test.local",
        hashed_password=PasswordHelper().hash(f"pwd-{suffix}"),
        is_active=True,
        is_superuser=True,
        is_verified=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture()
async def superuser_client() -> AsyncClient:
    """Fresh AsyncClient authenticated as a superuser.

    Creates a separate client (not reusing the shared ``client`` fixture)
    to avoid poisoning ``client``'s cookie jar with superuser credentials.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        suffix = uuid.uuid4().hex[:8]
        email = f"super-login-{suffix}@test.com"
        password = "supertest-pwd-123"
        await c.post(
            "/api/auth/register", json={"email": email, "password": password}
        )
        from app.config.db import async_session_maker
        from app.users.models import User as UserModel
        from sqlmodel import select

        async with async_session_maker() as s:
            u = (await s.exec(select(UserModel).where(UserModel.email == email))).one()
            u.is_superuser = True
            s.add(u)
            await s.commit()

        await c.post(
            "/api/auth/login", data={"username": email, "password": password}
        )
        yield c
