"""Seed the database with ArcheRage crafting items and the Blazing Sunridge Ingot recipe tree."""

import asyncio
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config.settings import settings
from app.crafting.models import Recipe, RecipeIngredient
from app.items.models import Item, ItemCategory, ItemGrade
from app.prices.models import PricePoint


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# (name, base_price) — items to seed price history for (copper values)
# Approximate ArcheRage market prices; Labour has no market price
PRICE_SEEDS: list[tuple[str, int]] = [
    ("Iron Ore", 15),
    ("Copper Ore", 20),
    ("Silver Ore", 25),
    ("Onyx Archeum Essence", 150),
    ("Azalea", 8),
    ("Narcissus", 8),
    ("Mysterious Garden Powder", 500),
    ("Lotus", 12),
    ("Oats", 10),
    ("Antler Coral", 30),
    ("Anya Pebble", 40),
    ("Dragon Essence Stabilizer", 800),
    ("Flaming Log", 200),
    ("Sunpoint", 1200),
    ("Turmeric", 6),
    ("Cactus", 6),
    ("Sparkling Shell Dust", 90),
    ("Beechnut", 15),
    ("Iron Ingot", 50),
    ("Copper Ingot", 65),
    ("Silver Ingot", 80),
    ("Opaque Polish", 450),
    ("Sturdy Ingot", 1200),
    ("Rough Polish", 2000),
    ("Anya Ingot", 130),
    ("Sunridge Ingot", 9000),
    ("Rainbow Polish", 4500),
    ("Blazing Sunridge Ingot", 21450),
]


def _price_history(
    base: int, seed: int, days: int = 30, points_per_day: int = 4
) -> list[tuple[datetime, int]]:
    """Generate price history with realistic random walk (±8% per step)."""
    rng = random.Random(seed)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    step = timedelta(hours=24 // points_per_day)
    total = days * points_per_day
    result = []
    price = base
    for i in range(total, 0, -1):
        ts = now - step * i
        noise = rng.uniform(-0.08, 0.08)
        price = max(1, round(price * (1 + noise)))
        result.append((ts, price))
    return result


# (name, category, grade)
# current_price=None — prices come in via the ingest pipeline
ITEMS: list[tuple[str, ItemCategory, ItemGrade]] = [
    # ── Leaf nodes (raw materials / purchased) ──────────────────────────────
    ("Iron Ore", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Copper Ore", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Silver Ore", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Onyx Archeum Essence", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Azalea", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Narcissus", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Labour", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Mysterious Garden Powder", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Lotus", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Oats", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Antler Coral", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Anya Pebble", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Dragon Essence Stabilizer", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Flaming Log", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Sunpoint", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Turmeric", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Cactus", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Sparkling Shell Dust", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Beechnut", ItemCategory.CRAFTING, ItemGrade.BASIC),
    # ── Crafted intermediates ───────────────────────────────────────────────
    ("Iron Ingot", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Copper Ingot", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Silver Ingot", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Opaque Polish", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Sturdy Ingot", ItemCategory.CRAFTING, ItemGrade.GRAND),
    ("Rough Polish", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Anya Ingot", ItemCategory.CRAFTING, ItemGrade.BASIC),
    ("Sunridge Ingot", ItemCategory.CRAFTING, ItemGrade.GRAND),
    ("Rainbow Polish", ItemCategory.CRAFTING, ItemGrade.GRAND),
    # ── Final product ───────────────────────────────────────────────────────
    ("Blazing Sunridge Ingot", ItemCategory.CRAFTING, ItemGrade.RARE),
]

# (output_item, output_qty, [(ingredient_item, qty), ...])
# Quantities are per single craft run.
# Sunridge Ingot: output=10 derived from tree ratios (80 needed / 8 crafts).
RECIPES: list[tuple[str, int, list[tuple[str, int]]]] = [
    ("Iron Ingot", 1, [("Iron Ore", 3)]),
    ("Copper Ingot", 1, [("Copper Ore", 3)]),
    ("Silver Ingot", 1, [("Silver Ore", 3)]),
    (
        "Opaque Polish",
        1,
        [
            ("Onyx Archeum Essence", 3),
            ("Azalea", 20),
            ("Narcissus", 20),
            ("Labour", 15),
        ],
    ),
    (
        "Sturdy Ingot",
        1,
        [
            ("Iron Ingot", 8),
            ("Copper Ingot", 1),
            ("Silver Ingot", 1),
            ("Opaque Polish", 1),
            ("Labour", 10),
        ],
    ),
    (
        "Rough Polish",
        1,
        [
            ("Onyx Archeum Essence", 5),
            ("Lotus", 30),
            ("Oats", 30),
            ("Antler Coral", 20),
            ("Labour", 30),
        ],
    ),
    ("Anya Ingot", 1, [("Anya Pebble", 3)]),
    # output=10 per craft; 8 crafts → 80 Sunridge Ingots needed by parent
    (
        "Sunridge Ingot",
        10,
        [
            ("Sturdy Ingot", 100),
            ("Mysterious Garden Powder", 50),
            ("Rough Polish", 10),
            ("Labour", 300),
            ("Anya Ingot", 9),
            ("Dragon Essence Stabilizer", 25),
            ("Flaming Log", 6),
        ],
    ),
    (
        "Rainbow Polish",
        1,
        [
            ("Dragon Essence Stabilizer", 3),
            ("Turmeric", 50),
            ("Cactus", 50),
            ("Sparkling Shell Dust", 10),
            ("Beechnut", 10),
        ],
    ),
    (
        "Blazing Sunridge Ingot",
        8,
        [
            ("Sunridge Ingot", 80),
            ("Sunpoint", 50),
            ("Rainbow Polish", 15),
            ("Labour", 500),
        ],
    ),
]


async def seed(session: AsyncSession) -> None:
    # ── Items ────────────────────────────────────────────────────────────────
    existing = {item.name for item in (await session.exec(select(Item))).all()}
    name_to_id: dict[str, int] = {
        item.name: item.id
        for item in (await session.exec(select(Item))).all()
        if item.id is not None
    }

    new_items = [
        Item(name=name, category=cat, grade=grade)
        for name, cat, grade in ITEMS
        if name not in existing
    ]
    if new_items:
        print(f"Seeding {len(new_items)} items...")
        for item in new_items:
            session.add(item)
        await session.flush()
        for item in new_items:
            if item.id is not None:
                name_to_id[item.name] = item.id
        print(f"  ✓ {len(new_items)} items inserted")
    else:
        print("Items already seeded — skipping.")

    # ── Recipes ──────────────────────────────────────────────────────────────
    existing_recipes = await session.exec(select(Recipe).limit(1))
    if existing_recipes.first() is not None:
        print("Recipes already seeded — skipping.")
    else:
        print(f"Seeding {len(RECIPES)} recipes...")
        for output_name, output_qty, ingredients in RECIPES:
            item_id = name_to_id.get(output_name)
            if item_id is None:
                print(f"  ! Item not found: {output_name!r} — skipping")
                continue

            recipe = Recipe(item_id=item_id, output_qty=output_qty)
            session.add(recipe)
            await session.flush()

            for ing_name, qty in ingredients:
                ing_id = name_to_id.get(ing_name)
                if ing_id is None:
                    print(f"  ! Ingredient not found: {ing_name!r} — skipping")
                    continue
                session.add(
                    RecipeIngredient(
                        recipe_id=recipe.id,
                        ingredient_item_id=ing_id,
                        quantity=qty,
                    )
                )

        await session.commit()
        print(f"  ✓ {len(RECIPES)} recipes inserted")

    # ── Price history ─────────────────────────────────────────────────────────
    existing_prices = await session.exec(select(PricePoint).limit(1))
    if existing_prices.first() is not None:
        print("Price history already seeded — skipping.")
        return  # nothing left after this section

    print("Seeding price history (30 days, 4 points/day per item)...")
    total_points = 0
    for item_name, base_price in PRICE_SEEDS:
        item_id = name_to_id.get(item_name)
        if item_id is None:
            continue
        history = _price_history(base_price, seed=item_id)
        last_price = history[-1][1]
        for ts, price in history:
            session.add(
                PricePoint(item_id=item_id, source="ah", price=price, captured_at=ts)
            )
        # Update current_price on the item
        result = await session.exec(select(Item).where(Item.id == item_id))
        db_item = result.first()
        if db_item:
            db_item.current_price = last_price
        total_points += len(history)

    await session.commit()
    print(f"  ✓ {total_points} price points inserted")


async def main() -> None:
    engine = create_async_engine(settings.async_database_url)
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
