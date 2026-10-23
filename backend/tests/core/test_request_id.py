import asyncio
import re

from httpx import ASGITransport, AsyncClient

from app.core.logging import JsonFormatter, RequestIdMiddleware, request_id


def _requests(caplog):
    return [r for r in caplog.records if r.getMessage() == "http.request"]


async def test_valid_request_id_is_echoed(client):
    r = await client.get("/openapi.json", headers={"X-Request-ID": "abc-123"})
    assert r.headers["x-request-id"] == "abc-123"


async def test_invalid_request_id_is_replaced(client):
    r = await client.get("/openapi.json", headers={"X-Request-ID": "bad id!"})
    assert re.fullmatch(r"[0-9a-f]{32}", r.headers["x-request-id"])


async def test_request_is_logged_once_without_query(client, caplog):
    caplog.set_level("INFO")
    await client.get("/openapi.json?code=secret", headers={"X-Request-ID": "abc-123"})
    [rec] = _requests(caplog)
    assert rec.fields == {
        "method": "GET",
        "path": "/openapi.json",
        "status": 200,
        "ms": rec.fields["ms"],
    }
    assert isinstance(rec.fields["ms"], float)
    assert rec.request_id == "abc-123"
    # caplog.text also holds the test client's own httpx line, so check our line only.
    assert "secret" not in JsonFormatter().format(rec)


async def test_concurrent_requests_keep_their_own_ids(client, caplog):
    caplog.set_level("INFO")
    a, b = await asyncio.gather(
        client.get("/openapi.json", headers={"X-Request-ID": "id-a"}),
        client.get("/openapi.json", headers={"X-Request-ID": "id-b"}),
    )
    assert (a.headers["x-request-id"], b.headers["x-request-id"]) == ("id-a", "id-b")
    assert sorted(r.request_id for r in _requests(caplog)) == ["id-a", "id-b"]


async def test_failing_app_still_logs_500_and_resets_id(caplog):
    caplog.set_level("INFO")

    async def boom(scope, receive, send):
        raise RuntimeError("boom")

    transport = ASGITransport(app=RequestIdMiddleware(boom), raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        await c.get("/x", headers={"X-Request-ID": "id-x"})
    [rec] = _requests(caplog)
    assert rec.fields["status"] == 500
    assert rec.request_id == "id-x"
    # The traceback is logged while the id is still set, so it can be found by id.
    [failed] = [r for r in caplog.records if r.getMessage() == "http.failed"]
    assert failed.exc_info and failed.request_id == "id-x"
    assert request_id.get() == "-"
