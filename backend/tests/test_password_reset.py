# backend/tests/test_password_reset.py
"""Regression tests for /auth/forgot-password and /auth/reset-password.

The throttled wrappers in app/auth/router.py must parse the JSON body
(per the fastapi-users contract), not interpret parameters as query args.
"""
import uuid

import pytest
from httpx import AsyncClient


def _email() -> str:
    return f"pwreset-{uuid.uuid4().hex[:8]}@test.com"


async def test_forgot_password_accepts_json_body(client: AsyncClient) -> None:
    """Regression: throttled wrapper must parse {"email": ...} from JSON body."""
    email = _email()
    await client.post(
        "/api/auth/register", json={"email": email, "password": "pwd123456"}
    )
    r = await client.post("/api/auth/forgot-password", json={"email": email})
    assert r.status_code != 422, (
        f"JSON body must be accepted (not as query param). Got {r.status_code}: {r.text}"
    )
    assert r.status_code in (200, 202, 204)


async def test_reset_password_accepts_json_body(client: AsyncClient) -> None:
    """Regression: throttled wrapper must parse {token,password} from JSON body."""
    r = await client.post(
        "/api/auth/reset-password",
        json={"token": "fake-token", "password": "newpass123"},
    )
    # Bad token → 400 (RESET_PASSWORD_BAD_TOKEN). NOT 422 (missing query args).
    assert r.status_code != 422, (
        f"JSON body must be accepted (not as query param). Got {r.status_code}: {r.text}"
    )
    assert r.status_code == 400
