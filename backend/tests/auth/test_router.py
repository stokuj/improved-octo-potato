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
    assert "id" in data


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


async def test_logout_clears_cookie(client: AsyncClient) -> None:
    email = _email()
    await client.post(
        "/api/auth/register", json={"email": email, "password": "password123"}
    )
    await client.post(
        "/api/auth/login", data={"username": email, "password": "password123"}
    )

    me_resp = await client.get("/api/users/me")
    assert me_resp.status_code == 200

    logout_resp = await client.post("/api/auth/logout")
    assert logout_resp.status_code == 204

    me_after = await client.get("/api/users/me")
    assert me_after.status_code == 401


async def test_me_does_not_expose_superuser_flag(client: AsyncClient) -> None:
    email = _email()
    await client.post(
        "/api/auth/register", json={"email": email, "password": "password123"}
    )
    await client.post(
        "/api/auth/login", data={"username": email, "password": "password123"}
    )

    resp = await client.get("/api/users/me")
    assert resp.status_code == 200
    body = resp.json()
    assert "is_superuser" not in body
    assert "is_active" not in body
    assert "is_verified" not in body
