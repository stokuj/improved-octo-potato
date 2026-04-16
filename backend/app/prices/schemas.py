from datetime import datetime

from pydantic import BaseModel


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
