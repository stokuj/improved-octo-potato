import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx
from httpx import Response

from cogs.prices import format_price, lookup_item, post_price

API_URL = "http://testapi"
INGEST_TOKEN = "test-ingest-token-32-characters-long-x"


# --- format_price ---


def test_format_price_gold_silver_copper():
    assert format_price(32000) == "3g 20s"


def test_format_price_zero_shows_0c():
    assert format_price(0) == "0c"


def test_format_price_only_copper():
    assert format_price(75) == "75c"


def test_format_price_exact_gold():
    assert format_price(10000) == "1g"


def test_format_price_all_parts():
    assert format_price(12345) == "1g 23s 45c"


# --- lookup_item ---


@respx.mock
async def test_lookup_item_returns_exact_match():
    respx.get(f"{API_URL}/items/").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "id": 1,
                        "name": "Iron Ore",
                        "grade": "Basic",
                        "category": "Crafting",
                        "current_price": 32000,
                        "updated_at": "2026-05-17T12:00:00",
                    }
                ],
                "total": 1,
                "offset": 0,
                "limit": 20,
            },
        )
    )

    item, suggestions = await lookup_item(API_URL, "Iron Ore", 0)

    assert item is not None
    assert item["name"] == "Iron Ore"
    assert suggestions == []


@respx.mock
async def test_lookup_item_case_insensitive():
    respx.get(f"{API_URL}/items/").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "id": 1,
                        "name": "Iron Ore",
                        "grade": "Basic",
                        "category": "Crafting",
                        "current_price": 32000,
                        "updated_at": "2026-05-17T12:00:00",
                    }
                ],
                "total": 1,
                "offset": 0,
                "limit": 20,
            },
        )
    )

    item, suggestions = await lookup_item(API_URL, "iron ore", 0)

    assert item is not None
    assert item["name"] == "Iron Ore"


@respx.mock
async def test_lookup_item_returns_suggestions_on_no_match():
    respx.get(f"{API_URL}/items/").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "id": 1,
                        "name": "Iron Ore",
                        "grade": "Basic",
                        "category": "Crafting",
                        "current_price": None,
                        "updated_at": "2026-05-17T12:00:00",
                    },
                    {
                        "id": 2,
                        "name": "Iron Ore Chunk",
                        "grade": "Basic",
                        "category": "Crafting",
                        "current_price": None,
                        "updated_at": "2026-05-17T12:00:00",
                    },
                ],
                "total": 2,
                "offset": 0,
                "limit": 20,
            },
        )
    )

    item, suggestions = await lookup_item(API_URL, "Iron Ores", 0)

    assert item is None
    assert "Iron Ore" in suggestions
    assert "Iron Ore Chunk" in suggestions


@respx.mock
async def test_lookup_item_grade_mismatch_returns_suggestions():
    respx.get(f"{API_URL}/items/").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "id": 1,
                        "name": "Iron Ore",
                        "grade": "Grand",  # grade 1, not Basic (0)
                        "category": "Crafting",
                        "current_price": 32000,
                        "updated_at": "2026-05-17T12:00:00",
                    }
                ],
                "total": 1,
                "offset": 0,
                "limit": 20,
            },
        )
    )

    item, suggestions = await lookup_item(API_URL, "Iron Ore", 0)  # looking for Basic

    assert item is None
    assert "Iron Ore" in suggestions


# --- post_price ---


@respx.mock
async def test_post_price_sends_correct_payload():
    route = respx.post(f"{API_URL}/ingest/prices").mock(
        return_value=Response(
            200,
            json={"accepted": 1, "auto_created": 0, "skipped": 0, "errors": []},
        )
    )

    await post_price(API_URL, "Iron Ore", 0, 32000, INGEST_TOKEN)

    assert route.called
    request = route.calls[0].request
    payload = json.loads(request.content)
    row = payload["rows"][0]
    assert row["name"] == "Iron Ore"
    assert row["grade"] == 0
    assert row["price"] == 32000
    assert row["source"] == "ah"
    assert request.headers.get("authorization") == f"Bearer {INGEST_TOKEN}"


@respx.mock
async def test_post_price_raises_on_http_error():
    respx.post(f"{API_URL}/ingest/prices").mock(
        return_value=Response(500, json={"detail": "error"})
    )

    with pytest.raises(httpx.HTTPStatusError):
        await post_price(API_URL, "Iron Ore", 0, 32000, INGEST_TOKEN)


@respx.mock
async def test_post_price_raises_value_error_when_backend_skips_row():
    respx.post(f"{API_URL}/ingest/prices").mock(
        return_value=Response(
            200,
            json={
                "accepted": 0,
                "auto_created": 0,
                "skipped": 1,
                "errors": [{"row_index": 0, "reason": "ts is in the future"}],
            },
        )
    )

    with pytest.raises(ValueError, match="ts is in the future"):
        await post_price(API_URL, "Iron Ore", 0, 32000, INGEST_TOKEN)


@respx.mock
async def test_post_price_ts_includes_timezone():
    route = respx.post(f"{API_URL}/ingest/prices").mock(
        return_value=Response(
            200,
            json={"accepted": 1, "auto_created": 0, "skipped": 0, "errors": []},
        )
    )

    await post_price(API_URL, "Iron Ore", 0, 32000, INGEST_TOKEN)

    payload = json.loads(route.calls[0].request.content)
    ts = payload["rows"][0]["ts"]
    assert "+" in ts or ts.endswith("Z") or ts.endswith("+00:00")


# ── Interaction mock helper ───────────────────────────────────────────────────


def make_interaction() -> MagicMock:
    """Return a minimal fake discord.Interaction for command handler tests."""
    interaction = MagicMock()
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    return interaction


def last_message(interaction: MagicMock) -> str:
    """Return the first positional arg of the last followup.send call."""
    return interaction.followup.send.call_args.args[0]


# ── /addprice handler ─────────────────────────────────────────────────────────


async def test_addprice_zero_price_sends_error():
    from cogs.prices import PricesCog

    bot = MagicMock()
    bot.api_url = "http://testapi"
    cog = PricesCog(bot)
    interaction = make_interaction()

    await cog.addprice.callback(cog, interaction, name="Egg", gold=0, silver=0, copper=0, grade=0)

    interaction.followup.send.assert_called_once()
    assert "zero" in last_message(interaction).lower()


async def test_addprice_negative_gold_sends_error():
    from cogs.prices import PricesCog

    bot = MagicMock()
    bot.api_url = "http://testapi"
    cog = PricesCog(bot)
    interaction = make_interaction()

    await cog.addprice.callback(cog, interaction, name="Egg", gold=-1, silver=0, copper=0, grade=0)

    interaction.followup.send.assert_called_once()
    assert "negative" in last_message(interaction).lower()


async def test_addprice_unreasonable_price_sends_error():
    from cogs.prices import PricesCog

    bot = MagicMock()
    bot.api_url = "http://testapi"
    cog = PricesCog(bot)
    interaction = make_interaction()

    await cog.addprice.callback(
        cog, interaction, name="Egg", gold=1_000_000, silver=0, copper=0, grade=0
    )

    interaction.followup.send.assert_called_once()
    assert "high" in last_message(interaction).lower()


@respx.mock
async def test_addprice_item_not_found_sends_not_found():
    from cogs.prices import PricesCog

    respx.get(f"{API_URL}/items/").mock(
        return_value=Response(
            200,
            json={"items": [], "total": 0, "offset": 0, "limit": 20},
        )
    )

    bot = MagicMock()
    bot.api_url = API_URL
    cog = PricesCog(bot)
    interaction = make_interaction()

    await cog.addprice.callback(
        cog, interaction, name="Nonexistent", gold=5, silver=0, copper=0, grade=0
    )

    interaction.followup.send.assert_called_once()
    assert "not found" in last_message(interaction).lower()


@respx.mock
async def test_addprice_success_sends_saved_message():
    from cogs.prices import PricesCog

    respx.get(f"{API_URL}/items/").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "id": 1,
                        "name": "Iron Ore",
                        "grade": "Basic",
                        "category": "Crafting",
                        "current_price": None,
                        "updated_at": "2026-05-17T12:00:00",
                    }
                ],
                "total": 1,
                "offset": 0,
                "limit": 20,
            },
        )
    )
    respx.post(f"{API_URL}/ingest/prices").mock(
        return_value=Response(
            200, json={"accepted": 1, "auto_created": 0, "skipped": 0, "errors": []}
        )
    )

    bot = MagicMock()
    bot.api_url = API_URL
    bot.ingest_token = INGEST_TOKEN
    cog = PricesCog(bot)
    interaction = make_interaction()

    await cog.addprice.callback(
        cog, interaction, name="Iron Ore", gold=3, silver=20, copper=0, grade=0
    )

    interaction.followup.send.assert_called_once()
    msg = last_message(interaction)
    assert "saved" in msg.lower()
    assert "3g" in msg
    assert "20s" in msg


# ── /price handler ────────────────────────────────────────────────────────────


@respx.mock
async def test_price_item_not_found_sends_not_found():
    from cogs.prices import PricesCog

    respx.get(f"{API_URL}/items/").mock(
        return_value=Response(
            200,
            json={"items": [], "total": 0, "offset": 0, "limit": 20},
        )
    )

    bot = MagicMock()
    bot.api_url = API_URL
    cog = PricesCog(bot)
    interaction = make_interaction()

    await cog.price.callback(cog, interaction, name="Nonexistent", grade=0)

    interaction.followup.send.assert_called_once()
    assert "not found" in last_message(interaction).lower()


@respx.mock
async def test_price_no_price_yet_sends_use_addprice():
    from cogs.prices import PricesCog

    respx.get(f"{API_URL}/items/").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "id": 1,
                        "name": "Iron Ore",
                        "grade": "Basic",
                        "category": "Crafting",
                        "current_price": None,
                        "updated_at": "2026-05-17T12:00:00",
                    }
                ],
                "total": 1,
                "offset": 0,
                "limit": 20,
            },
        )
    )

    bot = MagicMock()
    bot.api_url = API_URL
    cog = PricesCog(bot)
    interaction = make_interaction()

    await cog.price.callback(cog, interaction, name="Iron Ore", grade=0)

    interaction.followup.send.assert_called_once()
    assert "addprice" in last_message(interaction).lower()


@respx.mock
async def test_price_shows_formatted_price():
    from cogs.prices import PricesCog

    respx.get(f"{API_URL}/items/").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "id": 1,
                        "name": "Iron Ore",
                        "grade": "Basic",
                        "category": "Crafting",
                        "current_price": 32000,
                        "updated_at": "2026-05-17T12:00:00",
                    }
                ],
                "total": 1,
                "offset": 0,
                "limit": 20,
            },
        )
    )

    bot = MagicMock()
    bot.api_url = API_URL
    cog = PricesCog(bot)
    interaction = make_interaction()

    await cog.price.callback(cog, interaction, name="Iron Ore", grade=0)

    interaction.followup.send.assert_called_once()
    msg = last_message(interaction)
    assert "3g" in msg
    assert "20s" in msg
