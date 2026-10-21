import uuid

from httpx import AsyncClient

from app.auth.cli import create_superuser


async def test_create_superuser_creates_then_resets(client: AsyncClient) -> None:
    email = f"cli-{uuid.uuid4().hex[:8]}@example.com"
    assert await create_superuser(email, "first-pass-123") is True
    assert await create_superuser(email, "second-pass-123") is False
    r = await client.post(
        "/api/auth/login", data={"username": email, "password": "second-pass-123"}
    )
    assert r.status_code == 204
    assert (await client.get("/api/users/me")).json()["is_superuser"] is True
