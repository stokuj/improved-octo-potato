from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SlotRead(BaseModel):
    slot: int
    item: str | None
    item_type: int | None
    item_grade: int | None
    count: int
    # Per item (item_type, item_grade), summed over slots, newest vs previous snapshot.
    change: Literal["new", "up", "down"] | None
    delta: int | None


class GridRead(BaseModel):
    """The newest snapshot of one place: a bag, a warehouse or a chest."""

    captured_at: datetime
    previous_captured_at: datetime | None
    slot_count: int
    filled: int
    slots: list[SlotRead]


class CharacterRead(BaseModel):
    character: str
    bag: GridRead | None
    bank: GridRead | None


class ChestRead(GridRead):
    chest: int
    name: str | None  # last non-empty name; None if never named
    saved_by: str  # character of the newest snapshot
