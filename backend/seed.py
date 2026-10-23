"""Seed the database with the ArcheMarket sample CSVs (the same files the tests use)."""

import asyncio
from pathlib import Path

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import async_session_maker
from app.imports.schemas import ImportFileResult
from app.market.services import import_csv

FIXTURES = Path(__file__).parent / "tests" / "market" / "fixtures"


async def seed(session: AsyncSession) -> list[ImportFileResult]:
    return [
        await import_csv(session, name, (FIXTURES / name).read_bytes())
        for name in ("market.csv", "listings.csv")
    ]


async def main() -> None:
    async with async_session_maker() as session:
        for r in await seed(session):
            print(
                f"{r.filename}: {r.rows} rows, {r.inserted} inserted, "
                f"{r.updated} updated, {r.skipped} skipped, {r.error_count} errors"
            )


if __name__ == "__main__":
    asyncio.run(main())
