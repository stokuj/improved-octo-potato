from httpx import ASGITransport, AsyncClient

from app.main import app

FRONTEND_AUTH = "http://localhost:5173/auth"


async def test_admin_without_cookie_redirects_to_frontend_auth(
    client: AsyncClient,
) -> None:
    r = await client.get("/admin/", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert r.headers["location"] == FRONTEND_AUTH


async def test_admin_superuser_cookie_ok(superuser_client: AsyncClient) -> None:
    r = await superuser_client.get("/admin/", follow_redirects=False)
    assert r.status_code == 200


async def test_admin_non_superuser_cookie_redirects(make_user, login) -> None:
    user, pwd = await make_user(superuser=False)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        await login(c, user.email, pwd)
        r = await c.get("/admin/", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert r.headers["location"] == FRONTEND_AUTH


async def test_admin_garbage_cookie_redirects() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={"fastapiusersauth": "garbage"},
    ) as c:
        r = await c.get("/admin/", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert r.headers["location"] == FRONTEND_AUTH
