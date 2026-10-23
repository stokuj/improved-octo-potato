import uuid
from datetime import datetime

from sqlalchemy import BigInteger, SmallInteger
from sqlmodel import Field, SQLModel, UniqueConstraint


class InventorySnapshot(SQLModel, table=True):
    """One ArcheBag click for one character; only the two newest are kept."""

    __tablename__ = "inventory_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "character", "snapshot_id", name="uq_inventory_snapshot"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE", index=True)
    character: str = Field(max_length=64)
    snapshot_id: int = Field(sa_type=BigInteger)
    captured_at: datetime
    slot_count: int = Field(sa_type=SmallInteger)


class InventorySlot(SQLModel, table=True):
    """One bag slot; empty slots are stored too so the grid keeps its size."""

    __tablename__ = "inventory_slot"

    snapshot: int = Field(
        foreign_key="inventory_snapshot.id", ondelete="CASCADE", primary_key=True
    )
    slot: int = Field(sa_type=SmallInteger, primary_key=True)
    item: str | None = Field(default=None, max_length=120)
    item_type: int | None = None
    item_grade: int | None = Field(default=None, sa_type=SmallInteger)
    count: int
    icon: str | None = Field(default=None, max_length=64)
