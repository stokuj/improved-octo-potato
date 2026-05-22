# backend/tests/test_user_inventory_race.py
import asyncio
import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlmodel import select

from app.main import app
from app.user_inventory.models import UserInventory


def _email() -> str:
    return f"uinv-race-{uuid.uuid4().hex[:8]}@test.com"


async def _auth_client() -> AsyncClient:
    c = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    email = _email()
    await c.post("/api/auth/register", json={"email": email, "password": "pwd123456"})
    await c.post("/api/auth/login", data={"username": email, "password": "pwd123456"})
    return c


async def test_concurrent_upsert_same_item_final_quantity_correct(
    session_factory, sample_item
) -> None:
    c = await _auth_client()
    try:
        async def put(q):
            return await c.put(f"/api/inventory/{sample_item.id}", json={"quantity": q})

        quantities = [1, 5, 10, 25, 100, 250, 500, 1000, 2500, 5000]
        results = await asyncio.gather(*[put(q) for q in quantities], return_exceptions=True)
        statuses = [r.status_code for r in results if hasattr(r, "status_code")]
        assert all(s < 500 for s in statuses), statuses

        async with session_factory() as s:
            rows = (
                await s.exec(select(UserInventory).where(UserInventory.item_id == sample_item.id))
            ).all()
            assert len(rows) == 1, f"expected single row, got {len(rows)}"
            assert rows[0].quantity in quantities
    finally:
        await c.aclose()


async def test_concurrent_set_to_zero_deletes_exactly_once(
    session_factory, sample_item
) -> None:
    c = await _auth_client()
    try:
        r0 = await c.put(f"/api/inventory/{sample_item.id}", json={"quantity": 7})
        assert r0.status_code == 204

        async def delete_zero():
            return await c.put(f"/api/inventory/{sample_item.id}", json={"quantity": 0})

        results = await asyncio.gather(*[delete_zero() for _ in range(5)], return_exceptions=True)
        statuses = [r.status_code for r in results if hasattr(r, "status_code")]
        assert all(s < 500 for s in statuses), statuses

        async with session_factory() as s:
            rows = (
                await s.exec(select(UserInventory).where(UserInventory.item_id == sample_item.id))
            ).all()
            assert len(rows) == 0, "row should be deleted"
    finally:
        await c.aclose()


async def test_upsert_then_delete_race_no_orphan(
    session_factory, sample_item
) -> None:
    c = await _auth_client()
    try:
        async def put5():
            return await c.put(f"/api/inventory/{sample_item.id}", json={"quantity": 5})

        async def put0():
            return await c.put(f"/api/inventory/{sample_item.id}", json={"quantity": 0})

        results = await asyncio.gather(put5(), put0(), put5(), put0(), return_exceptions=True)
        statuses = [r.status_code for r in results if hasattr(r, "status_code")]
        assert all(s < 500 for s in statuses), statuses

        async with session_factory() as s:
            rows = (
                await s.exec(select(UserInventory).where(UserInventory.item_id == sample_item.id))
            ).all()
            assert len(rows) in (0, 1)
            if rows:
                assert rows[0].quantity == 5
    finally:
        await c.aclose()


async def test_for_recipe_endpoint_consistent_under_writes(sample_item) -> None:
    c = await _auth_client()
    try:
        async def put(q):
            return await c.put(f"/api/inventory/{sample_item.id}", json={"quantity": q})

        async def get_for_recipe():
            return await c.get(f"/api/inventory/for-recipe/{sample_item.id}")

        results = await asyncio.gather(
            put(10), get_for_recipe(), put(20), get_for_recipe(), put(30), get_for_recipe()
        )
        for r in results:
            assert r.status_code < 500, f"500 on race: {r.status_code} {r.text}"

        final = await c.get(f"/api/inventory/for-recipe/{sample_item.id}")
        assert final.status_code == 200
        body = final.json()
        assert isinstance(body, dict)
    finally:
        await c.aclose()
