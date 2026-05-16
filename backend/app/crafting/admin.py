from sqladmin import ModelView

from app.crafting.models import Recipe, RecipeIngredient


class RecipeAdmin(ModelView, model=Recipe):
    name = "Recipe"
    name_plural = "Recipes"
    icon = "fa-solid fa-scroll"

    can_create = False
    can_edit = False
    can_delete = False

    column_list = [Recipe.id, Recipe.item_id, Recipe.output_qty]
    column_sortable_list = [Recipe.id, Recipe.item_id]


class RecipeIngredientAdmin(ModelView, model=RecipeIngredient):
    name = "Recipe Ingredient"
    name_plural = "Recipe Ingredients"
    icon = "fa-solid fa-list"

    can_create = False
    can_edit = False
    can_delete = False

    column_list = [
        RecipeIngredient.id,
        RecipeIngredient.recipe_id,
        RecipeIngredient.ingredient_item_id,
        RecipeIngredient.quantity,
    ]
    column_sortable_list = [RecipeIngredient.recipe_id, RecipeIngredient.ingredient_item_id]
