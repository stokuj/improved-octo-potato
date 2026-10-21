from pydantic import BaseModel, Field

from app.items.models import ItemCategory, ItemGrade


class InventoryUpsert(BaseModel):
    quantity: int = Field(ge=0, le=10_000_000)


class InventoryItem(BaseModel):
    item_id: int
    item_name: str
    category: ItemCategory
    grade: ItemGrade
    quantity: int
