import uuid

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.errors import NotFoundError
from app.imports.schemas import ImportFileResult, ImportRowError, failed
from app.inventory.csv_format import Snapshot, parse_inventory
from app.inventory.models import InventorySlot, InventorySnapshot
from app.inventory.schemas import BagRead, CharacterRead, SlotRead
from app.market.csv_format import CsvFormatError
from app.market.services import MAX_ERRORS

KEEP = 2  # newest + previous snapshot per character
CHUNK_ROWS = 2_000  # 7 columns x 2000 stays under asyncpg's 32767 bind params


async def _store(session: AsyncSession, user_id: uuid.UUID, snap: Snapshot) -> None:
    row = InventorySnapshot(
        user_id=user_id,
        character=snap.character,
        snapshot_id=snap.snapshot_id,
        captured_at=snap.captured_at,
        slot_count=len(snap.slots),
    )
    session.add(row)
    await session.flush()
    slots = [
        {
            "snapshot": row.id,
            "slot": s.slot,
            "item": s.item,
            "item_type": s.item_type,
            "item_grade": s.item_grade,
            "count": s.count,
        }
        for s in snap.slots
    ]
    for i in range(0, len(slots), CHUNK_ROWS):
        await session.exec(pg_insert(InventorySlot).values(slots[i : i + CHUNK_ROWS]))  # type: ignore[call-overload]


async def _import_character(
    session: AsyncSession, user_id: uuid.UUID, character: str, snaps: list[Snapshot]
) -> tuple[int, int]:
    """Keep the KEEP newest of stored + uploaded snapshots. Returns (inserted, skipped) lines."""
    stored = (
        await session.exec(
            select(InventorySnapshot)
            .where(InventorySnapshot.user_id == user_id)
            .where(InventorySnapshot.character == character)
        )
    ).all()
    known = {s.snapshot_id for s in stored}
    new = [s for s in snaps if s.snapshot_id not in known]
    skipped = sum(s.lines for s in snaps if s.snapshot_id in known)

    ranked = sorted(
        [(s.captured_at, s.snapshot_id, s) for s in stored]
        + [(s.captured_at, s.snapshot_id, s) for s in new],
        key=lambda t: (t[0], t[1]),
        reverse=True,
    )
    keep = {id(t[2]) for t in ranked[:KEEP]}

    inserted = 0
    for s in new:
        if id(s) in keep:
            await _store(session, user_id, s)
            inserted += s.lines
        else:
            skipped += s.lines
    if evicted := [s.id for s in stored if id(s) not in keep]:
        await session.exec(  # type: ignore[call-overload]
            delete(InventorySnapshot).where(InventorySnapshot.id.in_(evicted))  # type: ignore[union-attr]
        )
    return inserted, skipped


async def import_csv(
    session: AsyncSession, user_id: uuid.UUID, filename: str, data: bytes
) -> ImportFileResult:
    try:
        parsed = parse_inventory(data)
    except CsvFormatError as e:
        return failed(filename, "inventory", 0, str(e))

    by_character: dict[str, list[Snapshot]] = {}
    for snap in parsed.snapshots:
        by_character.setdefault(snap.character, []).append(snap)

    inserted, skipped = 0, parsed.skipped
    try:
        for character, snaps in by_character.items():
            i, s = await _import_character(session, user_id, character, snaps)
            inserted, skipped = inserted + i, skipped + s
        await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()
        return failed(
            filename, "inventory", parsed.rows, f"database error: {type(e).__name__}"
        )

    return ImportFileResult(
        filename=filename,
        kind="inventory",
        rows=parsed.rows,
        inserted=inserted,
        updated=0,
        skipped=skipped,
        error_count=len(parsed.errors),
        errors=[
            ImportRowError(line=e.line, reason=e.reason)
            for e in parsed.errors[:MAX_ERRORS]
        ],
    )


async def _snapshots(
    session: AsyncSession, user_id: uuid.UUID, character: str | None = None
):
    """The user's snapshots, newest first; optionally for one character."""
    stmt = select(InventorySnapshot).where(InventorySnapshot.user_id == user_id)
    if character is not None:
        stmt = stmt.where(InventorySnapshot.character == character)
    stmt = stmt.order_by(
        InventorySnapshot.captured_at.desc(),  # type: ignore[attr-defined]
        InventorySnapshot.snapshot_id.desc(),  # type: ignore[attr-defined]
    )
    return (await session.exec(stmt)).all()


async def _slots(session: AsyncSession, snapshot_pk: int) -> list[InventorySlot]:
    stmt = (
        select(InventorySlot)
        .where(InventorySlot.snapshot == snapshot_pk)
        .order_by(InventorySlot.slot)  # type: ignore[arg-type]
    )
    return list((await session.exec(stmt)).all())


def _totals(slots: list[InventorySlot]) -> dict[tuple, int]:
    totals: dict[tuple, int] = {}
    for s in slots:
        if s.item is not None:
            key = (s.item_type, s.item_grade)
            totals[key] = totals.get(key, 0) + s.count
    return totals


async def list_characters(
    session: AsyncSession, user_id: uuid.UUID
) -> list[CharacterRead]:
    newest: dict[str, InventorySnapshot] = {}
    previous: dict[str, InventorySnapshot] = {}
    for snap in await _snapshots(session, user_id):
        (previous if snap.character in newest else newest).setdefault(
            snap.character, snap
        )
    out = []
    for name in sorted(newest):
        snap = newest[name]
        filled = sum(1 for s in await _slots(session, snap.id) if s.item is not None)  # type: ignore[arg-type]
        prev = previous.get(name)
        out.append(
            CharacterRead(
                character=name,
                captured_at=snap.captured_at,
                previous_captured_at=prev.captured_at if prev else None,
                slot_count=snap.slot_count,
                filled=filled,
            )
        )
    return out


async def get_bag(session: AsyncSession, user_id: uuid.UUID, character: str) -> BagRead:
    snaps = await _snapshots(session, user_id, character)
    if not snaps:
        raise NotFoundError("character not found")
    now = await _slots(session, snaps[0].id)  # type: ignore[arg-type]
    before = _totals(await _slots(session, snaps[1].id)) if len(snaps) > 1 else None  # type: ignore[arg-type]
    totals = _totals(now)

    def change(s: InventorySlot) -> tuple[str | None, int | None]:
        if before is None or s.item is None:
            return None, None
        key = (s.item_type, s.item_grade)
        if key not in before:
            return "new", totals[key]
        delta = totals[key] - before[key]
        return ("up" if delta > 0 else "down" if delta < 0 else None), delta

    slots = []
    for s in now:
        flag, delta = change(s)
        slots.append(
            SlotRead(
                slot=s.slot,
                item=s.item,
                item_type=s.item_type,
                item_grade=s.item_grade,
                count=s.count,
                change=flag,  # type: ignore[arg-type]
                delta=delta,
            )
        )
    return BagRead(
        character=character,
        captured_at=snaps[0].captured_at,
        previous_captured_at=snaps[1].captured_at if len(snaps) > 1 else None,
        slots=slots,
    )
