import os

# Musi być PRZED importami z app — pydantic-settings czyta env przy imporcie
# TEST_PG_HOSTPORT lets a local run point at a non-default test server.
os.environ.setdefault("TEST_PG_HOSTPORT", "localhost:5432")
os.environ["ASYNC_DATABASE_URL"] = (
    f"postgresql+asyncpg://postgres:postgres@{os.environ['TEST_PG_HOSTPORT']}/app_test"
)
os.environ["DATABASE_URL"] = (
    f"postgresql+psycopg://postgres:postgres@{os.environ['TEST_PG_HOSTPORT']}/app_test"
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
from app.auth.models import User  # noqa: F401
from app.core.db import async_session_maker
from app.core.rate_limit import limiter
from app.main import app

_TEST_URL = os.environ["ASYNC_DATABASE_URL"]


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    # NullPool disables connection reuse between tests — prevents leaked state
    engine = create_async_engine(_TEST_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        # drop_all cannot remove tables of deleted models that still have FKs to ours.
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
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
        await c.post("/api/auth/register", json={"email": email, "password": password})
        from app.core.db import async_session_maker
        from app.auth.models import User as UserModel
        from sqlmodel import select

        async with async_session_maker() as s:
            u = (await s.exec(select(UserModel).where(UserModel.email == email))).one()
            u.is_superuser = True
            s.add(u)
            await s.commit()

        await c.post("/api/auth/login", data={"username": email, "password": password})
        yield c
