# Parses ArcheBag inventory.csv into validated per-character snapshots.
import csv
import io
from dataclasses import dataclass, field
from datetime import datetime

# Shared row helpers of the market parser: same integer and epoch rules.
from app.market.csv_format import CsvFormatError, RowError, _int, _RowInvalid, _ts

INVENTORY_HEADER = (
    "snapshot_id,captured_at,character,slot,item,item_type,item_grade,count"
)
MAX_SLOTS = 300


@dataclass(frozen=True)
class SlotRow:
    slot: int
    item: str | None
    item_type: int | None
    item_grade: int | None
    count: int


@dataclass
class Snapshot:
    character: str
    snapshot_id: int
    captured_at: datetime
    slots: list[SlotRow]
    lines: int


@dataclass
class ParsedInventory:
    rows: int = 0
    snapshots: list[Snapshot] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)
    skipped: int = 0  # lines of earlier runs dropped by a same-second double click


@dataclass
class _Line:
    line: int
    captured_at: datetime | None = None
    row: SlotRow | None = None
    error: str | None = None


def _slot(r: list[str]) -> SlotRow:
    slot = _int(r[3], "slot")
    if slot < 1:
        raise _RowInvalid("slot must be at least 1")
    item = r[4] or None
    if item is None:
        return SlotRow(slot, None, None, None, _int(r[7], "count"))
    if len(item) > 120:
        raise _RowInvalid("item name longer than 120 characters")
    return SlotRow(
        slot,
        item,
        _int(r[5], "item_type"),
        _int(r[6], "item_grade"),
        _int(r[7], "count"),
    )


def _check_run(run: list[_Line]) -> str | None:
    if len(run) > MAX_SLOTS:
        return f"more than {MAX_SLOTS} slots"
    if [x.row.slot for x in run] != list(range(1, len(run) + 1)):
        return "slots are not 1..N without gaps or duplicates"
    if len({x.captured_at for x in run}) != 1:
        return "mixed captured_at in one snapshot"
    return None


def parse_inventory(data: bytes) -> ParsedInventory:
    if not data.strip():
        raise CsvFormatError("empty file")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise CsvFormatError("not UTF-8") from None
    try:
        return _read(text)
    except csv.Error as e:
        raise CsvFormatError(f"malformed CSV: {e}") from None


def _read(text: str) -> ParsedInventory:
    reader = csv.reader(io.StringIO(text, newline=""))
    header = ",".join(next(reader, []))
    if header != INVENTORY_HEADER:
        raise CsvFormatError("unknown header")

    parsed = ParsedInventory()
    groups: dict[tuple[str, int], list[_Line]] = {}  # insertion order = file order
    for r in reader:
        if not r:
            continue
        parsed.rows += 1
        entry = _Line(reader.line_num)
        try:
            if len(r) != 8:
                raise _RowInvalid(f"expected 8 columns, got {len(r)}")
            character = r[2]
            if not character or len(character) > 64:
                raise _RowInvalid("character name must be 1..64 characters")
            key = (character, _int(r[0], "snapshot_id"))
        except _RowInvalid as e:
            parsed.errors.append(RowError(entry.line, str(e)))
            continue
        try:
            entry.captured_at = _ts(r[1])
            entry.row = _slot(r)
        except _RowInvalid as e:
            entry.error = str(e)
        groups.setdefault(key, []).append(entry)

    for (character, snapshot_id), entries in groups.items():
        runs: list[list[_Line]] = [[]]
        for x in entries:
            if x.row is not None and x.row.slot == 1 and runs[-1]:
                runs.append([])
            runs[-1].append(x)
        run = runs[-1]
        parsed.skipped += sum(len(r) for r in runs[:-1])
        if bad := [x for x in run if x.error]:
            first = bad[0].line
            parsed.errors.extend(
                RowError(
                    x.line, x.error or f"snapshot rejected: line {first} is invalid"
                )
                for x in run
            )
            continue
        if reason := _check_run(run):
            parsed.errors.extend(RowError(x.line, reason) for x in run)
            continue
        parsed.snapshots.append(
            Snapshot(
                character=character,
                snapshot_id=snapshot_id,
                captured_at=run[0].captured_at,  # type: ignore[arg-type]
                slots=[x.row for x in run],  # type: ignore[misc]
                lines=len(run),
            )
        )
    parsed.errors.sort(key=lambda e: e.line)
    return parsed
