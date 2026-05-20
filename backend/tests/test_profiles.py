import asyncio
import os
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.profiles.models import Profile
from app.profiles.services import get_or_create_profile


def _email() -> str:
    return f"prof-{uuid.uuid4().hex[:8]}@test.com"


@pytest.fixture()
async def auth_client(client: AsyncClient) -> AsyncClient:
    email = _email()
    await client.post(
        "/api/auth/register", json={"email": email, "password": "password123"}
    )
    await client.post(
        "/api/auth/login", data={"username": email, "password": "password123"}
    )
    return client


async def test_profile_auto_created_after_register(auth_client: AsyncClient) -> None:
    resp = await auth_client.get("/api/profiles/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_private"] is True


async def test_update_profile_display_name(auth_client: AsyncClient) -> None:
    resp = await auth_client.patch(
        "/api/profiles/me", json={"display_name": "TestPlayer", "is_private": False}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["display_name"] == "TestPlayer"
    assert data["is_private"] is False


async def test_profile_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/profiles/me")
    assert resp.status_code == 401


async def test_get_or_create_profile_concurrent(client: AsyncClient) -> None:
    """ON CONFLICT DO NOTHING handles concurrent inserts without raising IntegrityError."""
    email = f"profile-concurrent-{uuid.uuid4().hex[:8]}@test.com"
    reg = await client.post(
        "/api/auth/register", json={"email": email, "password": "password123"}
    )
    assert reg.status_code == 201
    user_id = uuid.UUID(reg.json()["id"])

    url = os.environ["ASYNC_DATABASE_URL"]
    engine = create_async_engine(url, poolclass=NullPool)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _create_profile():
        async with Session() as session:
            return await get_or_create_profile(session, user_id)

    p1, p2 = await asyncio.gather(_create_profile(), _create_profile())
    assert p1.user_id == user_id
    assert p2.user_id == user_id

    # Verify only one profile row was created
    async with Session() as session:
        count_result = await session.exec(
            select(func.count()).where(Profile.user_id == user_id)
        )
        assert count_result.one() == 1

    await engine.dispose()
