import json

import httpx
import respx

from watcher.client import IngestClient, SendOutcome


@respx.mock
async def test_send_batch_returns_success_on_200():
    route = respx.post("http://test/api/ingest/prices").respond(
        200, json={"accepted": 1, "auto_created": 0, "skipped": 0, "errors": []}
    )
    client = IngestClient(api_url="http://test/api/ingest/prices", timeout=5)
    outcome = await client.send_batch(
        [{"name": "x", "grade": 1, "price": 1, "ts": "2026-05-16T18:30:00", "source": "ah"}]
    )

    assert outcome is SendOutcome.SUCCESS
    assert route.called


@respx.mock
async def test_send_batch_returns_skip_on_4xx():
    respx.post("http://test/api/ingest/prices").respond(422, json={"detail": "bad"})
    client = IngestClient(api_url="http://test/api/ingest/prices", timeout=5)
    outcome = await client.send_batch(
        [{"name": "x", "grade": 1, "price": 1, "ts": "2026-05-16T18:30:00", "source": "ah"}]
    )
    assert outcome is SendOutcome.SKIP


@respx.mock
async def test_send_batch_returns_retry_on_5xx():
    respx.post("http://test/api/ingest/prices").respond(500)
    client = IngestClient(api_url="http://test/api/ingest/prices", timeout=5)
    outcome = await client.send_batch(
        [{"name": "x", "grade": 1, "price": 1, "ts": "2026-05-16T18:30:00", "source": "ah"}]
    )
    assert outcome is SendOutcome.RETRY


@respx.mock
async def test_send_batch_returns_retry_on_network_error():
    respx.post("http://test/api/ingest/prices").mock(side_effect=httpx.ConnectError("boom"))
    client = IngestClient(api_url="http://test/api/ingest/prices", timeout=5)
    outcome = await client.send_batch(
        [{"name": "x", "grade": 1, "price": 1, "ts": "2026-05-16T18:30:00", "source": "ah"}]
    )
    assert outcome is SendOutcome.RETRY


@respx.mock
async def test_send_batch_sends_rows_wrapper():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200, json={"accepted": 1, "auto_created": 0, "skipped": 0, "errors": []}
        )

    respx.post("http://test/api/ingest/prices").mock(side_effect=handler)

    client = IngestClient(api_url="http://test/api/ingest/prices", timeout=5)
    await client.send_batch(
        [{"name": "x", "grade": 1, "price": 1, "ts": "2026-05-16T18:30:00", "source": "ah"}]
    )

    assert "rows" in captured["body"]
    assert len(captured["body"]["rows"]) == 1
