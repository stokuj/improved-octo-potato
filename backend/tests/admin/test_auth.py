from httpx import AsyncClient


async def test_admin_panel_redirects_unauth_to_login(client: AsyncClient) -> None:
    r = await client.get("/admin/", follow_redirects=False)
    assert r.status_code in (302, 303, 401)
    if r.status_code in (302, 303):
        assert "/admin" in r.headers.get("location", "")
