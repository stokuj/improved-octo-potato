from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from discord import Interaction, app_commands
from discord.ext import commands

from cogs._http import get_http_client

GRADE_CHOICES = [
    app_commands.Choice(name="basic", value=0),
    app_commands.Choice(name="grand", value=1),
    app_commands.Choice(name="rare", value=2),
    app_commands.Choice(name="arcane", value=3),
    app_commands.Choice(name="heroic", value=4),
    app_commands.Choice(name="unique", value=5),
    app_commands.Choice(name="celestial", value=6),
    app_commands.Choice(name="divine", value=7),
    app_commands.Choice(name="epic", value=8),
    app_commands.Choice(name="legendary", value=9),
    app_commands.Choice(name="mythic", value=10),
    app_commands.Choice(name="eternal", value=11),
]

# Map int grade (0-11) to the display name shown to users.
GRADE_INT_TO_STR: dict[int, str] = {c.value: c.name.capitalize() for c in GRADE_CHOICES}


def format_price(copper: int) -> str:
    """Return copper amount as human-readable gold/silver/copper string."""
    g = copper // 10000
    s = (copper % 10000) // 100
    c = copper % 100
    parts = []
    if g:
        parts.append(f"{g}g")
    if s:
        parts.append(f"{s}s")
    if c or not parts:
        parts.append(f"{c}c")
    return " ".join(parts)


async def lookup_item(api_url: str, name: str, grade_int: int) -> tuple[dict | None, list[str]]:
    """Search backend for item by name+grade.

    Returns (item_dict, []) on exact match, or (None, suggestions) if not found.
    suggestions is a list of up to 5 unique item names from the search results.
    Raises httpx.HTTPError on network/backend failure.
    """
    grade_str = GRADE_INT_TO_STR[grade_int]
    client = get_http_client()
    resp = await client.get(
        f"{api_url}/items/",
        params={"q": name, "limit": 20},
    )
    resp.raise_for_status()

    items: list[dict] = resp.json()["items"]

    exact = next(
        (i for i in items if i["name"].lower() == name.lower() and i["grade"] == grade_str),
        None,
    )
    if exact is not None:
        return exact, []

    seen: set[str] = set()
    suggestions: list[str] = []
    for item in items:
        n = item["name"]
        if n not in seen:
            seen.add(n)
            suggestions.append(n)
            if len(suggestions) == 5:
                break
    return None, suggestions


async def post_price(
    api_url: str,
    name: str,
    grade_int: int,
    price_copper: int,
    ingest_token: str,
) -> None:
    """POST one price row to the ingest API.

    Raises httpx.HTTPError on network/HTTP failure.
    Raises ValueError with backend reason if the row was accepted=0 (skipped/rejected).
    """
    ts = datetime.now(timezone.utc).isoformat()
    payload = {
        "rows": [
            {
                "name": name,
                "grade": grade_int,
                "price": price_copper,
                "ts": ts,
                "source": "ah",
            }
        ]
    }
    client = get_http_client()
    resp = await client.post(
        f"{api_url}/ingest/prices",
        json=payload,
        headers={"Authorization": f"Bearer {ingest_token}"},
    )
    resp.raise_for_status()

    body = resp.json()
    if body.get("accepted", 0) == 0:
        errors = body.get("errors", [])
        reason = errors[0]["reason"] if errors else "row odrzucony przez backend"
        raise ValueError(reason)


class PricesCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="addprice", description="Add an AH price for an item")
    @app_commands.describe(
        name="Item name (exact, e.g. Iron Ore)",
        grade="Item grade (default: basic)",
        gold="Gold",
        silver="Silver",
        copper="Copper",
    )
    @app_commands.choices(grade=GRADE_CHOICES)
    async def addprice(
        self,
        interaction: Interaction,
        name: str,
        gold: int = 0,
        silver: int = 0,
        copper: int = 0,
        grade: int = 0,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        if gold < 0 or silver < 0 or copper < 0:
            await interaction.followup.send("Values cannot be negative.", ephemeral=True)
            return

        total = gold * 10000 + silver * 100 + copper
        if total == 0:
            await interaction.followup.send("Price cannot be zero.", ephemeral=True)
            return
        if total > 999_999 * 10000:
            await interaction.followup.send("Price looks unreasonably high.", ephemeral=True)
            return

        try:
            item, suggestions = await lookup_item(self.bot.api_url, name.strip(), grade)
        except (httpx.HTTPError, KeyError, ValueError):
            logging.exception("Backend error in /addprice lookup")
            await interaction.followup.send(
                "Backend connection error — try again later.", ephemeral=True
            )
            return

        if item is None:
            grade_name = GRADE_INT_TO_STR[grade].lower()
            msg = f'Item "{name}" (grade: {grade_name}) not found.'
            if suggestions:
                msg += f"\nDid you mean: {', '.join(suggestions)}?"
            await interaction.followup.send(msg, ephemeral=True)
            return

        try:
            await post_price(
                self.bot.api_url,
                item["name"],
                grade,
                total,
                self.bot.ingest_token,
            )
        except httpx.HTTPError:
            logging.exception("Backend unreachable posting price in /addprice")
            await interaction.followup.send(
                "Backend connection error — try again later.", ephemeral=True
            )
            return
        except ValueError as exc:
            logging.warning("Backend rejected price in /addprice: %s", exc)
            await interaction.followup.send(f"Price rejected by backend: {exc}", ephemeral=True)
            return

        grade_name = GRADE_INT_TO_STR[grade].lower()
        await interaction.followup.send(
            f"{item['name']} ({grade_name}): {format_price(total)} saved.",
            ephemeral=True,
        )

    @app_commands.command(name="price", description="Check the current price of an item")
    @app_commands.describe(
        name="Item name",
        grade="Item grade (default: basic)",
    )
    @app_commands.choices(grade=GRADE_CHOICES)
    async def price(
        self,
        interaction: Interaction,
        name: str,
        grade: int = 0,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        try:
            item, suggestions = await lookup_item(self.bot.api_url, name.strip(), grade)
        except (httpx.HTTPError, KeyError, ValueError):
            logging.exception("Backend error in /price")
            await interaction.followup.send(
                "Backend connection error — try again later.", ephemeral=True
            )
            return

        grade_name = GRADE_INT_TO_STR[grade].lower()

        if item is None:
            msg = f'Item "{name}" (grade: {grade_name}) not found.'
            if suggestions:
                msg += f"\nDid you mean: {', '.join(suggestions)}?"
            await interaction.followup.send(msg, ephemeral=True)
            return

        current = item.get("current_price")
        if current is None:
            await interaction.followup.send(
                f"{item['name']} ({grade_name}): no price yet — use /addprice",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"{item['name']} ({grade_name}): {format_price(current)}",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PricesCog(bot))
