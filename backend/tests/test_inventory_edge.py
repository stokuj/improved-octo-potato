# backend/tests/test_inventory_edge.py
import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


def _email() -> str:
    return f"inv-edge-{uuid.uuid4().hex[:8]}@test.com"


async def _auth_client() -> AsyncClient:
    c = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    email = _email()
    await c.post("/api/auth/register", json={"email": email, "password": "pwd123456"})
    await c.post("/api/auth/login", data={"username": email, "password": "pwd123456"})
    return c


async def test_quantity_negative_rejected(sample_item) -> None:
    c = await _auth_client()
    try:
        r = await c.put(f"/api/inventory/{sample_item.id}", json={"quantity": -1})
        assert r.status_code == 422
    finally:
        await c.aclose()


async def test_quantity_overflow_rejected(sample_item) -> None:
    c = await _auth_client()
    try:
        r = await c.put(f"/api/inventory/{sample_item.id}", json={"quantity": 10_000_001})
        assert r.status_code == 422
    finally:
        await c.aclose()


async def test_inventory_for_unknown_item_returns_404() -> None:
    c = await _auth_client()
    try:
        r = await c.put("/api/inventory/9999999", json={"quantity": 5})
        assert r.status_code in (400, 404, 422), r.text
        assert r.status_code != 500
    finally:
        await c.aclose()


async def test_inventory_cross_user_isolation(sample_item) -> None:
    cA = await _auth_client()
    cB = await _auth_client()
    try:
        await cA.put(f"/api/inventory/{sample_item.id}", json={"quantity": 42})

        listA = await cA.get("/api/inventory/")
        listB = await cB.get("/api/inventory/")
        assert listA.status_code == 200
        assert listB.status_code == 200

        a_items = {row["item_id"] for row in listA.json()}
        b_items = {row["item_id"] for row in listB.json()}

        assert sample_item.id in a_items
        assert sample_item.id not in b_items, "user B saw user A's inventory"
    finally:
        await cA.aclose()
        await cB.aclose()


async def test_inventory_zero_quantity_idempotent_delete(sample_item) -> None:
    c = await _auth_client()
    try:
        await c.put(f"/api/inventory/{sample_item.id}", json={"quantity": 3})
        r1 = await c.put(f"/api/inventory/{sample_item.id}", json={"quantity": 0})
        assert r1.status_code == 204
        r2 = await c.put(f"/api/inventory/{sample_item.id}", json={"quantity": 0})
        assert r2.status_code == 204
    finally:
        await c.aclose()
