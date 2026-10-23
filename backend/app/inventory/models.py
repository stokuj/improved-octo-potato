import uuid
from datetime import datetime

from sqlalchemy import BigInteger, SmallInteger
from sqlmodel import Field, SQLModel, UniqueConstraint


class InventorySnapshot(SQLModel, table=True):
    """One saved place: a character's bag or warehouse, or a chest; two newest kept."""

    __tablename__ = "inventory_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "container",
            "chest",
            "character",
            "snapshot_id",
            name="uq_inventory_snapshot",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE", index=True)
    container: str = Field(max_length=5)  # bag | bank | chest
    chest: int = Field(default=0, sa_type=SmallInteger)  # 1..10 for a chest, else 0
    character: str = Field(max_length=64)  # for a chest: who saved it
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


class ChestName(SQLModel, table=True):
    """Last non-empty name per chest; outlives the two kept snapshots."""

    __tablename__ = "inventory_chest_name"

    user_id: uuid.UUID = Field(
        foreign_key="user.id", ondelete="CASCADE", primary_key=True
    )
    chest: int = Field(sa_type=SmallInteger, primary_key=True)
    name: str = Field(max_length=15)
    captured_at: datetime
