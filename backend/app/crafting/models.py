from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Recipe(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    item_id: int = Field(foreign_key="item.id", unique=True, index=True)
    output_qty: int = Field(ge=1)


class RecipeIngredient(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("recipe_id", "ingredient_item_id", name="uq_recipe_ingredient"),)

    id: int | None = Field(default=None, primary_key=True)
    recipe_id: int = Field(foreign_key="recipe.id", index=True)
    ingredient_item_id: int = Field(foreign_key="item.id", index=True)
    quantity: int = Field(ge=1)
