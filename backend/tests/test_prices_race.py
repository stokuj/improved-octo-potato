import asyncio
from datetime import datetime, timezone

import pytest

from app.prices.schemas import PricePointCreate
from app.prices.services import add_price_point


@pytest.mark.asyncio
async def test_concurrent_add_price_point_keeps_latest(session_factory, sample_item):
    """Two parallel writes must leave item.current_price == price of latest captured_at."""
    older = PricePointCreate(
        source="ah", price=100, captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    newer = PricePointCreate(
        source="ah", price=200, captured_at=datetime(2026, 1, 2, tzinfo=timezone.utc)
    )

    async def write(p):
        async with session_factory() as s:
            await add_price_point(s, sample_item.id, p)

    await asyncio.gather(write(newer), write(older))

    async with session_factory() as s:
        from app.items.models import Item

        item = await s.get(Item, sample_item.id)
        assert item.current_price == 200
        # last_price_at column is TIMESTAMP WITHOUT TIME ZONE — naive UTC
        assert item.last_price_at == newer.captured_at.replace(tzinfo=None)
