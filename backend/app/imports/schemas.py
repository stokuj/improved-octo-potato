from typing import Literal

from pydantic import BaseModel


class ImportRowError(BaseModel):
    line: int  # 0 = whole-file problem
    reason: str


class ImportFileResult(BaseModel):
    filename: str
    kind: Literal["listings", "market", "inventory", "chests"] | None
    rows: int
    inserted: int
    updated: int
    skipped: int
    error_count: int
    errors: list[ImportRowError]  # first MAX_ERRORS only


def failed(filename: str, kind, rows: int, reason: str) -> ImportFileResult:
    # Nothing imported: every row counts as an error so the sum still equals rows.
    return ImportFileResult(
        filename=filename,
        kind=kind,
        rows=rows,
        inserted=0,
        updated=0,
        skipped=0,
        error_count=rows,
        errors=[ImportRowError(line=0, reason=reason)],
    )
