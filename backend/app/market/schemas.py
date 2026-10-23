from datetime import date, datetime

from pydantic import BaseModel


class MarketItemRead(BaseModel):
    id: int
    name: str
    item_type: int | None
    item_grade: int | None
    last_day: date | None


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


class SummaryRow(BaseModel):
    item_id: int
    name: str
    day: date
    today_avg: int
    avg_7d: int | None  # weekly_avg of the day before "today"
    change_pct: float | None
    sold_today: int
    avg_daily_volume: float | None  # mean volume of the 7 days before "today"
