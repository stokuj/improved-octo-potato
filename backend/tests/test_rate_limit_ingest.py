# backend/tests/test_rate_limit_ingest.py
import uuid

from httpx import AsyncClient


def _email() -> str:
    return f"rl-{uuid.uuid4().hex[:8]}@test.com"


async def test_login_returns_429_after_burst(client: AsyncClient) -> None:
    email = _email()
    await client.post(
        "/api/auth/register", json={"email": email, "password": "pwd123456"}
    )

    responses = []
    for _ in range(6):
        r = await client.post(
            "/api/auth/login",
            data={"username": email, "password": "wrong-on-purpose"},
        )
        responses.append(r.status_code)

    assert 429 in responses
    last = responses[-1]
    assert last == 429, f"expected last call rate-limited, got {responses}"


async def test_register_rate_limited_per_ip(client: AsyncClient) -> None:
    statuses = []
    for _ in range(6):
        r = await client.post(
            "/api/auth/register",
            json={"email": _email(), "password": "pwd123456"},
        )
        statuses.append(r.status_code)

    assert 429 in statuses, f"expected 429 in {statuses}"


async def test_ingest_returns_429_above_threshold(
    client: AsyncClient, ingest_token: str
) -> None:
    headers = {"Authorization": f"Bearer {ingest_token}"}
    payload = {"rows": []}

    seen_429 = False
    for _ in range(65):
        r = await client.post("/api/ingest/prices", json=payload, headers=headers)
        if r.status_code == 429:
            seen_429 = True
            break

    assert seen_429, "ingest must rate-limit above 60/minute"


async def test_limiter_resets_between_tests(client: AsyncClient) -> None:
    email = _email()
    await client.post(
        "/api/auth/register", json={"email": email, "password": "pwd123456"}
    )

    r = await client.post(
        "/api/auth/login", data={"username": email, "password": "pwd123456"}
    )
    assert r.status_code != 429, "rate-limiter state leaked from previous test"


async def test_429_payload_shape(client: AsyncClient) -> None:
    email = _email()
    await client.post(
        "/api/auth/register", json={"email": email, "password": "pwd123456"}
    )

    rate_limited = None
    for _ in range(7):
        r = await client.post(
            "/api/auth/login",
            data={"username": email, "password": "wrong"},
        )
        if r.status_code == 429:
            rate_limited = r
            break

    assert rate_limited is not None, "expected to hit 429"
    body = rate_limited.json()
    assert isinstance(body, dict)
    assert "error" in body or "detail" in body
