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


async def test_admin_password_form_is_not_a_way_in(make_user) -> None:
    user, pwd = await make_user(superuser=True)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.post(
            "/admin/login",
            data={"username": user.email, "password": pwd},
            follow_redirects=False,
        )
        assert r.status_code in (302, 303)
        assert r.headers["location"] == FRONTEND_AUTH
        assert "fastapiusersauth" not in c.cookies
        r = await c.get("/admin/", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert r.headers["location"] == FRONTEND_AUTH


async def test_admin_login_page_redirects_to_frontend(client: AsyncClient) -> None:
    r = await client.get("/admin/login", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert r.headers["location"] == FRONTEND_AUTH


async def test_admin_logout_clears_cookie(superuser_client: AsyncClient) -> None:
    r = await superuser_client.get("/admin/logout", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert r.headers["location"] == FRONTEND_AUTH
    # Same attributes as fastapi-users' own cookie, so browsers drop the right one.
    set_cookie = r.headers["set-cookie"].lower()
    assert "fastapiusersauth=" in set_cookie
    assert "httponly" in set_cookie
    r = await superuser_client.get("/admin/", follow_redirects=False)
    assert r.headers["location"] == FRONTEND_AUTH
