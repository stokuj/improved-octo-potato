import uuid

from sqlmodel.ext.asyncio.session import AsyncSession

from app.imports.schemas import ImportFileResult, failed
from app.inventory import services as inventory
from app.inventory.csv_format import CHESTS_HEADER, INVENTORY_HEADER
from app.market import services as market
from app.market.csv_format import LISTINGS_HEADER, MARKET_HEADER

_MARKET_KINDS = {LISTINGS_HEADER: "listings", MARKET_HEADER: "market"}
_INVENTORY_KINDS = {INVENTORY_HEADER: "inventory", CHESTS_HEADER: "chests"}


def _header(data: bytes) -> str:
    return data.split(b"\n", 1)[0].decode("utf-8-sig", errors="replace").rstrip("\r")


def _data_lines(data: bytes) -> int:
    return sum(1 for line in data.splitlines()[1:] if line.strip())


async def import_file(
    session: AsyncSession,
    user_id: uuid.UUID,
    is_superuser: bool,
    filename: str,
    data: bytes,
) -> ImportFileResult:
    """Route one uploaded CSV to its module by its exact header."""
    if len(data) > market.MAX_FILE_BYTES:
        return failed(filename, None, 0, "file larger than 50 MB")
    header = _header(data)
    if inventory_kind := _INVENTORY_KINDS.get(header):
        return await inventory.import_csv(
            session,
            user_id,
            filename,
            data,
            inventory_kind,  # type: ignore[arg-type]
        )
    kind = _MARKET_KINDS.get(header)
    if kind and not is_superuser:
        return failed(filename, kind, _data_lines(data), "admin only")
    return await market.import_csv(session, filename, data)
