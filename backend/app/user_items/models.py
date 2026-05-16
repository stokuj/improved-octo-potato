import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel, UniqueConstraint


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class UserItem(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("user_id", "item_id", name="uq_user_item"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    item_id: int = Field(foreign_key="item.id", index=True)
    created_at: datetime = Field(default_factory=utcnow)
