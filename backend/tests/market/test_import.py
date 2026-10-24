import csv
import io
import random
import uuid
from collections.abc import Callable
from datetime import date
from pathlib import Path

from httpx import AsyncClient
from sqlmodel import col, select

from app.market import services
from app.market.csv_format import (
    LISTINGS_HEADER,
    LISTINGS_HEADER_V2,
    MARKET_HEADER,
    MARKET_HEADER_V2,
)
from app.market.models import Item, MarketDay

FIXTURES = Path(__file__).parent / "fixtures"


def _base() -> int:
    # Unique item_type offset per test; fixture types are < 100_000.
    return random.randint(1, 20_000) * 100_000


def rewrite_fixture(name: str, suffix: str, base: int) -> bytes:
    """Fixture with every item renamed to '<name> <suffix>' and item_type shifted by base."""
    rows = list(csv.reader(io.StringIO((FIXTURES / name).read_text())))
    header, body = rows[0], rows[1:]
    i_item = header.index("item")
    i_type = header.index("item_type") if "item_type" in header else None
    for r in body:
        r[i_item] = f"{r[i_item]} {suffix}"
        if i_type is not None and r[i_type]:
            r[i_type] = str(base + int(r[i_type]))
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows([header, *body])
    return out.getvalue().encode()


def to_v2(data: bytes, extra: Callable[[dict], list[str]]) -> bytes:
    """Append V2 columns: extra(row_as_dict) returns the new cell values."""
    rows = list(csv.reader(io.StringIO(data.decode())))
    header = ",".join(rows[0])
    v2 = {LISTINGS_HEADER: LISTINGS_HEADER_V2, MARKET_HEADER: MARKET_HEADER_V2}[header]
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(v2.split(","))
    w.writerows(r + extra(dict(zip(rows[0], r))) for r in rows[1:])
    return out.getvalue().encode()


def split_by_scan(data: bytes) -> list[bytes]:
    lines = data.decode().splitlines()
    scans: dict[str, list[str]] = {}
    for line in lines[1:]:
        scans.setdefault(line.split(",")[0], []).append(line)
    return [("\n".join([lines[0], *ls]) + "\n").encode() for ls in scans.values()]


async def upload(c: AsyncClient, *files: tuple[str, bytes]) -> list[dict]:
    r = await c.post(
        "/api/import",
        files=[("files", (n, d, "text/csv")) for n, d in files],
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


async def test_sample_first_and_second_upload(superuser_client: AsyncClient) -> None:
    s, base = uuid.uuid4().hex[:8], _base()
    m = rewrite_fixture("market.csv", s, base)
    li = rewrite_fixture("listings.csv", s, base)
    first = await upload(superuser_client, ("market.csv", m), ("listings.csv", li))
    assert counts(first[0]) == ("market", 406, 140, 0, 266, 0)
    assert counts(first[1]) == ("listings", 250, 250, 0, 0, 0)
    second = await upload(superuser_client, ("market.csv", m), ("listings.csv", li))
    assert counts(second[0]) == ("market", 406, 0, 0, 406, 0)
    assert counts(second[1]) == ("listings", 250, 0, 0, 250, 0)


async def test_listings_before_market_fills_item_type(
    superuser_client: AsyncClient, session
) -> None:
    s, base = uuid.uuid4().hex[:8], _base()
    await upload(superuser_client, ("l.csv", rewrite_fixture("listings.csv", s, base)))
    res = await upload(
        superuser_client, ("m.csv", rewrite_fixture("market.csv", s, base))
    )
    assert counts(res[0]) == ("market", 406, 140, 0, 266, 0)
    items = (
        await session.exec(select(Item).where(col(Item.name).endswith(f" {s}")))
    ).all()
    by_name = {i.name: i for i in items}
    assert len(items) == 11  # 10 market items + "Nonexistent Item"
    assert by_name[f"Leather {s}"].item_type == base + 16327
    assert by_name[f"Nonexistent Item {s}"].item_type is None


def two_dates(s: str, base: int) -> bytes:
    return rewrite_fixture("market_two_dates.csv", s, base)


async def _values(session, name: str) -> dict[date, int]:
    item = (await session.exec(select(Item).where(Item.name == name))).one()
    days = (
        await session.exec(select(MarketDay).where(MarketDay.item_id == item.id))
    ).all()
    return {d.day: d.daily_avg for d in days}


async def test_two_dates_dedup_in_one_file(
    superuser_client: AsyncClient, session
) -> None:
    s, base = uuid.uuid4().hex[:8], _base()
    res = await upload(superuser_client, ("m.csv", two_dates(s, base)))
    assert counts(res[0]) == ("market", 28, 15, 0, 13, 0)
    values = await _values(session, f"Two Dates {s}")
    assert values[date(2026, 10, 7)] == 100
    assert all(values[date(2026, 10, d)] == 200 for d in range(8, 22))


async def test_newer_scan_updates_older_does_not(
    superuser_client: AsyncClient, session
) -> None:
    s, base = uuid.uuid4().hex[:8], _base()
    scan_a, scan_b = split_by_scan(two_dates(s, base))
    assert counts((await upload(superuser_client, ("a.csv", scan_a)))[0])[2] == 14
    res_b = await upload(superuser_client, ("b.csv", scan_b))
    assert counts(res_b[0]) == ("market", 14, 1, 13, 0, 0)
    res_a = await upload(superuser_client, ("a.csv", scan_a))
    assert counts(res_a[0]) == ("market", 14, 0, 0, 14, 0)
    assert (await _values(session, f"Two Dates {s}"))[date(2026, 10, 10)] == 200


async def test_same_kind_twice_in_one_request(superuser_client: AsyncClient) -> None:
    s, base = uuid.uuid4().hex[:8], _base()
    data = two_dates(s, base)
    res = await upload(superuser_client, ("1.csv", data), ("2.csv", data))
    assert counts(res[0]) == ("market", 28, 15, 0, 13, 0)
    assert counts(res[1]) == ("market", 28, 0, 0, 28, 0)


async def test_name_used_by_another_grade_is_row_error(
    superuser_client: AsyncClient,
) -> None:
    name, t = f"Graded {uuid.uuid4().hex[:8]}", _base()

    def file(grade: int) -> bytes:
        row = f"1792607894,1792607894,{name},{t},{grade},ok,14,1,1,1,1,1"
        return f"{MARKET_HEADER}\n{row}\n".encode()

    await upload(superuser_client, ("g0.csv", file(0)))
    res = (await upload(superuser_client, ("g1.csv", file(1))))[0]
    assert counts(res) == ("market", 1, 0, 0, 0, 1)
    assert res["errors"] == [
        {"line": 2, "reason": "name already used by another grade"}
    ]


async def test_junk_files_do_not_block_others(superuser_client: AsyncClient) -> None:
    s, base = uuid.uuid4().hex[:8], _base()
    res = await upload(
        superuser_client,
        ("empty.csv", b""),
        ("bin.csv", b"\xff\xfe\x00"),
        ("header.csv", (MARKET_HEADER + "\n").encode()),
        ("unknown.csv", b"a,b\n1,2\n"),
        ("listings.csv", rewrite_fixture("listings.csv", s, base)),
    )
    reasons = [r["errors"][0]["reason"] if r["errors"] else None for r in res]
    assert reasons == ["empty file", "not UTF-8", None, "unknown header", None]
    assert [r["kind"] for r in res] == [None, None, "market", None, "listings"]
    assert counts(res[4]) == ("listings", 250, 250, 0, 0, 0)
    for r in res:
        assert_sum(r)


async def test_large_file_is_chunked(superuser_client: AsyncClient) -> None:
    s, base = uuid.uuid4().hex[:8], _base()
    rows = [
        f"1792607894,1792607894,Bulk {s} {i},{base + i},0,ok,{d},1,1,1,1,1"
        for i in range(400)
        for d in range(1, 15)
    ]
    data = ("\n".join([MARKET_HEADER, *rows]) + "\n").encode()
    res = (await upload(superuser_client, ("big.csv", data)))[0]
    assert counts(res) == ("market", 5600, 5600, 0, 0, 0)


async def test_error_list_is_capped(superuser_client: AsyncClient) -> None:
    rows = ["1,1,X,weird,0,,," for _ in range(150)]
    data = ("\n".join([LISTINGS_HEADER, *rows]) + "\n").encode()
    res = (await upload(superuser_client, ("bad.csv", data)))[0]
    assert (res["error_count"], len(res["errors"])) == (150, 100)
    assert_sum(res)


async def test_file_over_cap(superuser_client: AsyncClient, monkeypatch) -> None:
    monkeypatch.setattr(services, "MAX_FILE_BYTES", 100)
    res = (
        await upload(
            superuser_client,
            ("l.csv", (FIXTURES / "listings.csv").read_bytes()),
        )
    )[0]
    assert res["kind"] is None
    assert res["errors"] == [{"line": 0, "reason": "file larger than 50 MB"}]
    assert_sum(res)


async def test_import_requires_signed_in_user(client: AsyncClient) -> None:
    files = [("files", ("l.csv", b"", "text/csv"))]
    assert (await client.post("/api/import", files=files)).status_code == 401


def _market_rows(name: str, item_type: int, captured_at: int, value: int) -> list[str]:
    return [
        f"{captured_at},{captured_at},{name},{item_type},0,ok,{d},{value},{value},{value},{value},{value}"
        for d in range(1, 15)
    ]


async def test_rename_inside_one_file(superuser_client: AsyncClient, session) -> None:
    s, t = uuid.uuid4().hex[:8], _base()
    rows = _market_rows(f"Old {s}", t, 1792500000, 1) + _market_rows(
        f"New {s}", t, 1792600000, 2
    )
    data = ("\n".join([MARKET_HEADER, *rows]) + "\n").encode()
    res = (await upload(superuser_client, ("m.csv", data)))[0]
    assert counts(res)[0] == "market" and res["error_count"] == 0
    assert_sum(res)
    item = (await session.exec(select(Item).where(Item.item_type == t))).one()
    assert item.name == f"New {s}"


async def test_rename_across_uploads(superuser_client: AsyncClient, session) -> None:
    s, t = uuid.uuid4().hex[:8], _base()
    for name, ts in ((f"Old {s}", 1792500000), (f"New {s}", 1792600000)):
        data = (
            "\n".join([MARKET_HEADER, *_market_rows(name, t, ts, 1)]) + "\n"
        ).encode()
        res = (await upload(superuser_client, ("m.csv", data)))[0]
        assert res["error_count"] == 0
    items = (await session.exec(select(Item).where(Item.item_type == t))).all()
    assert [i.name for i in items] == [f"New {s}"]


async def test_db_error_in_one_file_does_not_block_the_next(
    superuser_client: AsyncClient,
) -> None:
    s, base = uuid.uuid4().hex[:8], _base()
    overflow = f"1,1,Huge {s},{base},0,ok,14,{10**20},1,1,1,1"
    bad = f"{MARKET_HEADER}\n{overflow}\n".encode()
    res = await upload(
        superuser_client,
        ("bad.csv", bad),
        ("listings.csv", rewrite_fixture("listings.csv", s, base)),
    )
    assert res[0]["errors"][0]["reason"].startswith("database error")
    assert_sum(res[0])
    assert counts(res[1]) == ("listings", 250, 250, 0, 0, 0)


async def _category(session, name: str) -> str | None:
    return (await session.exec(select(Item.category).where(Item.name == name))).one()


async def test_v2_market_sets_category(superuser_client: AsyncClient, session) -> None:
    s, base = uuid.uuid4().hex[:8], _base()
    data = to_v2(rewrite_fixture("market.csv", s, base), lambda r: ["Hide"])
    [r] = await upload(superuser_client, ("market.csv", data))
    assert_sum(r)
    assert counts(r) == ("market", 406, 140, 0, 266, 0)
    assert await _category(session, f"Leather {s}") == "Hide"


async def test_v2_market_empty_category_keeps_stored(
    superuser_client: AsyncClient, session
) -> None:
    s, base = uuid.uuid4().hex[:8], _base()
    m = rewrite_fixture("market.csv", s, base)
    await upload(superuser_client, ("a.csv", to_v2(m, lambda r: ["Hide"])))
    [r] = await upload(superuser_client, ("b.csv", to_v2(m, lambda r: [""])))
    assert_sum(r)
    assert await _category(session, f"Leather {s}") == "Hide"


def _v2_offers(name: str, t: int, grades: list[int]) -> bytes:
    rows = [
        f"1792607894,1792607894,{name},ok,{rank},100,1000,10,{t},{g}"
        for rank, g in enumerate(grades, 1)
    ]
    return ("\n".join([LISTINGS_HEADER_V2, *rows]) + "\n").encode()


async def test_v2_listings_resolve_by_type_and_grade(
    superuser_client: AsyncClient, session
) -> None:
    name, t = f"Keyed {uuid.uuid4().hex[:8]}", _base() + 16327
    [r] = await upload(superuser_client, ("l.csv", _v2_offers(name, t, [0, 0])))
    assert counts(r) == ("listings", 2, 2, 0, 0, 0)
    item = (await session.exec(select(Item).where(Item.name == name))).one()
    assert (item.item_type, item.item_grade) == (t, 0)


async def test_v2_listings_two_grades_of_one_name(
    superuser_client: AsyncClient,
) -> None:
    name, t = f"Graded {uuid.uuid4().hex[:8]}", _base()
    [r] = await upload(superuser_client, ("l.csv", _v2_offers(name, t, [0, 0, 2])))
    assert_sum(r)
    assert [e["reason"] for e in r["errors"]] == [services.GRADE_CONFLICT]
    assert r["inserted"] == 2


async def test_v1_listings_after_v2_market_match_by_name(
    superuser_client: AsyncClient,
) -> None:
    s, base = uuid.uuid4().hex[:8], _base()
    m = to_v2(rewrite_fixture("market.csv", s, base), lambda r: ["Hide"])
    li = rewrite_fixture("listings.csv", s, base)
    res = await upload(superuser_client, ("market.csv", m), ("listings.csv", li))
    assert counts(res[0]) == ("market", 406, 140, 0, 266, 0)
    assert counts(res[1]) == ("listings", 250, 250, 0, 0, 0)


async def test_v2_listings_keep_the_stored_grade_when_rank_1_differs(
    superuser_client: AsyncClient,
) -> None:
    name, t = f"Flip {uuid.uuid4().hex[:8]}", _base()
    await upload(superuser_client, ("a.csv", _v2_offers(name, t, [0, 0])))
    later = _v2_offers(name, t, [2, 0, 0]).replace(b"1792607894", b"1792607954")
    [r] = await upload(superuser_client, ("b.csv", later))
    assert_sum(r)
    assert (r["inserted"], [e["line"] for e in r["errors"]]) == (2, [2])
    assert r["errors"][0]["reason"] == services.GRADE_CONFLICT


async def test_market_keeps_the_stored_grade_when_the_first_scan_differs(
    superuser_client: AsyncClient,
) -> None:
    name, t = f"Flip {uuid.uuid4().hex[:8]}", _base()

    def row(scan: int, grade: int) -> str:
        return f"{scan},{scan},{name},{t},{grade},ok,14,1,1,1,1,1"

    await upload(
        superuser_client, ("a.csv", f"{MARKET_HEADER}\n{row(1792607894, 0)}\n".encode())
    )
    data = f"{MARKET_HEADER}\n{row(1792694294, 2)}\n{row(1792780694, 0)}\n".encode()
    [r] = await upload(superuser_client, ("b.csv", data))
    assert_sum(r)
    assert (r["inserted"], [e["line"] for e in r["errors"]]) == (1, [2])
