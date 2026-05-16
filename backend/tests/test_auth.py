import uuid
from httpx import AsyncClient


def _email() -> str:
    return f"user-{uuid.uuid4().hex[:8]}@test.com"


async def test_register_creates_user(client: AsyncClient) -> None:
    email = _email()
    resp = await client.post(
        "/api/auth/register", json={"email": email, "password": "password123"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == email
    assert data["is_active"] is True


async def test_register_duplicate_returns_400(client: AsyncClient) -> None:
    email = _email()
    await client.post(
        "/api/auth/register", json={"email": email, "password": "password123"}
    )
    resp = await client.post(
        "/api/auth/register", json={"email": email, "password": "password123"}
    )
    assert resp.status_code == 400


async def test_login_sets_cookie(client: AsyncClient) -> None:
    email = _email()
    await client.post(
        "/api/auth/register", json={"email": email, "password": "password123"}
    )
    resp = await client.post(
        "/api/auth/login",
        data={"username": email, "password": "password123"},
    )
    assert resp.status_code == 204
    assert "fastapiusersauth" in resp.cookies


async def test_login_wrong_password_returns_400(client: AsyncClient) -> None:
    email = _email()
    await client.post(
        "/api/auth/register", json={"email": email, "password": "password123"}
    )
    resp = await client.post(
        "/api/auth/login",
        data={"username": email, "password": "wrongpassword"},
    )
    assert resp.status_code == 400


async def test_me_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/users/me")
    assert resp.status_code == 401


async def test_me_returns_user_after_login(client: AsyncClient) -> None:
    email = _email()
    await client.post(
        "/api/auth/register", json={"email": email, "password": "password123"}
    )
    await client.post(
        "/api/auth/login", data={"username": email, "password": "password123"}
    )
    resp = await client.get("/api/users/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == email
