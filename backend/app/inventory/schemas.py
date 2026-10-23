from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class CharacterRead(BaseModel):
    character: str
    captured_at: datetime
    previous_captured_at: datetime | None
    slot_count: int
    filled: int


class SlotRead(BaseModel):
    slot: int
    item: str | None
    item_type: int | None
    item_grade: int | None
    count: int
    icon: str | None
    # Per item (item_type, item_grade), summed over slots, newest vs previous snapshot.
    change: Literal["new", "up", "down"] | None
    delta: int | None


class BagRead(BaseModel):
    character: str
    captured_at: datetime
    previous_captured_at: datetime | None
    slots: list[SlotRead]
