from datetime import datetime

from pydantic import BaseModel

from app.items.models import ItemCategory, ItemGrade


class UserItemRead(BaseModel):
    item_id: int
    name: str
    category: ItemCategory
    grade: ItemGrade
    current_price: int | None = None
    followed_at: datetime
