import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.rate_limit import limiter


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


def _prod_like_app() -> FastAPI:
    from app.auth.router import build_router

    prod = FastAPI()
    prod.state.limiter = limiter
    prod.include_router(build_router(password_login=False), prefix="/api")
    return prod


async def test_prod_has_no_password_login(make_user) -> None:
    user, pwd = await make_user()
    async with AsyncClient(
        transport=ASGITransport(app=_prod_like_app()), base_url="http://test"
    ) as c:
        r = await c.post(
            "/api/auth/login", data={"username": user.email, "password": pwd}
        )
    assert r.status_code in (404, 405)


async def test_prod_logout_works(client: AsyncClient, make_user, login) -> None:
    user, pwd = await make_user()
    await login(client, user.email, pwd)
    async with AsyncClient(
        transport=ASGITransport(app=_prod_like_app()),
        base_url="http://test",
        cookies={"fastapiusersauth": client.cookies["fastapiusersauth"]},
    ) as c:
        r = await c.post("/api/auth/logout")
    assert r.status_code == 204
    set_cookie = r.headers["set-cookie"]
    assert 'fastapiusersauth=""' in set_cookie or "Max-Age=0" in set_cookie


def test_only_one_login_route() -> None:
    from app.main import app

    logins = [r for r in app.routes if getattr(r, "path", None) == "/api/auth/login"]
    assert len(logins) == 1
