from datetime import date, datetime
from pathlib import Path

import pytest

from app.market.csv_format import (
    LISTINGS_HEADER,
    LISTINGS_HEADER_V2,
    MARKET_HEADER,
    MARKET_HEADER_V2,
    CsvFormatError,
    game_day,
    parse_csv,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_game_day_uses_moscow_clock() -> None:
    assert game_day(datetime(2026, 10, 21, 20, 59), 14) == date(2026, 10, 21)
    assert game_day(datetime(2026, 10, 21, 21, 30), 14) == date(2026, 10, 22)
    assert game_day(datetime(2026, 10, 21, 21, 30), 1) == date(2026, 10, 9)


def test_parse_sample_market() -> None:
    p = parse_csv((FIXTURES / "market.csv").read_bytes())
    assert (p.kind, p.rows, len(p.market), p.skipped, p.errors) == (
        "market",
        406,
        406,
        0,
        [],
    )
    leather14 = [
        r for r in p.market if r.item == "Leather" and r.scan_id == 1792607894
    ][-1]
    assert (
        leather14.item_type,
        leather14.item_grade,
        leather14.day,
        leather14.volume,
    ) == (16327, 0, date(2026, 10, 21), 171924)
    assert leather14.captured_at == datetime(2026, 10, 21, 18, 38, 16)


def test_parse_sample_listings() -> None:
    p = parse_csv((FIXTURES / "listings.csv").read_bytes())
    assert (p.kind, p.rows, len(p.listings), p.errors) == ("listings", 250, 250, [])
    nr = [r for r in p.listings if r.status == "no_result"]
    assert len(nr) == 2 and all(r.rank == 0 and r.unit_price is None for r in nr)


def test_crlf_and_bom() -> None:
    raw = (FIXTURES / "listings.csv").read_bytes().replace(b"\n", b"\r\n")
    p = parse_csv(b"\xef\xbb\xbf" + raw)
    assert (p.kind, p.rows, p.errors) == ("listings", 250, [])


def test_quoted_name_with_comma() -> None:
    data = (LISTINGS_HEADER + '\n1,1,"Sword, Rusty",ok,1,10,10,1\n').encode()
    assert parse_csv(data).listings[0].item == "Sword, Rusty"


@pytest.mark.parametrize(
    "data,reason",
    [
        (b"", "empty file"),
        (b"\xff\xfe\x00", "not UTF-8"),
        (b"a,b\n1,2\n", "unknown header"),
    ],
)
def test_whole_file_errors(data: bytes, reason: str) -> None:
    with pytest.raises(CsvFormatError, match=reason):
        parse_csv(data)


def test_header_only_file_has_zero_rows() -> None:
    p = parse_csv((MARKET_HEADER + "\n").encode())
    assert (p.kind, p.rows, p.market, p.errors) == ("market", 0, [], [])


@pytest.mark.parametrize(
    "line",
    [
        "1,1,X,ok,0,10,10,1",  # ok needs rank >= 1
        "1,1,X,ok,1,,10,1",  # ok needs prices
        "1,1,X,no_result,1,,,",  # non-ok needs rank 0
        "1,1,X,no_result,0,5,,",  # non-ok needs empty prices
        "1,1,X,weird,0,,,",  # unknown status
        "1,1,X,ok,1,-1,10,1",  # negative
        "x,1,X,ok,1,10,10,1",  # not an int
        "1,1,X,ok,1,10,10",  # too few columns
    ],
)
def test_bad_listing_rows_become_errors(line: str) -> None:
    p = parse_csv(f"{LISTINGS_HEADER}\n{line}\n".encode())
    assert p.listings == [] and [e.line for e in p.errors] == [2]


def test_market_no_answer_is_skipped_and_bad_day_is_error() -> None:
    data = (
        f"{MARKET_HEADER}\n1,1,X,5,0,no_answer,0,,,,,\n1,1,X,5,0,ok,15,1,1,1,1,1\n"
    ).encode()
    p = parse_csv(data)
    assert (p.skipped, len(p.market), [e.line for e in p.errors]) == (1, 0, [3])


def test_market_non_ok_needs_day_zero_and_empty_values() -> None:
    data = f"{MARKET_HEADER}\n1,1,X,5,0,error,3,,,,,\n".encode()
    p = parse_csv(data)
    assert (p.skipped, [e.line for e in p.errors]) == (0, [2])


def test_out_of_range_timestamp_is_row_error() -> None:
    data = f"{LISTINGS_HEADER}\n1,99999999999999,X,ok,1,10,10,1\n".encode()
    p = parse_csv(data)
    assert p.listings == [] and [e.line for e in p.errors] == [2]


def test_oversized_field_is_file_error() -> None:
    data = f'{LISTINGS_HEADER}\n1,1,"{"x" * 200_000}",ok,1,10,10,1\n'.encode()
    with pytest.raises(CsvFormatError, match="malformed CSV"):
        parse_csv(data)


def test_listings_v2_reads_type_and_grade() -> None:
    data = (
        LISTINGS_HEADER_V2 + "\n1,1,Leather,ok,1,4650,2418000,520,16327,0\n"
        "1,1,Leather,no_result,0,,,,,\n"
    ).encode()
    p = parse_csv(data)
    assert p.kind == "listings" and not p.errors
    assert (p.listings[0].item_type, p.listings[0].item_grade) == (16327, 0)
    assert (p.listings[1].item_type, p.listings[1].item_grade) == (None, None)


@pytest.mark.parametrize("tail", ["16327,", ",0"])
def test_listings_v2_half_key_is_row_error(tail: str) -> None:
    p = parse_csv(
        f"{LISTINGS_HEADER_V2}\n1,1,Leather,ok,1,4650,2418000,520,{tail}\n".encode()
    )
    assert [e.reason for e in p.errors] == [
        "item_type and item_grade must both be set or both empty"
    ]


def test_listings_v2_status_row_with_key_is_row_error() -> None:
    p = parse_csv(
        f"{LISTINGS_HEADER_V2}\n1,1,Leather,no_result,0,,,,16327,0\n".encode()
    )
    assert [e.reason for e in p.errors] == [
        "no_result row needs empty item_type and item_grade"
    ]


def test_market_v2_reads_category_and_empty_is_none() -> None:
    rows = "\n".join(
        f"1792607894,1792607894,Leather,16327,0,ok,{d},4702,4877,2100,19999,1000,{c}"
        for d, c in ((14, "Hide"), (13, ""))
    )
    p = parse_csv(f"{MARKET_HEADER_V2}\n{rows}\n".encode())
    assert [m.category for m in p.market] == ["Hide", None]


def test_market_v2_category_too_long_is_row_error() -> None:
    p = parse_csv(
        f"{MARKET_HEADER_V2}\n1,1,Leather,16327,0,ok,14,1,1,1,1,1,{'x' * 65}\n".encode()
    )
    assert [e.reason for e in p.errors] == ["category longer than 64"]


def test_v1_headers_still_parse() -> None:  # the sample fixtures are V1
    assert parse_csv((FIXTURES / "listings.csv").read_bytes()).kind == "listings"
    assert parse_csv((FIXTURES / "market.csv").read_bytes()).kind == "market"
