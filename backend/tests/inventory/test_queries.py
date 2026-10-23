from httpx import ASGITransport, AsyncClient

from app.inventory.csv_format import INVENTORY_HEADER
from app.main import app
from tests.inventory.test_import import CHESTS, FIXTURE, chest, upload

LEATHER = ("Leather", 16327, 0)
ORE = ("Iron Ore", 8001, 0)
INGOT = ("Copper Ingot", 8320, 1)


def bag(
    character: str,
    t: int,
    size: int,
    items: dict[int, tuple],
    container: str = "bag",
) -> bytes:
    """items: slot -> (name, item_type, grade, count); the other slots are empty."""
    lines = [INVENTORY_HEADER]
    who = character.replace(chr(34), chr(34) * 2)
    for s in range(1, size + 1):
        if s in items:
            name, it, g, n = items[s]
            lines.append(f'{t},{t},"{who}",{container},{s},{name},{it},{g},{n},,')
        else:
            lines.append(f'{t},{t},"{who}",{container},{s},,,,0,,')
    return ("\n".join(lines) + "\n").encode()


async def character(c: AsyncClient, name: str) -> dict:
    r = await c.get("/api/inventory/characters")
    assert r.status_code == 200, r.text
    [found] = [x for x in r.json() if x["character"] == name]
    return found


async def two_snapshots(c: AsyncClient, before: dict, now: dict) -> dict:
    await upload(
        c,
        ("a.csv", bag("Alpha", 100, 20, before)),
        ("b.csv", bag("Alpha", 200, 20, now)),
    )
    grid = (await character(c, "Alpha"))["bag"]
    return {s["slot"]: s for s in grid["slots"]}


async def test_characters_only_own(
    superuser_client: AsyncClient, make_user, login
) -> None:
    await upload(superuser_client, ("inv.csv", FIXTURE.read_bytes()))
    r = await superuser_client.get("/api/inventory/characters")
    assert [c["character"] for c in r.json()] == ["Alpha", "Bravo"]
    alpha = r.json()[0]["bag"]
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


async def test_bag_slots_in_order_with_empty_slots(
    superuser_client: AsyncClient,
) -> None:
    await upload(superuser_client, ("inv.csv", FIXTURE.read_bytes()))
    slots = (await character(superuser_client, "Alpha"))["bag"]["slots"]
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
    body = (await character(superuser_client, "Alpha"))["bag"]
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
    assert (await character(superuser_client, name))["bag"]["slots"][0]["count"] == 5


async def test_requires_login(client: AsyncClient) -> None:
    assert (await client.get("/api/inventory/characters")).status_code == 401
    assert (await client.get("/api/inventory/chests")).status_code == 401


async def test_characters_with_bag_and_bank(superuser_client: AsyncClient) -> None:
    await upload(superuser_client, ("inv.csv", FIXTURE.read_bytes()))
    alpha = await character(superuser_client, "Alpha")
    assert (alpha["bag"]["slot_count"], alpha["bag"]["filled"]) == (90, 56)
    assert (alpha["bank"]["slot_count"], alpha["bank"]["filled"]) == (30, 5)
    assert (await character(superuser_client, "Bravo"))["bank"] is None


async def test_bank_only_character(superuser_client: AsyncClient) -> None:
    await upload(
        superuser_client, ("a.csv", bag("Charlie", 100, 10, {}, container="bank"))
    )
    charlie = await character(superuser_client, "Charlie")
    assert charlie["bag"] is None
    assert charlie["bank"]["slot_count"] == 10


async def test_bag_and_bank_have_separate_history(
    superuser_client: AsyncClient,
) -> None:
    await upload(
        superuser_client,
        ("a.csv", bag("Alpha", 100, 5, {})),
        ("b.csv", bag("Alpha", 200, 5, {})),
        ("c.csv", bag("Alpha", 200, 5, {}, container="bank")),
    )
    alpha = await character(superuser_client, "Alpha")
    assert alpha["bag"]["previous_captured_at"] is not None
    assert alpha["bank"]["previous_captured_at"] is None


async def test_chests_listed_by_number(superuser_client: AsyncClient) -> None:
    await upload(superuser_client, ("chests.csv", CHESTS.read_bytes()))
    chests = (await superuser_client.get("/api/inventory/chests")).json()
    assert [c["chest"] for c in chests] == [1, 2]
    one, two = chests
    assert (one["name"], one["saved_by"], one["slot_count"], one["filled"]) == (
        "Treehouse",
        "Alpha",
        30,
        12,
    )
    assert (two["name"], two["saved_by"]) == (None, "Bravo")


async def test_chest_change_flags(superuser_client: AsyncClient) -> None:
    await upload(superuser_client, ("a.csv", chest(1, 100, character="Alpha")))
    more = chest(1, 200, character="Bravo").replace(
        b"Leather,16327,0,5,", b"Leather,16327,0,55,"
    )
    await upload(superuser_client, ("b.csv", more))
    [one] = (await superuser_client.get("/api/inventory/chests")).json()
    assert one["saved_by"] == "Bravo"
    assert (one["slots"][0]["change"], one["slots"][0]["delta"]) == ("up", 50)


async def test_chests_only_own(superuser_client: AsyncClient, make_user, login) -> None:
    await upload(superuser_client, ("chests.csv", CHESTS.read_bytes()))
    other, pwd = await make_user(superuser=False)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        await login(c, other.email, pwd)
        assert (await c.get("/api/inventory/chests")).json() == []
