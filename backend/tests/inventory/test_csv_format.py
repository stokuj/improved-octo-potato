from pathlib import Path

import pytest

from app.inventory.csv_format import (
    INVENTORY_HEADER,
    INVENTORY_HEADER_ICON,
    SlotRow,
    normalize_icon,
    parse_inventory,
)
from app.market.csv_format import CsvFormatError

FIXTURE = Path(__file__).parent / "fixtures" / "inventory.csv"


def _file(*lines: str, header: str = INVENTORY_HEADER) -> bytes:
    return ("\n".join([header, *lines]) + "\n").encode()


def _bag(character: str, snapshot: int, n: int, at: int | None = None) -> list[str]:
    at = snapshot if at is None else at
    return [f"{snapshot},{at},{character},{s},,,,0" for s in range(1, n + 1)]


def test_fixture_two_characters() -> None:
    parsed = parse_inventory(FIXTURE.read_bytes())
    assert parsed.rows == 240
    assert parsed.errors == []
    by_name = {s.character: s for s in parsed.snapshots}
    assert sorted(by_name) == ["Alpha", "Bravo"]
    assert len(by_name["Alpha"].slots) == 90
    assert len(by_name["Bravo"].slots) == 150
    assert sum(1 for s in by_name["Alpha"].slots if s.item) == 56
    assert sum(1 for s in by_name["Bravo"].slots if s.item) == 112
    assert by_name["Alpha"].lines == 90


def test_header_with_icon() -> None:
    data = _file(
        "7,7,Alpha,1,Leather,16327,0,412,Game/ui/icon/icon_item_0352.dds",
        "7,7,Alpha,2,,,,0,",
        header=INVENTORY_HEADER_ICON,
    )
    [snap] = parse_inventory(data).snapshots
    assert snap.slots[0].icon == "icon_item_0352"
    assert snap.slots[1].icon is None


def test_normalize_icon() -> None:
    assert normalize_icon("Game/ui/icon/ICON_Item_0352.dds") == "icon_item_0352"
    assert normalize_icon("") is None
    # Base name only, so no path part ever reaches the icon cache.
    assert normalize_icon("../etc/passwd") == "passwd"
    assert normalize_icon("Game/ui/icon/bad name!.dds") is None


def test_empty_slot_line() -> None:
    [snap] = parse_inventory(
        _file("1,1,Alpha,1,Leather,16327,0,5", "1,1,Alpha,2,,,,0")
    ).snapshots
    assert snap.slots[1] == SlotRow(2, None, None, None, 0, None)


def test_quoted_character_name() -> None:
    [snap] = parse_inventory(_file('1,1,"Zażółć, ""Gęś""",1,,,,0')).snapshots
    assert snap.character == 'Zażółć, "Gęś"'


@pytest.mark.parametrize(
    "lines",
    [
        ["1,1,Alpha,1,,,,0", "1,1,Alpha,2,,,,0", "1,1,Alpha,4,,,,0"],  # gap
        ["1,1,Alpha,1,,,,0", "1,1,Alpha,2,,,,0", "1,1,Alpha,2,,,,0"],  # duplicate
        ["1,1,Alpha,1,,,,0", "1,2,Alpha,2,,,,0"],  # mixed captured_at
        _bag("Alpha", 1, 301),  # more than 300 slots
    ],
    ids=["gap", "duplicate", "mixed_captured_at", "over_300"],
)
def test_invalid_snapshot_is_rejected(lines: list[str]) -> None:
    parsed = parse_inventory(_file(*lines))
    assert parsed.snapshots == []
    assert len(parsed.errors) == len(lines)
    assert len({e.reason for e in parsed.errors}) == 1


def test_same_second_double_click_keeps_last_run() -> None:
    first = ["5,5,Alpha,1,Leather,16327,0,1", "5,5,Alpha,2,,,,0", "5,5,Alpha,3,,,,0"]
    second = ["5,5,Alpha,1,Leather,16327,0,9", "5,5,Alpha,2,,,,0", "5,5,Alpha,3,,,,0"]
    parsed = parse_inventory(_file(*first, *second))
    [snap] = parsed.snapshots
    assert len(snap.slots) == 3
    assert snap.slots[0].count == 9
    assert snap.lines == 3
    assert parsed.skipped == 3
    assert parsed.errors == []


def test_bad_row_rejects_its_snapshot() -> None:
    parsed = parse_inventory(
        _file(
            "1,1,Alpha,1,Leather,16327,0,lots", "1,1,Alpha,2,,,,0", *_bag("Bravo", 1, 2)
        )
    )
    assert [s.character for s in parsed.snapshots] == ["Bravo"]
    assert [e.line for e in parsed.errors] == [2, 3]
    assert "count is not an integer" in parsed.errors[0].reason


def test_bom_and_crlf() -> None:
    data = ("\ufeff" + INVENTORY_HEADER + "\r\n1,1,Alpha,1,,,,0\r\n").encode()
    [snap] = parse_inventory(data).snapshots
    assert snap.character == "Alpha"


def test_unknown_header() -> None:
    with pytest.raises(CsvFormatError, match="unknown header"):
        parse_inventory(b"a,b\n1,2\n")


def test_icon_with_trailing_newline_is_rejected() -> None:
    assert normalize_icon("Game/ui/icon/icon_item_1\n") is None
