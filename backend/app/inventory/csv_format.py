# Parses ArcheBag inventory.csv (bag + warehouse) and chests.csv into validated snapshots.
import csv
import io
from dataclasses import dataclass, field
from datetime import datetime

# Shared row helpers of the market parser: same integer and epoch rules.
from app.market.csv_format import CsvFormatError, RowError, _int, _RowInvalid, _ts

INVENTORY_HEADER = (
    "snapshot_id,captured_at,character,container,slot,"
    "item,item_type,item_grade,count,category,npc_price"
)
CHESTS_HEADER = (
    "snapshot_id,captured_at,character,chest,name,zone,x,y,z,slot,"
    "item,item_type,item_grade,count,category,npc_price"
)
MAX_SLOTS = 300
CONTAINERS = ("bag", "bank")
MAX_CHEST = 10
MAX_CHEST_NAME = 15


@dataclass(frozen=True)
class _Layout:
    columns: int
    slot: int  # index of the slot column; item, item_type, item_grade, count follow
    chests: bool


_LAYOUTS = {
    INVENTORY_HEADER: _Layout(11, 4, chests=False),
    CHESTS_HEADER: _Layout(16, 9, chests=True),
}


@dataclass(frozen=True)
class SlotRow:
    slot: int
    item: str | None
    item_type: int | None
    item_grade: int | None
    count: int


@dataclass
class Snapshot:
    character: str  # for a chest: who saved it
    container: str  # bag | bank | chest
    chest: int  # 1..MAX_CHEST for a chest, 0 otherwise
    name: str | None  # chest name; None when empty
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
    character: str = ""
    name: str | None = None
    captured_at: datetime | None = None
    row: SlotRow | None = None
    error: str | None = None


def _slot(r: list[str], i: int) -> SlotRow:
    slot = _int(r[i], "slot")
    if slot < 1:
        raise _RowInvalid("slot must be at least 1")
    item = r[i + 1] or None
    if item is None:
        return SlotRow(slot, None, None, None, _int(r[i + 4], "count"))
    if len(item) > 120:
        raise _RowInvalid("item name longer than 120 characters")
    return SlotRow(
        slot,
        item,
        _int(r[i + 2], "item_type"),
        _int(r[i + 3], "item_grade"),
        _int(r[i + 4], "count"),
    )


def _place(r: list[str], layout: _Layout) -> tuple[str, str, int]:
    """(container, character, chest): a chest is one place whoever saved it."""
    if layout.chests:
        chest = _int(r[3], "chest")
        if not 1 <= chest <= MAX_CHEST:
            raise _RowInvalid(f"chest must be 1..{MAX_CHEST}")
        return "chest", "", chest
    if r[3] not in CONTAINERS:
        raise _RowInvalid("container must be bag or bank")
    return r[3], r[2], 0


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
    layout = _LAYOUTS.get(",".join(next(reader, [])))
    if layout is None:
        raise CsvFormatError("unknown header")

    parsed = ParsedInventory()
    # (container, character, chest, snapshot_id); insertion order = file order
    groups: dict[tuple[str, str, int, int], list[_Line]] = {}
    for r in reader:
        if not r:
            continue
        parsed.rows += 1
        entry = _Line(reader.line_num)
        try:
            if len(r) != layout.columns:
                raise _RowInvalid(f"expected {layout.columns} columns, got {len(r)}")
            entry.character = r[2]
            if not entry.character or len(entry.character) > 64:
                raise _RowInvalid("character name must be 1..64 characters")
            key = (*_place(r, layout), _int(r[0], "snapshot_id"))
        except _RowInvalid as e:
            parsed.errors.append(RowError(entry.line, str(e)))
            continue
        try:
            entry.captured_at = _ts(r[1])
            entry.row = _slot(r, layout.slot)
            if layout.chests:
                entry.name = r[4] or None
                if entry.name and len(entry.name) > MAX_CHEST_NAME:
                    raise _RowInvalid(f"name longer than {MAX_CHEST_NAME} characters")
        except _RowInvalid as e:
            entry.error = str(e)
        groups.setdefault(key, []).append(entry)

    for (container, _, chest, snapshot_id), entries in groups.items():
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
                character=run[0].character,
                container=container,
                chest=chest,
                name=run[0].name,
                snapshot_id=snapshot_id,
                captured_at=run[0].captured_at,  # type: ignore[arg-type]
                slots=[x.row for x in run],  # type: ignore[misc]
                lines=len(run),
            )
        )
    parsed.errors.sort(key=lambda e: e.line)
    return parsed
