import hashlib

import pytest
from httpx import AsyncClient

from app.core.settings import settings
from app.inventory import icons

PNG = b"\x89PNG real icon bytes"


@pytest.fixture(autouse=True)
def fresh_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "icon_cache_dir", str(tmp_path))
    icons._fetches.clear()


@pytest.fixture()
def codex(monkeypatch):
    """Fake Codex: returns PNG for every name unless told otherwise; records calls."""
    calls: list[str] = []
    answer = {"value": PNG}

    async def fake(name: str):
        calls.append(name)
        return answer["value"]

    monkeypatch.setattr(icons, "fetch_codex", fake)
    return calls, answer


@pytest.mark.parametrize("name", ["ICON..x", "a%2Fb", "x" * 65, "bad-name"])
async def test_invalid_name_404_without_fetch(client: AsyncClient, codex, name) -> None:
    calls, _ = codex
    assert (await client.get(f"/api/inventory/icons/{name}.png")).status_code == 404
    assert calls == []


async def test_uppercase_is_lowercased(client: AsyncClient, codex) -> None:
    calls, _ = codex
    r = await client.get("/api/inventory/icons/ICON_ITEM_0352.png")
    assert r.status_code == 200
    assert calls == ["icon_item_0352"]


async def test_miss_fetches_once_then_cache(client: AsyncClient, codex) -> None:
    calls, _ = codex
    a = await client.get("/api/inventory/icons/icon_item_0352.png")
    b = await client.get("/api/inventory/icons/icon_item_0352.png")
    assert (a.status_code, b.status_code) == (200, 200)
    assert a.content == b.content == PNG
    assert a.headers["content-type"] == "image/png"
    assert "max-age" in a.headers["cache-control"]
    assert calls == ["icon_item_0352"]


async def test_placeholder_is_missing_and_remembered(
    client: AsyncClient, codex, monkeypatch
) -> None:
    calls, answer = codex
    answer["value"] = b"ph"
    monkeypatch.setattr(
        icons, "CODEX_PLACEHOLDER_SHA256", hashlib.sha256(b"ph").hexdigest()
    )
    assert (
        await client.get("/api/inventory/icons/icon_item_9999.png")
    ).status_code == 404
    assert (
        await client.get("/api/inventory/icons/icon_item_9999.png")
    ).status_code == 404
    assert calls == ["icon_item_9999"]


async def test_fetch_error_is_not_cached(client: AsyncClient, codex) -> None:
    calls, answer = codex
    answer["value"] = None
    assert (await client.get("/api/inventory/icons/icon_item_1.png")).status_code == 404
    assert (await client.get("/api/inventory/icons/icon_item_1.png")).status_code == 404
    assert calls == ["icon_item_1", "icon_item_1"]


async def test_fetch_budget(client: AsyncClient, codex, monkeypatch) -> None:
    calls, _ = codex
    monkeypatch.setattr(icons, "MAX_FETCHES_PER_MINUTE", 1)
    assert (await client.get("/api/inventory/icons/icon_a.png")).status_code == 200
    assert (await client.get("/api/inventory/icons/icon_b.png")).status_code == 503
    assert (await client.get("/api/inventory/icons/icon_a.png")).status_code == 200
    assert calls == ["icon_a"]


def test_real_placeholder_hash_constant() -> None:
    # Fetched from Codex on 2026-10-23 for unknown names (1891-byte generic icon).
    assert icons.CODEX_PLACEHOLDER_SHA256 == (
        "17e787bf26c33e45813d82c103aaf42ddf48315a893a1b4be72d12ed26423c2a"
    )


def test_trailing_newline_is_not_a_valid_name() -> None:
    # `re.match(...$)` accepts "abc\n"; the public route must not.
    assert icons.valid_name("icon_item_1\n") is None
