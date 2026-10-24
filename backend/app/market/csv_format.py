# Pure parsing/validation of ArcheMarket CSV files; no DB access.
import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Literal

LISTINGS_HEADER = (
    "scan_id,captured_at,item,status,rank,unit_price_copper,listing_price_copper,stack"
)
MARKET_HEADER = "scan_id,captured_at,item,item_type,item_grade,status,day,daily_avg_copper,weekly_avg_copper,min_copper,max_copper,volume"
# ArcheMarket 7e: offers carry the item key, market rows the game's category.
LISTINGS_HEADER_V2 = LISTINGS_HEADER + ",item_type,item_grade"
MARKET_HEADER_V2 = MARKET_HEADER + ",category"
CATEGORY_MAX = 64
GAME_TZ = timezone(timedelta(hours=3), "MSK")  # ArcheRage server clock (Moscow, no DST)

Kind = Literal["listings", "market"]

LISTING_NON_OK = {"no_buyout", "not_on_page1", "no_result", "error"}
MARKET_NON_OK = {"no_answer", "error"}


class CsvFormatError(Exception):
    """Whole-file problem; str(e) is the reason."""


@dataclass(frozen=True)
class RowError:
    line: int
    reason: str


@dataclass(frozen=True)
class ListingRow:
    line: int
    scan_id: int
    captured_at: datetime
    item: str
    status: str
    rank: int
    unit_price: int | None
    listing_price: int | None
    stack: int | None
    item_type: int | None = None
    item_grade: int | None = None


@dataclass(frozen=True)
class MarketRow:
    line: int
    scan_id: int
    captured_at: datetime
    item: str
    item_type: int
    item_grade: int
    day: date
    daily_avg: int
    weekly_avg: int
    min: int
    max: int
    volume: int
    category: str | None = None


@dataclass
class ParsedFile:
    kind: Kind
    rows: int = 0
    listings: list[ListingRow] = field(default_factory=list)
    market: list[MarketRow] = field(default_factory=list)
    skipped: int = 0  # market no_answer/error lines
    errors: list[RowError] = field(default_factory=list)


class _RowInvalid(Exception):
    pass


def game_day(captured_at: datetime, day: int) -> date:
    """Date of stats day `day` (14 = the scan's own game day); captured_at is naive UTC."""
    scan_date = captured_at.replace(tzinfo=timezone.utc).astimezone(GAME_TZ).date()
    return scan_date - timedelta(days=14 - day)


def _int(value: str, name: str) -> int:
    try:
        n = int(value)
    except ValueError:
        raise _RowInvalid(f"{name} is not an integer: {value!r}") from None
    if n < 0:
        raise _RowInvalid(f"{name} is negative")
    return n


def _ts(value: str) -> datetime:
    epoch = _int(value, "captured_at")
    try:
        return datetime.fromtimestamp(epoch, timezone.utc).replace(tzinfo=None)
    except (OverflowError, OSError, ValueError):
        raise _RowInvalid(f"captured_at out of range: {epoch}") from None


def _listing(line: int, r: list[str]) -> ListingRow:
    scan_id, captured_at, item, status, rank, unit, listing, stack = r[:8]
    item_type, item_grade = r[8:] or ("", "")
    if (item_type == "") != (item_grade == ""):
        raise _RowInvalid("item_type and item_grade must both be set or both empty")
    rank_n = _int(rank, "rank")
    prices = (unit, listing, stack)
    if status == "ok":
        if rank_n < 1:
            raise _RowInvalid("ok row needs rank >= 1")
        if any(v == "" for v in prices):
            raise _RowInvalid("ok row needs prices and stack")
        unit_n, listing_n, stack_n = (
            _int(unit, "unit_price_copper"),
            _int(listing, "listing_price_copper"),
            _int(stack, "stack"),
        )
    elif status in LISTING_NON_OK:
        if rank_n != 0 or any(v != "" for v in prices):
            raise _RowInvalid(f"{status} row needs rank 0 and empty prices")
        if item_type != "":
            raise _RowInvalid(f"{status} row needs empty item_type and item_grade")
        unit_n = listing_n = stack_n = None
    else:
        raise _RowInvalid(f"unknown status {status!r}")
    if not item:
        raise _RowInvalid("empty item name")
    return ListingRow(
        line,
        _int(scan_id, "scan_id"),
        _ts(captured_at),
        item,
        status,
        rank_n,
        unit_n,
        listing_n,
        stack_n,
        _int(item_type, "item_type") if item_type else None,
        _int(item_grade, "item_grade") if item_grade else None,
    )


def _market(line: int, r: list[str]) -> MarketRow | None:
    """Returns None for a valid no_answer/error line (counted as skipped)."""
    scan_id, captured_at, item, item_type, item_grade, status, day, *values = r[:12]
    category = r[12] if len(r) > 12 else ""
    if len(category) > CATEGORY_MAX:
        raise _RowInvalid(f"category longer than {CATEGORY_MAX}")
    day_n = _int(day, "day")
    if status in MARKET_NON_OK:
        if day_n != 0 or any(v != "" for v in values):
            raise _RowInvalid(f"{status} row needs day 0 and empty values")
        return None
    if status != "ok":
        raise _RowInvalid(f"unknown status {status!r}")
    if not 1 <= day_n <= 14:
        raise _RowInvalid(f"day must be 1..14, got {day_n}")
    if not item:
        raise _RowInvalid("empty item name")
    names = (
        "daily_avg_copper",
        "weekly_avg_copper",
        "min_copper",
        "max_copper",
        "volume",
    )
    daily, weekly, lo, hi, volume = (_int(v, n) for v, n in zip(values, names))
    ts = _ts(captured_at)
    return MarketRow(
        line,
        _int(scan_id, "scan_id"),
        ts,
        item,
        _int(item_type, "item_type"),
        _int(item_grade, "item_grade"),
        game_day(ts, day_n),
        daily,
        weekly,
        lo,
        hi,
        volume,
        category or None,
    )


def parse_csv(data: bytes) -> ParsedFile:
    if not data.strip():
        raise CsvFormatError("empty file")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise CsvFormatError("not UTF-8") from None
    try:
        return _read(text)
    except csv.Error as e:  # e.g. a corrupted line with a giant field
        raise CsvFormatError(f"malformed CSV: {e}") from None


def _read(text: str) -> ParsedFile:
    reader = csv.reader(io.StringIO(text, newline=""))
    header = ",".join(next(reader, []))
    if header in (LISTINGS_HEADER, LISTINGS_HEADER_V2):
        parsed, width = ParsedFile("listings"), 8 if header == LISTINGS_HEADER else 10
    elif header in (MARKET_HEADER, MARKET_HEADER_V2):
        parsed, width = ParsedFile("market"), 12 if header == MARKET_HEADER else 13
    else:
        raise CsvFormatError("unknown header")

    for r in reader:
        if not r:
            continue
        parsed.rows += 1
        line = reader.line_num
        try:
            if len(r) != width:
                raise _RowInvalid(f"expected {width} columns, got {len(r)}")
            if parsed.kind == "listings":
                parsed.listings.append(_listing(line, r))
            elif (m := _market(line, r)) is None:
                parsed.skipped += 1
            else:
                parsed.market.append(m)
        except _RowInvalid as e:
            parsed.errors.append(RowError(line, str(e)))
    return parsed
