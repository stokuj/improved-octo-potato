from datetime import date, datetime

from pydantic import BaseModel


class MarketItemRead(BaseModel):
    id: int
    name: str
    item_type: int | None
    item_grade: int | None
    category: str | None
    last_day: date | None
    # Offers smaller than this are bait ("tiny stack"); see services.min_stack.
    min_stack: int
    cheapest_real: (
        int | None
    )  # lowest ok unit price with stack >= min_stack, newest scan
    scan_at: datetime | None


class MarketDayRead(BaseModel):
    day: date
    daily_avg: int
    weekly_avg: int
    min: int
    max: int
    volume: int


class ListingRead(BaseModel):
    scan_id: int
    captured_at: datetime
    status: str
    rank: int
    unit_price: int | None
    listing_price: int | None
    stack: int | None
    tiny: bool


class ListingsRead(BaseModel):
    scan_id: int | None
    captured_at: datetime | None
    min_stack: int
    listings: list[ListingRead]
