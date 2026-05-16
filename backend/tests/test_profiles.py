import uuid
import pytest
from httpx import AsyncClient


def _email() -> str:
    return f"prof-{uuid.uuid4().hex[:8]}@test.com"


@pytest.fixture()
async def auth_client(client: AsyncClient) -> AsyncClient:
    email = _email()
    await client.post("/api/auth/register", json={"email": email, "password": "password123"})
    await client.post("/api/auth/login", data={"username": email, "password": "password123"})
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
