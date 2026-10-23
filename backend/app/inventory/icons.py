# Fetches item icons from ArcheAge Codex once and serves them from a local cache.
import hashlib
import logging
import os
import re
import tempfile
import time
from collections import deque
from pathlib import Path

import httpx

from app.core.settings import settings

log = logging.getLogger(__name__)

CODEX_URL = "https://archeagecodex.com/items/{name}.png"
# Codex answers unknown names with 200 and this generic 1891-byte image (fetched 2026-10-23).
CODEX_PLACEHOLDER_SHA256 = (
    "17e787bf26c33e45813d82c103aaf42ddf48315a893a1b4be72d12ed26423c2a"
)
MAX_FETCHES_PER_MINUTE = 60
_NAME = re.compile(r"^[a-z0-9_]{1,64}$")
# shortcut: per-process window (2 prod workers → up to 2x), move to the shared limiter if Codex complains
_fetches: deque[float] = deque()


class FetchBudgetExceeded(Exception):
    """Too many Codex fetches in the last minute; try again later."""


def valid_name(name: str) -> str | None:
    name = name.lower()
    return name if _NAME.fullmatch(name) else None


async def fetch_codex(name: str) -> bytes | None:
    """The one network call. None on any failure (not cached, retried next time)."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(CODEX_URL.format(name=name))
    except httpx.HTTPError as e:
        log.warning("Codex icon %s failed: %s", name, e)
        return None
    if (
        r.status_code != 200
        or r.headers.get("content-type", "").split(";")[0] != "image/png"
    ):
        return None
    return r.content


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def _take_budget() -> None:
    now = time.monotonic()
    while _fetches and now - _fetches[0] > 60:
        _fetches.popleft()
    if len(_fetches) >= MAX_FETCHES_PER_MINUTE:
        raise FetchBudgetExceeded
    _fetches.append(now)


async def get_icon(name: str) -> bytes | None:
    """PNG bytes, or None when the icon does not exist. `name` must be valid."""
    cache = Path(settings.icon_cache_dir)
    png, missing = cache / f"{name}.png", cache / f"{name}.missing"
    if png.exists():
        return png.read_bytes()
    if missing.exists():
        return None
    _take_budget()
    # shortcut: no per-name lock; two concurrent misses both fetch and write identical bytes
    data = await fetch_codex(name)
    if data is None:
        return None
    if hashlib.sha256(data).hexdigest() == CODEX_PLACEHOLDER_SHA256:
        _write(missing, b"")
        return None
    _write(png, data)
    return data
