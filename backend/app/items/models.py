from datetime import datetime, timezone
from enum import StrEnum

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ItemCategory(StrEnum):
    SPECIAL_PRODUCT = "Special Product"
    WEAPONS = "Weapons"
    ARMOR = "Armor"
    ACCESSORIES = "Accessories"
    INSTRUMENT = "Instrument"
    COSTUME = "Costume"
    CONSUMABLES = "Consumables"
    CRAFTING = "Crafting"
    MACHINING = "Machining"
    COMPANIONS = "Companions"
    OTHER = "Other"
    LUNAGEM = "Lunagem"
    LUNASTONE = "Lunastone"


class ItemGrade(StrEnum):
    ALL = "All"
    GRAND = "Grand"
    RARE = "Rare"
    ARCANE = "Arcane"
    HEROIC = "Heroic"
    UNIQUE = "Unique"
    CELESTIAL = "Celestial"
    DIVINE = "Divine"
    EPIC = "Epic"
    LEGENDARY = "Legendary"
    MYTHIC = "Mythic"
    ETERNAL = "Eternal"


class Item(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=120)
    category: ItemCategory = Field(default=ItemCategory.OTHER, index=True)
    grade: ItemGrade = Field(default=ItemGrade.ALL, index=True)
    current_price: int | None = Field(default=None, ge=0)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
