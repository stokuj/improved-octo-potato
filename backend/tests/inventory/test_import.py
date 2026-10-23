import uuid
from pathlib import Path

from httpx import ASGITransport, AsyncClient
from sqlmodel import select

from app.inventory.csv_format import CHESTS_HEADER, INVENTORY_HEADER
from app.inventory.models import ChestName, InventorySlot, InventorySnapshot
from app.main import app

FIXTURE = Path(__file__).parent / "fixtures" / "inventory.csv"
CHESTS = Path(__file__).parent / "fixtures" / "chests.csv"


def bag(character: str, t: int, container: str = "bag") -> bytes:
    """The fixture's `container` of `character`, re-stamped as snapshot `t`."""
    lines = FIXTURE.read_text().splitlines()
    rows = [line.split(",", 2) for line in lines[1:]]
    body = [
        f"{t},{t},{rest}"
        for _, _, rest in rows
        if rest.startswith(f"{character},{container},")
    ]
    return ("\n".join([INVENTORY_HEADER, *body]) + "\n").encode()


def chest(n: int, t: int, name: str = "", character: str = "Alpha", size: int = 3):
    """A chest snapshot with Leather x5 in slot 1."""
    body = [
        f"{t},{t},{character},{n},{name},7,1,2,3,{s},"
        + ("Leather,16327,0,5,Material,5" if s == 1 else ",,,0,,")
        for s in range(1, size + 1)
    ]
    return ("\n".join([CHESTS_HEADER, *body]) + "\n").encode()


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


async def stored(
    c: AsyncClient, session, character: str, container: str = "bag"
) -> list[int]:
    user_id = (await c.get("/api/users/me")).json()["id"]
    snaps = await session.exec(
        select(InventorySnapshot)
        .where(InventorySnapshot.user_id == user_id)
        .where(InventorySnapshot.container == container)
        .where(InventorySnapshot.character == character)
        .order_by(InventorySnapshot.snapshot_id)
    )
    return [s.snapshot_id for s in snaps.all()]


async def stored_chest(c: AsyncClient, session, n: int) -> list[int]:
    user_id = (await c.get("/api/users/me")).json()["id"]
    snaps = await session.exec(
        select(InventorySnapshot)
        .where(InventorySnapshot.user_id == user_id)
        .where(InventorySnapshot.container == "chest")
        .where(InventorySnapshot.chest == n)
        .order_by(InventorySnapshot.snapshot_id)
    )
    return [s.snapshot_id for s in snaps.all()]


async def chest_name(c: AsyncClient, session, n: int) -> str | None:
    user_id = (await c.get("/api/users/me")).json()["id"]
    row = await session.get(ChestName, (uuid.UUID(user_id), n))
    return row.name if row else None


async def test_first_upload(superuser_client: AsyncClient, session) -> None:
    [res] = await upload(superuser_client, ("inventory.csv", FIXTURE.read_bytes()))
    assert counts(res) == ("inventory", 270, 270, 0, 0, 0)
    assert len(await stored(superuser_client, session, "Alpha")) == 1
    assert len(await stored(superuser_client, session, "Bravo")) == 1


async def test_reupload_is_noop(superuser_client: AsyncClient) -> None:
    await upload(superuser_client, ("inventory.csv", FIXTURE.read_bytes()))
    [res] = await upload(superuser_client, ("inventory.csv", FIXTURE.read_bytes()))
    assert counts(res) == ("inventory", 270, 0, 0, 270, 0)


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
        assert counts(res) == ("inventory", 270, 270, 0, 0, 0)
        assert len(await stored(c, session, "Alpha")) == 1
    assert len(await stored(superuser_client, session, "Alpha")) == 1


async def test_invariant_with_errors(superuser_client: AsyncClient) -> None:
    broken = "500,500,Alpha,bag,1,,,,0,,\n500,500,Alpha,bag,3,,,,0,,\n"  # gap
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
    assert res["inserted"] == 270


async def test_bag_and_bank_share_snapshot_id(
    superuser_client: AsyncClient, session
) -> None:
    await upload(superuser_client, ("inv.csv", FIXTURE.read_bytes()))
    bag_ids = await stored(superuser_client, session, "Alpha")
    assert bag_ids == await stored(superuser_client, session, "Alpha", "bank")
    assert len(bag_ids) == 1
    [res] = await upload(superuser_client, ("inv.csv", FIXTURE.read_bytes()))
    assert counts(res) == ("inventory", 270, 0, 0, 270, 0)


async def test_bank_keeps_two_on_its_own(
    superuser_client: AsyncClient, session
) -> None:
    for t in (100, 200, 300):
        await upload(superuser_client, (f"{t}.csv", bag("Alpha", t, "bank")))
    await upload(superuser_client, ("b.csv", bag("Alpha", 400)))
    assert await stored(superuser_client, session, "Alpha", "bank") == [200, 300]
    assert await stored(superuser_client, session, "Alpha") == [400]


async def test_chests_first_upload_and_reupload(superuser_client: AsyncClient) -> None:
    [res] = await upload(superuser_client, ("chests.csv", CHESTS.read_bytes()))
    assert counts(res) == ("chests", 80, 80, 0, 0, 0)
    [res] = await upload(superuser_client, ("chests.csv", CHESTS.read_bytes()))
    assert counts(res) == ("chests", 80, 0, 0, 80, 0)
    assert_sum(res)


async def test_chest_keep_two_across_characters(
    superuser_client: AsyncClient, session
) -> None:
    for t, who in ((100, "Alpha"), (200, "Bravo"), (300, "Alpha")):
        await upload(superuser_client, ("c.csv", chest(1, t, character=who)))
    assert await stored_chest(superuser_client, session, 1) == [200, 300]


async def test_chest_name_kept_when_empty(
    superuser_client: AsyncClient, session
) -> None:
    await upload(superuser_client, ("a.csv", chest(1, 100, "Treehouse")))
    await upload(superuser_client, ("b.csv", chest(1, 200)), ("c.csv", chest(1, 300)))
    assert await stored_chest(superuser_client, session, 1) == [200, 300]
    assert await chest_name(superuser_client, session, 1) == "Treehouse"


async def test_chest_renamed_by_newer_save(
    superuser_client: AsyncClient, session
) -> None:
    await upload(superuser_client, ("a.csv", chest(1, 100, "Treehouse")))
    await upload(superuser_client, ("b.csv", chest(1, 200, "Barn")))
    assert await chest_name(superuser_client, session, 1) == "Barn"


async def test_older_chest_name_does_not_win(
    superuser_client: AsyncClient, session
) -> None:
    await upload(superuser_client, ("b.csv", chest(1, 200, "Barn")))
    await upload(superuser_client, ("a.csv", chest(1, 100, "Treehouse")))
    assert await chest_name(superuser_client, session, 1) == "Barn"


async def test_old_header_is_rejected(superuser_client: AsyncClient) -> None:
    old = b"snapshot_id,captured_at,character,slot,item,item_type,item_grade,count\n1,1,Alpha,1,,,,0\n"
    [res] = await upload(superuser_client, ("inventory.csv", old))
    assert res["kind"] is None
    assert res["errors"] == [{"line": 0, "reason": "unknown header"}]
