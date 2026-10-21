from typing import Literal

from pydantic import BaseModel


class ImportRowError(BaseModel):
    line: int  # 0 = whole-file problem
    reason: str


class ImportFileResult(BaseModel):
    filename: str
    kind: Literal["listings", "market"] | None
    rows: int
    inserted: int
    updated: int
    skipped: int
    error_count: int
    errors: list[ImportRowError]  # first MAX_ERRORS only
