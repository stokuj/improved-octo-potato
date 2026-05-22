# backend/tests/test_admin_users.py
import uuid

import pytest
from httpx import AsyncClient

from app.users.models import User


def _email() -> str:
    return f"adm-{uuid.uuid4().hex[:8]}@test.com"


@pytest.fixture()
async def regular_user_id(client: AsyncClient) -> str:
    """Register a regular user via API, return the new user's id."""
    email = _email()
    r = await client.post(
        "/api/auth/register", json={"email": email, "password": "pwd123456"}
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


async def test_get_user_by_id_as_superuser(
    superuser_client: AsyncClient, regular_user_id: str
) -> None:
    r = await superuser_client.get(f"/api/users/{regular_user_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == regular_user_id
    assert "email" in body


async def test_get_user_by_id_as_regular_user_forbidden(
    client: AsyncClient, regular_user_id: str
) -> None:
    email = _email()
    await client.post("/api/auth/register", json={"email": email, "password": "pwd123456"})
    await client.post(
        "/api/auth/login", data={"username": email, "password": "pwd123456"}
    )

    r = await client.get(f"/api/users/{regular_user_id}")
    assert r.status_code == 403


async def test_get_user_by_id_unauthenticated(
    client: AsyncClient, regular_user_id: str
) -> None:
    r = await client.get(f"/api/users/{regular_user_id}")
    assert r.status_code == 401


async def test_patch_user_as_superuser_can_promote(
    superuser_client: AsyncClient, regular_user_id: str, session
) -> None:
    r = await superuser_client.patch(
        f"/api/users/{regular_user_id}", json={"is_superuser": True}
    )
    assert r.status_code == 200, r.text

    from sqlmodel import select
    from app.users.models import User as UserModel

    result = await session.exec(select(UserModel).where(UserModel.id == regular_user_id))
    user = result.one()
    assert user.is_superuser is True


async def test_patch_user_self_cannot_promote(client: AsyncClient, session) -> None:
    email = _email()
    reg = await client.post(
        "/api/auth/register", json={"email": email, "password": "pwd123456"}
    )
    uid = reg.json()["id"]
    await client.post(
        "/api/auth/login", data={"username": email, "password": "pwd123456"}
    )

    r = await client.patch("/api/users/me", json={"is_superuser": True})

    from sqlmodel import select
    from app.users.models import User as UserModel

    result = await session.exec(select(UserModel).where(UserModel.id == uid))
    user = result.one()
    assert user.is_superuser is False, "self-promotion must not succeed"
    assert r.status_code in (200, 403, 422)


async def test_delete_user_as_superuser(
    superuser_client: AsyncClient, regular_user_id: str
) -> None:
    r = await superuser_client.delete(f"/api/users/{regular_user_id}")
    assert r.status_code in (200, 204)

    r2 = await superuser_client.get(f"/api/users/{regular_user_id}")
    assert r2.status_code == 404


async def test_admin_panel_redirects_unauth_to_login(client: AsyncClient) -> None:
    r = await client.get("/admin/", follow_redirects=False)
    assert r.status_code in (302, 303, 401)
    if r.status_code in (302, 303):
        assert "/admin" in r.headers.get("location", "")
