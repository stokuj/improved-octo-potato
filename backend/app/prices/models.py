from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PricePoint(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    item_id: int = Field(foreign_key="item.id", index=True)
    source: str = Field(index=True, max_length=40)
    price: int = Field(ge=0)
    captured_at: datetime = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)
