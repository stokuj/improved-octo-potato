"""Seed the database with sample items, price history, and crafting recipes."""
import asyncio
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from app.config.settings import settings
from app.crafting.models import Recipe, RecipeIngredient
from app.items.models import Item, ItemCategory, ItemGrade
from app.prices.models import PricePoint


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


ITEMS = [
    # Raw crafting materials (no recipe — leaf nodes)
    ("Ethereal Dust",    ItemCategory.CRAFTING, ItemGrade.GRAND,    3_800),
    ("Lapis Lazuli",     ItemCategory.CRAFTING, ItemGrade.RARE,    12_500),
    ("Moonstone Shard",  ItemCategory.CRAFTING, ItemGrade.ARCANE,   8_200),
    ("Dragon Scale",     ItemCategory.CRAFTING, ItemGrade.HEROIC,  45_000),
    ("Void Crystal",     ItemCategory.CRAFTING, ItemGrade.UNIQUE, 120_000),
    # Weapons
    ("Iron Crossbow",    ItemCategory.WEAPONS,  ItemGrade.GRAND,   14_000),
    ("Shadow Dagger",    ItemCategory.WEAPONS,  ItemGrade.RARE,    95_000),
    ("Storm Lance",      ItemCategory.WEAPONS,  ItemGrade.ARCANE,  62_000),
    ("Blazing Sword",    ItemCategory.WEAPONS,  ItemGrade.HEROIC, 280_000),
    ("Abyssal Bow",      ItemCategory.WEAPONS,  ItemGrade.UNIQUE, 380_000),
    # Armor
    ("Iron Helm",        ItemCategory.ARMOR,    ItemGrade.GRAND,    9_500),
    ("Titan Gauntlets",  ItemCategory.ARMOR,    ItemGrade.ARCANE,  54_000),
    ("Shadow Robe",      ItemCategory.ARMOR,    ItemGrade.RARE,    88_000),
    ("Aegis Plate",      ItemCategory.ARMOR,    ItemGrade.HEROIC, 195_000),
    ("Phantom Boots",    ItemCategory.ARMOR,    ItemGrade.UNIQUE, 210_000),
    # Accessories
    ("Ring of Swiftness",  ItemCategory.ACCESSORIES, ItemGrade.RARE,       72_000),
    ("Amulet of Power",    ItemCategory.ACCESSORIES, ItemGrade.HEROIC,    150_000),
    ("Celestial Earring",  ItemCategory.ACCESSORIES, ItemGrade.CELESTIAL, 950_000),
    # Consumables
    ("Health Potion (L)", ItemCategory.CONSUMABLES, ItemGrade.GRAND, 1_200),
    ("Mana Elixir (L)",   ItemCategory.CONSUMABLES, ItemGrade.GRAND, 1_800),
    # Other
    ("Awakening Stone",   ItemCategory.SPECIAL_PRODUCT, ItemGrade.LEGENDARY, 2_500_000),
    ("Red Lunagem",       ItemCategory.LUNAGEM,          ItemGrade.RARE,         35_000),
    ("Blue Lunastone",    ItemCategory.LUNASTONE,        ItemGrade.ARCANE,       22_000),
    ("Companion Egg: Fox",ItemCategory.COMPANIONS,       ItemGrade.HEROIC,      450_000),
]

# (output_name, output_qty, [(ingredient_name, qty), ...])
# Costs verified: all craftable items have positive profit margin
RECIPES: list[tuple[str, int, list[tuple[str, int]]]] = [
    # Grand tier — cheap entry-level crafting
    ("Iron Crossbow",   1, [("Ethereal Dust", 3)]),                           # cost 11400, profit 2600
    ("Iron Helm",       1, [("Ethereal Dust", 2)]),                           # cost 7600,  profit 1900
    ("Health Potion (L)", 10, [("Ethereal Dust", 2)]),                        # cost 7600 → 10 pots, profit 4400

    # Rare tier
    ("Shadow Dagger",     1, [("Lapis Lazuli", 2), ("Ethereal Dust", 8)]),    # cost 55400, profit 39600
    ("Ring of Swiftness", 1, [("Lapis Lazuli", 3), ("Ethereal Dust", 5)]),    # cost 56500, profit 15500

    # Arcane tier
    ("Storm Lance",     1, [("Moonstone Shard", 4), ("Lapis Lazuli", 1)]),    # cost 45300, profit 16700
    ("Titan Gauntlets", 1, [("Moonstone Shard", 3), ("Ethereal Dust", 2)]),   # cost 32200, profit 21800

    # Heroic tier
    ("Blazing Sword",   1, [("Dragon Scale", 3), ("Lapis Lazuli", 4)]),       # cost 185000, profit 95000
    ("Aegis Plate",     1, [("Dragon Scale", 2), ("Lapis Lazuli", 3)]),       # cost 127500, profit 67500
    ("Amulet of Power", 1, [("Dragon Scale", 1), ("Moonstone Shard", 2), ("Lapis Lazuli", 3)]),  # cost 98900, profit 51100

    # Unique tier — tight margin
    ("Abyssal Bow",     1, [("Void Crystal", 2), ("Dragon Scale", 2), ("Moonstone Shard", 5)]),  # cost 371000, profit 9000

    # Celestial — nested crafting: Ring of Swiftness (itself craftable) is an ingredient
    ("Celestial Earring", 1, [("Ring of Swiftness", 1), ("Void Crystal", 2), ("Dragon Scale", 1)]),  # cost 357000, profit 593000
]


def make_price_history(item_id: int, current_price: int, days: int = 30) -> list[PricePoint]:
    points = []
    now = utcnow()
    price = current_price
    for d in range(days, 0, -1):
        for hour in [6, 12, 18, 23]:
            jitter = random.uniform(-0.04, 0.04)
            price = max(1, int(price * (1 + jitter)))
            captured = now - timedelta(days=d) + timedelta(hours=hour)
            points.append(PricePoint(
                item_id=item_id,
                source="market",
                price=price,
                captured_at=captured,
            ))
    return points


async def seed():
    engine = create_async_engine(settings.async_database_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        # ── Items ──────────────────────────────────────────────────────────
        existing_items = await session.exec(select(Item).limit(1))
        if existing_items.first() is None:
            print(f"Seeding {len(ITEMS)} items with 30 days of price history...")
            random.seed(42)

            for name, category, grade, price in ITEMS:
                item = Item(name=name, category=category, grade=grade, current_price=price)
                session.add(item)
                await session.flush()
                for point in make_price_history(item.id, price):
                    session.add(point)

            await session.commit()
            print(f"  ✓ {len(ITEMS)} items inserted")
        else:
            print("Items already seeded — skipping items.")

        # ── Recipes ────────────────────────────────────────────────────────
        existing_recipes = await session.exec(select(Recipe).limit(1))
        if existing_recipes.first() is None:
            print(f"Seeding {len(RECIPES)} crafting recipes...")

            # Build name→id lookup
            all_items_result = await session.exec(select(Item))
            name_to_id = {item.name: item.id for item in all_items_result.all()}

            for output_name, output_qty, ingredients in RECIPES:
                output_id = name_to_id.get(output_name)
                if output_id is None:
                    print(f"  ! Item not found: {output_name!r} — skipping recipe")
                    continue

                recipe = Recipe(item_id=output_id, output_qty=output_qty)
                session.add(recipe)
                await session.flush()

                for ing_name, qty in ingredients:
                    ing_id = name_to_id.get(ing_name)
                    if ing_id is None:
                        print(f"  ! Ingredient not found: {ing_name!r} — skipping")
                        continue
                    session.add(RecipeIngredient(
                        recipe_id=recipe.id,
                        ingredient_item_id=ing_id,
                        quantity=qty,
                    ))

            await session.commit()
            print(f"  ✓ {len(RECIPES)} recipes inserted")
        else:
            print("Recipes already seeded — skipping recipes.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
