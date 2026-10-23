from pathlib import Path

from httpx import ASGITransport, AsyncClient
from sqlmodel import select

from app.inventory.csv_format import INVENTORY_HEADER
from app.inventory.models import InventorySlot, InventorySnapshot
from app.main import app

FIXTURE = Path(__file__).parent / "fixtures" / "inventory.csv"


def bag(character: str, t: int) -> bytes:
    """The fixture's bag for `character`, re-stamped as snapshot `t`."""
    lines = FIXTURE.read_text().splitlines()
    rows = [line.split(",", 2) for line in lines[1:]]
    body = [
        f"{t},{t},{rest}" for _, _, rest in rows if rest.startswith(character + ",")
    ]
    return ("\n".join([INVENTORY_HEADER, *body]) + "\n").encode()


async def upload(c: AsyncClient, *files: tuple[str, bytes]) -> list[dict]:
    r = await c.post(
        "/api/import", files=[("files", (n, d, "text/csv")) for n, d in files]
    )
    assert r.status_code == 200, r.text
    return r.json()


def counts(r: dict) -> tuple:
    return (
        r["kind"],
        r["rows"],
        r["inserted"],
        r["updated"],
        r["skipped"],
        r["error_count"],
    )


def assert_sum(r: dict) -> None:
    assert r["inserted"] + r["updated"] + r["skipped"] + r["error_count"] == r["rows"]


async def stored(c: AsyncClient, session, character: str) -> list[int]:
    user_id = (await c.get("/api/users/me")).json()["id"]
    snaps = await session.exec(
        select(InventorySnapshot)
        .where(InventorySnapshot.user_id == user_id)
        .where(InventorySnapshot.character == character)
        .order_by(InventorySnapshot.snapshot_id)
    )
    return [s.snapshot_id for s in snaps.all()]


async def test_first_upload(superuser_client: AsyncClient, session) -> None:
    [res] = await upload(superuser_client, ("inventory.csv", FIXTURE.read_bytes()))
    assert counts(res) == ("inventory", 240, 240, 0, 0, 0)
    assert len(await stored(superuser_client, session, "Alpha")) == 1
    assert len(await stored(superuser_client, session, "Bravo")) == 1


async def test_reupload_is_noop(superuser_client: AsyncClient) -> None:
    await upload(superuser_client, ("inventory.csv", FIXTURE.read_bytes()))
    [res] = await upload(superuser_client, ("inventory.csv", FIXTURE.read_bytes()))
    assert counts(res) == ("inventory", 240, 0, 0, 240, 0)


async def test_third_snapshot_evicts_oldest(
    superuser_client: AsyncClient, session
) -> None:
    for t in (100, 200, 300):
        await upload(superuser_client, (f"{t}.csv", bag("Alpha", t)))
    assert await stored(superuser_client, session, "Alpha") == [200, 300]
    orphans = await session.exec(
        select(InventorySlot).where(
            InventorySlot.snapshot.not_in(select(InventorySnapshot.id))  # type: ignore[attr-defined]
        )
    )
    assert orphans.all() == []


async def test_older_file_after_newer_is_noop(
    superuser_client: AsyncClient, session
) -> None:
    await upload(
        superuser_client, ("a.csv", bag("Alpha", 200)), ("b.csv", bag("Alpha", 300))
    )
    [res] = await upload(superuser_client, ("old.csv", bag("Alpha", 100)))
    assert counts(res) == ("inventory", 90, 0, 0, 90, 0)
    assert await stored(superuser_client, session, "Alpha") == [200, 300]


async def test_same_snapshot_in_two_files_of_one_upload(
    superuser_client: AsyncClient,
) -> None:
    first, second = await upload(
        superuser_client, ("1.csv", bag("Alpha", 100)), ("2.csv", bag("Alpha", 100))
    )
    assert counts(first) == ("inventory", 90, 90, 0, 0, 0)
    assert counts(second) == ("inventory", 90, 0, 0, 90, 0)


async def test_users_are_separate(
    superuser_client: AsyncClient, make_user, login, session
) -> None:
    await upload(superuser_client, ("inv.csv", FIXTURE.read_bytes()))
    other, pwd = await make_user(superuser=False)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        await login(c, other.email, pwd)
        [res] = await upload(c, ("inv.csv", FIXTURE.read_bytes()))
        assert counts(res) == ("inventory", 240, 240, 0, 0, 0)
        assert len(await stored(c, session, "Alpha")) == 1
    assert len(await stored(superuser_client, session, "Alpha")) == 1


async def test_invariant_with_errors(superuser_client: AsyncClient) -> None:
    broken = "500,500,Alpha,1,,,,0\n500,500,Alpha,3,,,,0\n"  # gap: rejected
    data = bag("Bravo", 500) + broken.encode()
    [res] = await upload(superuser_client, ("mixed.csv", data))
    assert counts(res) == ("inventory", 152, 150, 0, 0, 2)
    assert_sum(res)


async def test_non_superuser_can_import_inventory(make_user, login) -> None:
    user, pwd = await make_user(superuser=False)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        await login(c, user.email, pwd)
        [res] = await upload(c, ("inv.csv", FIXTURE.read_bytes()))
    assert res["inserted"] == 240
