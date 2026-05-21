import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ingest_rejects_missing_token(async_client: AsyncClient):
    r = await async_client.post("/api/ingest/prices", json={"rows": []})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_ingest_rejects_bad_token(async_client: AsyncClient):
    r = await async_client.post(
        "/api/ingest/prices",
        json={"rows": []},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_ingest_accepts_valid_token(async_client: AsyncClient, ingest_token: str):
    r = await async_client.post(
        "/api/ingest/prices",
        json={"rows": []},
        headers={"Authorization": f"Bearer {ingest_token}"},
    )
    assert r.status_code == 200
