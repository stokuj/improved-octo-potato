from pathlib import Path


def read_new_lines(path: Path, offset: int) -> tuple[list[str], int]:
    """Read complete lines (terminated by \\n) from `offset` to EOF.

    Returns (lines, new_offset). A trailing partial line (no \\n) is NOT consumed —
    we wait for the next poll when it's complete. This prevents tearing JSON lines.
    """
    if not path.exists():
        return [], offset

    with path.open("rb") as f:
        f.seek(offset)
        data = f.read()

    if not data:
        return [], offset

    text = data.decode("utf-8", errors="replace")
    last_nl = text.rfind("\n")
    if last_nl < 0:
        # No complete line in the new data
        return [], offset

    complete = text[: last_nl + 1]
    lines = [ln for ln in complete.splitlines() if ln]
    new_offset = offset + len(complete.encode("utf-8"))
    return lines, new_offset


def detect_truncation(path: Path, offset: int) -> bool:
    """True when the file shrunk below the offset (rotated / replaced)."""
    if not path.exists():
        return False
    return path.stat().st_size < offset
