from datetime import datetime

from pydantic import BaseModel
from pydantic import Field as PydanticField


class PricePointRead(BaseModel):
    item_id: int
    source: str
    price: int
    captured_at: datetime


class PriceBucketRead(BaseModel):
    bucket_start: datetime
    min_price: int
    max_price: int
    avg_price: float
    last_price: int


class PricePointCreate(BaseModel):
    source: str = PydanticField(min_length=1, max_length=40)
    price: int = PydanticField(ge=0)
    captured_at: datetime
