from datetime import datetime

from pydantic import BaseModel, Field


class PriceIngestRow(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    grade: int = Field(ge=0, le=11)
    price: int = Field(gt=0)
    ts: datetime
    source: str = Field(min_length=1, max_length=40)


class IngestRequest(BaseModel):
    rows: list[PriceIngestRow] = Field(max_length=100)


class IngestErrorRow(BaseModel):
    row_index: int
    reason: str


class IngestResponse(BaseModel):
    accepted: int
    auto_created: int
    skipped: int
    errors: list[IngestErrorRow]
