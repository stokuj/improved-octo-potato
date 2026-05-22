import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_rate_limited_after_5_attempts(async_client: AsyncClient):
    """Hammer login with bad creds; the 6th call within a minute must 429."""
    for _ in range(5):
        r = await async_client.post(
            "/api/auth/login",
            data={"username": "x@x.com", "password": "wrong"},
        )
        assert r.status_code in (400, 401)
    r = await async_client.post(
        "/api/auth/login",
        data={"username": "x@x.com", "password": "wrong"},
    )
    assert r.status_code == 429


@pytest.mark.asyncio
async def test_login_throttled_still_accepts_valid_credentials(
    async_client, sample_user
):
    """Even when throttled, the endpoint must continue to parse credentials.

    If the proxy signature is broken, FastAPI returns 422 (form not parsed).
    Either 200 or 400 is acceptable here; what we must NOT see is 422 or 500.
    """
    r = await async_client.post(
        "/api/auth/login",
        data={"username": sample_user.email, "password": "correct-horse-battery"},
    )
    assert r.status_code in (200, 400)
