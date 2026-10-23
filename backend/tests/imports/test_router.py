import uuid

from httpx import AsyncClient

from tests.market.test_import import _base, assert_sum, counts, rewrite_fixture


def _files(*named: tuple[str, bytes]) -> list:
    return [("files", (n, d, "text/csv")) for n, d in named]


async def test_import_requires_signed_in_user(client: AsyncClient) -> None:
    r = await client.post("/api/import", files=_files(("m.csv", b"x")))
    assert r.status_code == 401


async def test_market_file_admin_only_per_file(
    client: AsyncClient, make_user, login
) -> None:
    user, pwd = await make_user(superuser=False)
    await login(client, user.email, pwd)
    data = rewrite_fixture("market.csv", uuid.uuid4().hex[:8], _base())
    r = await client.post("/api/import", files=_files(("market.csv", data)))
    assert r.status_code == 200
    [res] = r.json()
    assert res["kind"] == "market"
    assert res["inserted"] == 0
    assert res["errors"] == [{"line": 0, "reason": "admin only"}]
    assert res["rows"] == 406
    assert_sum(res)


async def test_superuser_market_import_still_works(
    superuser_client: AsyncClient,
) -> None:
    s, base = uuid.uuid4().hex[:8], _base()
    r = await superuser_client.post(
        "/api/import",
        files=_files(
            ("market.csv", rewrite_fixture("market.csv", s, base)),
            ("listings.csv", rewrite_fixture("listings.csv", s, base)),
        ),
    )
    assert r.status_code == 200
    first, second = r.json()
    assert counts(first) == ("market", 406, 140, 0, 266, 0)
    assert counts(second) == ("listings", 250, 250, 0, 0, 0)


async def test_unknown_header(superuser_client: AsyncClient) -> None:
    r = await superuser_client.post(
        "/api/import", files=_files(("x.csv", b"a,b\n1,2\n"))
    )
    [res] = r.json()
    assert res["kind"] is None
    assert res["errors"] == [{"line": 0, "reason": "unknown header"}]


async def test_old_market_import_route_is_gone(superuser_client: AsyncClient) -> None:
    r = await superuser_client.post("/api/market/import", files=_files(("m.csv", b"x")))
    assert r.status_code in (404, 405)
