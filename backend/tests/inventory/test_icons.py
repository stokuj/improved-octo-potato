import asyncio
import hashlib
from functools import partial

import httpx
import pytest
from httpx import AsyncClient

from app.core.settings import settings
from app.inventory import icons

PNG = b"\x89PNG real icon bytes"
# Trimmed from https://archeagecodex.com/us/item/16327/ (Leather) on 2026-10-23.
LEATHER_PAGE = (
    '<title>Leather - Archeage Codex</title><td class="item-icon">'
    '<div style="position: relative; left: 0; top: 0;">'
    '<img src="//archeagecodex.com/items/icon_item_0352.png" alt="icon">'
    '<img src="//archeagecodex.com/images/icon_grade1.png"></div></td>'
    '<img src="//archeagecodex.com/items/bronze.png">'
)
ERROR_PAGE = "<title>ERROR! - Archeage Codex</title><p>nothing here</p>"


@pytest.fixture(autouse=True)
def fresh_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "icon_cache_dir", str(tmp_path))
    icons._fetches.clear()


@pytest.fixture()
def codex(monkeypatch):
    """Fake Codex: returns PNG for every item unless told otherwise; records calls."""
    calls: list[int] = []
    answer = {"value": PNG}

    async def fake(item_type: int):
        calls.append(item_type)
        return answer["value"]

    monkeypatch.setattr(icons, "fetch_codex", fake)
    return calls, answer


def fake_web(monkeypatch, pages: dict[str, httpx.Response]) -> list[str]:
    """Route fetch_codex's real HTTP calls to canned responses; unknown URLs are 404."""
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return pages.get(str(request.url), httpx.Response(404))

    monkeypatch.setattr(
        icons,
        "_client",
        partial(httpx.AsyncClient, transport=httpx.MockTransport(handler)),
    )
    return seen


def png_response(data: bytes = PNG) -> httpx.Response:
    return httpx.Response(200, content=data, headers={"content-type": "image/png"})


@pytest.mark.parametrize("item_type", ["abc", "0", "-1", "1.5"])
async def test_invalid_item_type_without_fetch(
    client: AsyncClient, codex, item_type
) -> None:
    calls, _ = codex
    r = await client.get(f"/api/inventory/icons/{item_type}.png")
    assert r.status_code == 422
    assert calls == []


async def test_miss_fetches_once_then_cache(client: AsyncClient, codex) -> None:
    calls, _ = codex
    a = await client.get("/api/inventory/icons/16327.png")
    b = await client.get("/api/inventory/icons/16327.png")
    assert (a.status_code, b.status_code) == (200, 200)
    assert a.content == b.content == PNG
    assert a.headers["content-type"] == "image/png"
    assert "max-age" in a.headers["cache-control"]
    assert calls == [16327]


async def test_no_icon_is_missing_and_remembered(client: AsyncClient, codex) -> None:
    calls, answer = codex
    answer["value"] = b""
    assert (await client.get("/api/inventory/icons/9999.png")).status_code == 404
    assert (await client.get("/api/inventory/icons/9999.png")).status_code == 404
    assert calls == [9999]


async def test_fetch_error_is_not_cached(client: AsyncClient, codex) -> None:
    calls, answer = codex
    answer["value"] = None
    assert (await client.get("/api/inventory/icons/1.png")).status_code == 404
    assert (await client.get("/api/inventory/icons/1.png")).status_code == 404
    assert calls == [1, 1]


async def test_fetch_budget(client: AsyncClient, codex, monkeypatch) -> None:
    calls, _ = codex
    monkeypatch.setattr(icons, "MAX_FETCHES_PER_MINUTE", 1)
    assert (await client.get("/api/inventory/icons/1.png")).status_code == 200
    assert (await client.get("/api/inventory/icons/2.png")).status_code == 503
    assert (await client.get("/api/inventory/icons/1.png")).status_code == 200
    assert calls == [1]


async def test_parallel_fetches_are_capped(client: AsyncClient, monkeypatch) -> None:
    # A first page load asks for ~50 icons at once; Codex times out when hit that hard.
    running, peak = 0, 0

    async def slow(item_type: int):
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.01)
        running -= 1
        return PNG

    monkeypatch.setattr(icons, "fetch_codex", slow)
    rs = await asyncio.gather(
        *(client.get(f"/api/inventory/icons/{t}.png") for t in range(1, 21))
    )
    assert {r.status_code for r in rs} == {200}
    assert peak == icons.MAX_PARALLEL_FETCHES


def test_icon_path_is_the_items_own_icon() -> None:
    assert icons.icon_path(LEATHER_PAGE) == "items/icon_item_0352.png"


def test_icon_path_in_a_subfolder() -> None:
    page = LEATHER_PAGE.replace(
        "items/icon_item_0352", "items/quest/icon_item_quest169"
    )
    assert icons.icon_path(page) == "items/quest/icon_item_quest169.png"


def test_icon_path_with_a_windows_separator() -> None:
    # Codex keeps the game's `\` in some paths (item 47047 on 2026-10-23); `/` serves the icon.
    page = LEATHER_PAGE.replace(
        "items/icon_item_0352", "items/costume_bo\\nu_f_bo_leather295"
    )
    assert icons.icon_path(page) == "items/costume_bo/nu_f_bo_leather295.png"


@pytest.mark.parametrize(
    "src",
    ["//archeagecodex.com/items/../x.png", "//evil.example.com/items/a.png", ""],
)
def test_icon_path_rejects_anything_else(src) -> None:
    page = LEATHER_PAGE.replace("//archeagecodex.com/items/icon_item_0352.png", src)
    assert icons.icon_path(page) is None


async def test_fetch_codex_reads_page_then_png(monkeypatch) -> None:
    seen = fake_web(
        monkeypatch,
        {
            "https://archeagecodex.com/us/item/16327/": httpx.Response(
                200, text=LEATHER_PAGE
            ),
            "https://archeagecodex.com/items/icon_item_0352.png": png_response(),
        },
    )
    assert await icons.fetch_codex(16327) == PNG
    assert seen == [
        "https://archeagecodex.com/us/item/16327/",
        "https://archeagecodex.com/items/icon_item_0352.png",
    ]


async def test_fetch_codex_unknown_item_is_missing(monkeypatch) -> None:
    # Codex answers unknown ids with 200 and an "ERROR!" page.
    url = "https://archeagecodex.com/us/item/999999999/"
    fake_web(monkeypatch, {url: httpx.Response(200, text=ERROR_PAGE)})
    assert await icons.fetch_codex(999999999) == b""


async def test_fetch_codex_placeholder_png_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        icons, "CODEX_PLACEHOLDER_SHA256", hashlib.sha256(b"ph").hexdigest()
    )
    fake_web(
        monkeypatch,
        {
            "https://archeagecodex.com/us/item/16327/": httpx.Response(
                200, text=LEATHER_PAGE
            ),
            "https://archeagecodex.com/items/icon_item_0352.png": png_response(b"ph"),
        },
    )
    assert await icons.fetch_codex(16327) == b""


async def test_fetch_codex_changed_layout_is_not_cached(monkeypatch) -> None:
    # A real page without the icon box means Codex changed its HTML: retry later.
    url = "https://archeagecodex.com/us/item/16327/"
    fake_web(monkeypatch, {url: httpx.Response(200, text="<title>Leather</title>")})
    assert await icons.fetch_codex(16327) is None


async def test_fetch_codex_unusable_icon_path_is_missing(monkeypatch) -> None:
    # The icon box is there but its path is not one we fetch: no icon, don't ask again.
    url = "https://archeagecodex.com/us/item/16327/"
    page = LEATHER_PAGE.replace("//archeagecodex.com/items/icon_item_0352.png", "")
    seen = fake_web(monkeypatch, {url: httpx.Response(200, text=page)})
    assert await icons.fetch_codex(16327) == b""
    assert seen == [url]


async def test_fetch_codex_server_error_is_not_cached(monkeypatch) -> None:
    url = "https://archeagecodex.com/us/item/16327/"
    fake_web(monkeypatch, {url: httpx.Response(502)})
    assert await icons.fetch_codex(16327) is None


def test_real_placeholder_hash_constant() -> None:
    # Fetched from Codex on 2026-10-23 for unknown names (1891-byte generic icon).
    assert icons.CODEX_PLACEHOLDER_SHA256 == (
        "17e787bf26c33e45813d82c103aaf42ddf48315a893a1b4be72d12ed26423c2a"
    )
