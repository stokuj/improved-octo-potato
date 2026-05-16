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
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

# Import modeli — rejestruje metadata w SQLModel
from app.items.models import Item  # noqa: F401
from app.prices.models import PricePoint  # noqa: F401
from app.profiles.models import Profile  # noqa: F401
from app.user_items.models import UserItem  # noqa: F401
from app.users.models import User  # noqa: F401
from app.crafting.models import Recipe  # noqa: F401
from app.crafting.models import RecipeIngredient  # noqa: F401
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
