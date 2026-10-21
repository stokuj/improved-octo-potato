import uuid
from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.market.models import Item, Listing


def _suffix() -> str:
    return uuid.uuid4().hex[:8]


def _type() -> int:
    return uuid.uuid4().int % 2_000_000_000


async def test_item_type_grade_is_unique(session) -> None:
    t = _type()
    session.add(Item(item_type=t, item_grade=0, name=f"a-{_suffix()}"))
    await session.commit()
    session.add(Item(item_type=t, item_grade=0, name=f"b-{_suffix()}"))
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_item_name_is_unique(session) -> None:
    name = f"dup-{_suffix()}"
    session.add(Item(item_type=_type(), item_grade=0, name=name))
    await session.commit()
    session.add(Item(item_type=_type(), item_grade=0, name=name))
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_two_listing_only_items_may_both_have_null_type(session) -> None:
    session.add(Item(name=f"x-{_suffix()}"))
    session.add(Item(name=f"y-{_suffix()}"))
    await session.commit()


async def test_money_columns_hold_more_than_int32(session) -> None:
    item = Item(name=f"big-{_suffix()}")
    session.add(item)
    await session.commit()
    await session.refresh(item)
    session.add(
        Listing(
            item_id=item.id,
            scan_id=1792607894,
            rank=1,
            captured_at=datetime(2026, 10, 21, 18, 38),
            status="ok",
            unit_price=10**6,
            listing_price=10**10,
            stack=10_000,
        )
    )
    await session.commit()
    row = await session.get(Listing, (item.id, 1792607894, 1))
    assert row.listing_price == 10**10
