# backend/tests/test_user_items_race.py
import asyncio
import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlmodel import select

from app.main import app
from app.user_items.models import UserItem


def _email() -> str:
    return f"ui-race-{uuid.uuid4().hex[:8]}@test.com"


async def _auth_client() -> AsyncClient:
    c = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    email = _email()
    await c.post("/api/auth/register", json={"email": email, "password": "pwd123456"})
    await c.post("/api/auth/login", data={"username": email, "password": "pwd123456"})
    return c


async def test_concurrent_follow_same_item_no_duplicate(
    session_factory, sample_item
) -> None:
    c = await _auth_client()
    try:
        async def follow():
            return await c.post(f"/api/user-items/{sample_item.id}")

        results = await asyncio.gather(*[follow() for _ in range(5)], return_exceptions=True)
        statuses = [r.status_code for r in results if hasattr(r, "status_code")]
        assert all(s < 500 for s in statuses), statuses

        async with session_factory() as s:
            rows = (await s.exec(select(UserItem).where(UserItem.item_id == sample_item.id))).all()
            assert len(rows) == 1, f"expected 1 follow row, got {len(rows)}"
    finally:
        await c.aclose()


async def test_follow_then_unfollow_then_follow_idempotent(
    session_factory, sample_item
) -> None:
    c = await _auth_client()
    try:
        r1 = await c.post(f"/api/user-items/{sample_item.id}")
        assert r1.status_code in (200, 201, 204), r1.text

        r2 = await c.delete(f"/api/user-items/{sample_item.id}")
        assert r2.status_code in (200, 204), r2.text

        r3 = await c.post(f"/api/user-items/{sample_item.id}")
        assert r3.status_code in (200, 201, 204), r3.text

        async with session_factory() as s:
            rows = (await s.exec(select(UserItem).where(UserItem.item_id == sample_item.id))).all()
            assert len(rows) == 1
    finally:
        await c.aclose()


async def test_unfollow_non_existent_returns_404_not_500(sample_item) -> None:
    c = await _auth_client()
    try:
        r = await c.delete(f"/api/user-items/{sample_item.id}")
        assert r.status_code in (404, 204), f"expected 404 or 204, got {r.status_code}"
        assert r.status_code != 500
    finally:
        await c.aclose()
