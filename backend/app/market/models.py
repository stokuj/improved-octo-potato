from datetime import date, datetime

from sqlalchemy import BigInteger, SmallInteger
from sqlmodel import Field, SQLModel, UniqueConstraint

from app.core.time import utcnow


class Item(SQLModel, table=True):
    __tablename__ = "item"
    __table_args__ = (
        UniqueConstraint("item_type", "item_grade", name="uq_item_type_grade"),
        UniqueConstraint("name", name="uq_item_name"),
    )

    id: int | None = Field(default=None, primary_key=True)
    # Game ids from market.csv; NULL until a market row names the item.
    item_type: int | None = None
    item_grade: int | None = None
    name: str = Field(max_length=120)
    # The game's category from market.csv (ArcheMarket 7e); NULL until one arrives.
    category: str | None = Field(default=None, max_length=64)
    created_at: datetime = Field(default_factory=utcnow)


class MarketDay(SQLModel, table=True):
    __tablename__ = "market_day"

    item_id: int = Field(foreign_key="item.id", primary_key=True)
    day: date = Field(primary_key=True)
    daily_avg: int = Field(sa_type=BigInteger)
    weekly_avg: int = Field(sa_type=BigInteger)
    min: int = Field(sa_type=BigInteger)
    max: int = Field(sa_type=BigInteger)
    volume: int = Field(sa_type=BigInteger)
    scan_id: int = Field(sa_type=BigInteger)
    captured_at: datetime


class Listing(SQLModel, table=True):
    __tablename__ = "listing"

    item_id: int = Field(foreign_key="item.id", primary_key=True)
    scan_id: int = Field(sa_type=BigInteger, primary_key=True)
    rank: int = Field(sa_type=SmallInteger, primary_key=True)
    captured_at: datetime
    status: str = Field(max_length=20)
    unit_price: int | None = Field(default=None, sa_type=BigInteger)
    listing_price: int | None = Field(default=None, sa_type=BigInteger)
    stack: int | None = None
