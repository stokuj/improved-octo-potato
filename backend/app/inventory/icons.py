# Fetches item icons from ArcheAge Codex once and serves them from a local cache.
import asyncio
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

CODEX_PAGE = "https://archeagecodex.com/us/item/{item_type}/"
CODEX_ORIGIN = "https://archeagecodex.com/"
# The item's own icon is the first image in the page's `item-icon` cell; related items come later.
_ICON_CELL = re.compile(r'class="item-icon">.*?<img src="([^"]*)"', re.DOTALL)
_ICON_SRC = re.compile(r"//archeagecodex\.com/(items/[a-z0-9_]+(?:/[a-z0-9_]+)*\.png)")
# Codex answers unknown names with 200 and this generic 1891-byte image (fetched 2026-10-23).
CODEX_PLACEHOLDER_SHA256 = (
    "17e787bf26c33e45813d82c103aaf42ddf48315a893a1b4be72d12ed26423c2a"
)
MAX_FETCHES_PER_MINUTE = 60
# A first page load asks for ~50 icons at once; keep the burst on Codex small.
MAX_PARALLEL_FETCHES = 4
_parallel = asyncio.Semaphore(MAX_PARALLEL_FETCHES)
# shortcut: per-process window (2 prod workers → up to 2x), move to the shared limiter if Codex complains
_fetches: deque[float] = deque()


class FetchBudgetExceeded(Exception):
    """Too many Codex fetches in the last minute; try again later."""


def icon_path(html: str) -> str | None:
    """The icon path on a Codex item page, e.g. `items/icon_item_0352.png`."""
    cell = _ICON_CELL.search(html)
    src = cell and _ICON_SRC.fullmatch(cell.group(1))
    return src.group(1) if src else None


def _client() -> httpx.AsyncClient:
    # Codex drops about 1 in 7 TCP connects (seen 2026-10-23, also with curl); retry those quickly.
    return httpx.AsyncClient(
        timeout=httpx.Timeout(5, connect=2),
        transport=httpx.AsyncHTTPTransport(retries=2),
    )


async def fetch_codex(item_type: int) -> bytes | None:
    """The network calls. b"" when Codex has no icon (cached), None on any other failure (retried)."""
    try:
        async with _client() as client:
            page = await client.get(CODEX_PAGE.format(item_type=item_type))
            if page.status_code != 200:
                return None
            path = icon_path(page.text)
            if path is None:
                if "<title>ERROR!" in page.text:  # Codex's page for an unknown id
                    return b""
                log.warning("Codex page for %s has no icon box", item_type)
                return None
            r = await client.get(CODEX_ORIGIN + path)
    except httpx.HTTPError as e:
        log.warning("Codex icon %s failed: %r", item_type, e)
        return None
    if (
        r.status_code != 200
        or r.headers.get("content-type", "").split(";")[0] != "image/png"
    ):
        return None
    if hashlib.sha256(r.content).hexdigest() == CODEX_PLACEHOLDER_SHA256:
        return b""
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


async def get_icon(item_type: int) -> bytes | None:
    """PNG bytes, or None when the icon does not exist."""
    cache = Path(settings.icon_cache_dir)
    png, missing = cache / f"{item_type}.png", cache / f"{item_type}.missing"
    if png.exists():
        return png.read_bytes()
    if missing.exists():
        return None
    _take_budget()
    # shortcut: no per-item lock; two concurrent misses both fetch and write identical bytes
    async with _parallel:
        data = await fetch_codex(item_type)
    if data is None:
        return None
    if data == b"":
        _write(missing, b"")
        return None
    _write(png, data)
    return data
