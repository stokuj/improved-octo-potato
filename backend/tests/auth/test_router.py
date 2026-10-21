import pytest
from httpx import AsyncClient


async def test_register_route_is_gone(client: AsyncClient) -> None:
    r = await client.post(
        "/api/auth/register", json={"email": "x@example.com", "password": "password123"}
    )
    assert r.status_code in (404, 405)


@pytest.mark.parametrize(
    "path",
    [
        "/api/auth/forgot-password",
        "/api/auth/reset-password",
        "/api/auth/request-verify-token",
        "/api/auth/verify",
    ],
)
async def test_account_flow_routes_are_gone(client: AsyncClient, path: str) -> None:
    assert (await client.post(path, json={})).status_code in (404, 405)


async def test_login_sets_cookie(client: AsyncClient, make_user) -> None:
    user, pwd = await make_user()
    resp = await client.post(
        "/api/auth/login", data={"username": user.email, "password": pwd}
    )
    assert resp.status_code == 204
    assert "fastapiusersauth" in resp.cookies


async def test_login_wrong_password_returns_400(client: AsyncClient, make_user) -> None:
    user, _ = await make_user()
    resp = await client.post(
        "/api/auth/login", data={"username": user.email, "password": "wrongpassword"}
    )
    assert resp.status_code == 400


async def test_me_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/users/me")
    assert resp.status_code == 401


async def test_me_exposes_superuser_flag(client: AsyncClient, make_user, login) -> None:
    user, pwd = await make_user(superuser=True)
    await login(client, user.email, pwd)
    body = (await client.get("/api/users/me")).json()
    assert body == {"id": str(user.id), "email": user.email, "is_superuser": True}


async def test_logout_clears_cookie(client: AsyncClient, make_user, login) -> None:
    user, pwd = await make_user()
    await login(client, user.email, pwd)
    assert (await client.get("/api/users/me")).status_code == 200

    logout_resp = await client.post("/api/auth/logout")
    assert logout_resp.status_code == 204
    assert (await client.get("/api/users/me")).status_code == 401
