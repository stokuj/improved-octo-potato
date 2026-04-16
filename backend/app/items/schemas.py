from datetime import datetime

from pydantic import BaseModel

from app.items.models import ItemCategory, ItemGrade


class ItemRead(BaseModel):
    id: int
    name: str
    category: ItemCategory
    grade: ItemGrade
    current_price: int | None = None
    created_at: datetime
    updated_at: datetime


class ItemListItem(BaseModel):
    id: int
    name: str
    category: ItemCategory
    grade: ItemGrade
    current_price: int | None = None
    updated_at: datetime


class PaginatedItems(BaseModel):
    items: list[ItemListItem]
    total: int
    offset: int
    limit: int


class ItemFilter(BaseModel):
    category: ItemCategory | None = None
    grade: ItemGrade | None = None
