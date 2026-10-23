from urllib.parse import quote

from httpx import ASGITransport, AsyncClient

from app.inventory.csv_format import INVENTORY_HEADER
from app.main import app
from tests.inventory.test_import import FIXTURE, upload

LEATHER = ("Leather", 16327, 0)
ORE = ("Iron Ore", 8001, 0)
INGOT = ("Copper Ingot", 8320, 1)


def bag(character: str, t: int, size: int, items: dict[int, tuple]) -> bytes:
    """items: slot -> (name, item_type, grade, count); the other slots are empty."""
    lines = [INVENTORY_HEADER]
    for s in range(1, size + 1):
        if s in items:
            name, it, g, n = items[s]
            lines.append(
                f'{t},{t},"{character.replace(chr(34), chr(34) * 2)}",{s},{name},{it},{g},{n}'
            )
        else:
            lines.append(
                f'{t},{t},"{character.replace(chr(34), chr(34) * 2)}",{s},,,,0'
            )
    return ("\n".join(lines) + "\n").encode()


async def two_snapshots(c: AsyncClient, before: dict, now: dict) -> dict:
    await upload(
        c,
        ("a.csv", bag("Alpha", 100, 20, before)),
        ("b.csv", bag("Alpha", 200, 20, now)),
    )
    r = await c.get("/api/inventory/characters/Alpha")
    assert r.status_code == 200, r.text
    return {s["slot"]: s for s in r.json()["slots"]}


async def test_characters_only_own(
    superuser_client: AsyncClient, make_user, login
) -> None:
    await upload(superuser_client, ("inv.csv", FIXTURE.read_bytes()))
    r = await superuser_client.get("/api/inventory/characters")
    assert [c["character"] for c in r.json()] == ["Alpha", "Bravo"]
    alpha = r.json()[0]
    assert (alpha["slot_count"], alpha["filled"], alpha["previous_captured_at"]) == (
        90,
        56,
        None,
    )

    other, pwd = await make_user(superuser=False)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        await login(c, other.email, pwd)
        assert (await c.get("/api/inventory/characters")).json() == []
        assert (await c.get("/api/inventory/characters/Alpha")).status_code == 404


async def test_bag_slots_in_order_with_empty_slots(
    superuser_client: AsyncClient,
) -> None:
    await upload(superuser_client, ("inv.csv", FIXTURE.read_bytes()))
    body = (await superuser_client.get("/api/inventory/characters/Alpha")).json()
    slots = body["slots"]
    assert len(slots) == 90
    assert [s["slot"] for s in slots] == list(range(1, 91))
    empty = [s for s in slots if s["item"] is None]
    assert len(empty) == 34
    assert all(s["count"] == 0 and s["change"] is None for s in empty)


async def test_moved_stack_is_no_change(superuser_client: AsyncClient) -> None:
    slots = await two_snapshots(
        superuser_client,
        {4: (*LEATHER, 100), 7: (*ORE, 5)},
        {12: (*LEATHER, 100), 7: (*ORE, 5)},
    )
    assert (slots[12]["change"], slots[12]["delta"]) == (None, 0)
    assert slots[4]["item"] is None


async def test_up(superuser_client: AsyncClient) -> None:
    slots = await two_snapshots(
        superuser_client, {4: (*LEATHER, 100)}, {4: (*LEATHER, 150)}
    )
    assert (slots[4]["change"], slots[4]["delta"]) == ("up", 50)


async def test_down(superuser_client: AsyncClient) -> None:
    slots = await two_snapshots(
        superuser_client, {4: (*LEATHER, 100)}, {4: (*LEATHER, 40)}
    )
    assert (slots[4]["change"], slots[4]["delta"]) == ("down", -60)


async def test_new(superuser_client: AsyncClient) -> None:
    slots = await two_snapshots(
        superuser_client, {4: (*LEATHER, 100)}, {4: (*LEATHER, 100), 9: (*INGOT, 3)}
    )
    assert (slots[9]["change"], slots[9]["delta"]) == ("new", 3)


async def test_split_stack_sums_per_item(superuser_client: AsyncClient) -> None:
    slots = await two_snapshots(
        superuser_client, {4: (*LEATHER, 100)}, {4: (*LEATHER, 60), 5: (*LEATHER, 60)}
    )
    assert (slots[4]["change"], slots[4]["delta"]) == ("up", 20)
    assert (slots[5]["change"], slots[5]["delta"]) == ("up", 20)


async def test_no_previous_snapshot(superuser_client: AsyncClient) -> None:
    await upload(
        superuser_client, ("a.csv", bag("Alpha", 100, 20, {4: (*LEATHER, 100)}))
    )
    body = (await superuser_client.get("/api/inventory/characters/Alpha")).json()
    assert body["previous_captured_at"] is None
    assert all(s["change"] is None and s["delta"] is None for s in body["slots"])


async def test_empty_bag_snapshot(superuser_client: AsyncClient) -> None:
    slots = await two_snapshots(superuser_client, {4: (*LEATHER, 100)}, {})
    assert all(s["item"] is None and s["change"] is None for s in slots.values())


async def test_character_name_with_comma_and_unicode(
    superuser_client: AsyncClient,
) -> None:
    name = 'Zażółć, "Gęś"'
    await upload(superuser_client, ("a.csv", bag(name, 100, 10, {1: (*LEATHER, 5)})))
    listed = (await superuser_client.get("/api/inventory/characters")).json()
    assert [c["character"] for c in listed] == [name]
    r = await superuser_client.get(f"/api/inventory/characters/{quote(name, safe='')}")
    assert r.status_code == 200
    assert r.json()["slots"][0]["count"] == 5


async def test_requires_login(client: AsyncClient) -> None:
    assert (await client.get("/api/inventory/characters")).status_code == 401
    assert (await client.get("/api/inventory/characters/Alpha")).status_code == 401
