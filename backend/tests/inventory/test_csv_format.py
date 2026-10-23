from pathlib import Path

import pytest

from app.inventory.csv_format import (
    CHESTS_HEADER,
    INVENTORY_HEADER,
    SlotRow,
    parse_inventory,
)
from app.market.csv_format import CsvFormatError

FIXTURE = Path(__file__).parent / "fixtures" / "inventory.csv"
CHESTS = Path(__file__).parent / "fixtures" / "chests.csv"


def _file(*lines: str, header: str = INVENTORY_HEADER) -> bytes:
    return ("\n".join([header, *lines]) + "\n").encode()


def _bag(
    character: str,
    snapshot: int,
    n: int,
    at: int | None = None,
    container: str = "bag",
) -> list[str]:
    at = snapshot if at is None else at
    return [
        f"{snapshot},{at},{character},{container},{s},,,,0,," for s in range(1, n + 1)
    ]


def _chest(chest: int, snapshot: int, n: int, name: str = "", who: str = "Alpha"):
    return [
        f"{snapshot},{snapshot},{who},{chest},{name},7,1,2,3,{s},,,,0,,"
        for s in range(1, n + 1)
    ]


def test_fixture_bag_and_bank() -> None:
    parsed = parse_inventory(FIXTURE.read_bytes())
    assert parsed.rows == 270 and parsed.errors == []
    by_place = {(s.character, s.container): s for s in parsed.snapshots}
    assert sorted(by_place) == [("Alpha", "bag"), ("Alpha", "bank"), ("Bravo", "bag")]
    assert len(by_place[("Alpha", "bag")].slots) == 90
    assert len(by_place[("Alpha", "bank")].slots) == 30
    assert len(by_place[("Bravo", "bag")].slots) == 150
    assert sum(1 for s in by_place[("Alpha", "bag")].slots if s.item) == 56
    assert (
        by_place[("Alpha", "bank")].snapshot_id
        == by_place[("Alpha", "bag")].snapshot_id
    )
    assert by_place[("Alpha", "bank")].slots[0] == SlotRow(
        1, "Copper Ingot", 8320, 1, 1
    )
    assert by_place[("Alpha", "bag")].lines == 90


def test_fixture_chests() -> None:
    parsed = parse_inventory(CHESTS.read_bytes())
    assert parsed.rows == 80 and parsed.errors == []
    one, two = sorted(parsed.snapshots, key=lambda s: s.chest)
    assert (one.container, one.chest, one.name, one.character, len(one.slots)) == (
        "chest",
        1,
        "Treehouse",
        "Alpha",
        30,
    )
    assert (two.chest, two.name, two.character, len(two.slots)) == (
        2,
        None,
        "Bravo",
        50,
    )
    assert one.slots[11].count == 120


def test_empty_slot_line() -> None:
    [snap] = parse_inventory(
        _file("1,1,Alpha,bag,1,Leather,16327,0,5,Material,3", "1,1,Alpha,bag,2,,,,0,,")
    ).snapshots
    assert snap.slots[0] == SlotRow(1, "Leather", 16327, 0, 5)
    assert snap.slots[1] == SlotRow(2, None, None, None, 0)


def test_quoted_character_name() -> None:
    [snap] = parse_inventory(_file('1,1,"Zażółć, ""Gęś""",bag,1,,,,0,,')).snapshots
    assert snap.character == 'Zażółć, "Gęś"'


@pytest.mark.parametrize(
    "lines",
    [
        [
            "1,1,Alpha,bag,1,,,,0,,",
            "1,1,Alpha,bag,2,,,,0,,",
            "1,1,Alpha,bag,4,,,,0,,",
        ],
        [
            "1,1,Alpha,bag,1,,,,0,,",
            "1,1,Alpha,bag,2,,,,0,,",
            "1,1,Alpha,bag,2,,,,0,,",
        ],
        ["1,1,Alpha,bag,1,,,,0,,", "1,2,Alpha,bag,2,,,,0,,"],
        _bag("Alpha", 1, 301),
    ],
    ids=["gap", "duplicate", "mixed_captured_at", "over_300"],
)
def test_invalid_snapshot_is_rejected(lines: list[str]) -> None:
    parsed = parse_inventory(_file(*lines))
    assert parsed.snapshots == []
    assert len(parsed.errors) == len(lines)
    assert len({e.reason for e in parsed.errors}) == 1


def test_same_second_double_click_keeps_last_run() -> None:
    first = [
        "5,5,Alpha,bag,1,Leather,16327,0,1,,",
        "5,5,Alpha,bag,2,,,,0,,",
        "5,5,Alpha,bag,3,,,,0,,",
    ]
    second = [
        "5,5,Alpha,bag,1,Leather,16327,0,9,,",
        "5,5,Alpha,bag,2,,,,0,,",
        "5,5,Alpha,bag,3,,,,0,,",
    ]
    parsed = parse_inventory(_file(*first, *second))
    [snap] = parsed.snapshots
    assert len(snap.slots) == 3
    assert snap.slots[0].count == 9
    assert snap.lines == 3
    assert parsed.skipped == 3
    assert parsed.errors == []


def test_bag_and_bank_of_one_click_are_separate() -> None:
    parsed = parse_inventory(
        _file(*_bag("Alpha", 1, 3), *_bag("Alpha", 1, 2, container="bank"))
    )
    assert [(s.container, len(s.slots)) for s in parsed.snapshots] == [
        ("bag", 3),
        ("bank", 2),
    ]
    assert parsed.skipped == 0


def test_bad_row_rejects_its_snapshot() -> None:
    parsed = parse_inventory(
        _file(
            "1,1,Alpha,bag,1,Leather,16327,0,lots,,",
            "1,1,Alpha,bag,2,,,,0,,",
            *_bag("Bravo", 1, 2),
        )
    )
    assert [s.character for s in parsed.snapshots] == ["Bravo"]
    assert [e.line for e in parsed.errors] == [2, 3]
    assert "count is not an integer" in parsed.errors[0].reason


def test_bad_container_rejects_snapshot() -> None:
    parsed = parse_inventory(_file(*_bag("Alpha", 1, 2, container="mail")))
    assert parsed.snapshots == []
    assert parsed.errors[0].reason == "container must be bag or bank"


@pytest.mark.parametrize("chest", [0, 11])
def test_chest_number_out_of_range(chest: int) -> None:
    parsed = parse_inventory(_file(*_chest(chest, 1, 2), header=CHESTS_HEADER))
    assert parsed.snapshots == []
    assert parsed.errors[0].reason == "chest must be 1..10"


def test_chest_name_too_long() -> None:
    parsed = parse_inventory(
        _file(*_chest(1, 1, 2, name="x" * 16), header=CHESTS_HEADER)
    )
    assert parsed.snapshots == []
    assert parsed.errors[0].reason == "name longer than 15 characters"


def test_wrong_column_count() -> None:
    inv = parse_inventory(_file("1,1,Alpha,bag,1,,,,0,"))
    assert inv.errors[0].reason == "expected 11 columns, got 10"
    chests = parse_inventory(
        _file("1,1,Alpha,1,,7,1,2,3,1,,,,0,", header=CHESTS_HEADER)
    )
    assert chests.errors[0].reason == "expected 16 columns, got 15"


def test_chest_double_click_keeps_last_run() -> None:
    parsed = parse_inventory(
        _file(*_chest(1, 5, 3), *_chest(1, 5, 3, name="Barn"), header=CHESTS_HEADER)
    )
    [snap] = parsed.snapshots
    assert snap.name == "Barn"
    assert parsed.skipped == 3


def test_two_chests_same_second_are_separate() -> None:
    parsed = parse_inventory(
        _file(*_chest(1, 5, 3), *_chest(2, 5, 4), header=CHESTS_HEADER)
    )
    assert [(s.chest, len(s.slots)) for s in parsed.snapshots] == [(1, 3), (2, 4)]


def test_bom_and_crlf() -> None:
    data = ("﻿" + INVENTORY_HEADER + "\r\n1,1,Alpha,bag,1,,,,0,,\r\n").encode()
    [snap] = parse_inventory(data).snapshots
    assert snap.character == "Alpha"


@pytest.mark.parametrize(
    "header",
    ["snapshot_id,captured_at,character,slot,item,item_type,item_grade,count", "a,b"],
    ids=["old_8_column", "garbage"],
)
def test_unknown_header(header: str) -> None:
    with pytest.raises(CsvFormatError, match="unknown header"):
        parse_inventory(f"{header}\n1,2\n".encode())
