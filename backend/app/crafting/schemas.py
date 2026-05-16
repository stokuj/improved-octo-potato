from pydantic import BaseModel, Field, field_validator


class CalculateRequest(BaseModel):
    multiplier: int = Field(default=1, ge=1, le=10_000)
    inventory: dict[int, int] = Field(default_factory=dict, max_length=500)

    @field_validator("inventory")
    @classmethod
    def inventory_values_non_negative(cls, v: dict[int, int]) -> dict[int, int]:
        if any(qty < 0 for qty in v.values()):
            raise ValueError("inventory quantities must be non-negative")
        return v


class CraftNode(BaseModel):
    item_id: int
    item_name: str
    qty_needed: int
    unit_price: int | None
    total_cost: int
    can_craft: bool
    crafts_possible: int | None
    ingredients: list["CraftNode"] = []


CraftNode.model_rebuild()


class CraftResult(BaseModel):
    item_id: int
    item_name: str
    output_qty: int
    multiplier: int
    market_price: int | None
    profit_per_craft: int | None
    total_material_cost: int
    has_missing_prices: bool  # True if any ingredient has current_price=None
    ingredients: list[CraftNode]


class CraftSummary(BaseModel):
    item_id: int
    item_name: str
    output_qty: int
    total_material_cost: int
    market_price: int | None
    profit_per_craft: int | None
