from app.items.models import ItemGrade

# Integer grades used by the ingest API (0 = Basic, 1-6 = game grades, 7-11 = high-end).
GAME_GRADE_TO_ENUM: dict[int, ItemGrade] = {
    0: ItemGrade.BASIC,
    1: ItemGrade.GRAND,
    2: ItemGrade.RARE,
    3: ItemGrade.ARCANE,
    4: ItemGrade.HEROIC,
    5: ItemGrade.UNIQUE,
    6: ItemGrade.CELESTIAL,
    7: ItemGrade.DIVINE,
    8: ItemGrade.EPIC,
    9: ItemGrade.LEGENDARY,
    10: ItemGrade.MYTHIC,
    11: ItemGrade.ETERNAL,
}


def map_grade(game_grade: int) -> ItemGrade | None:
    return GAME_GRADE_TO_ENUM.get(game_grade)
