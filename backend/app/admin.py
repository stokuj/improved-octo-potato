from fastapi import FastAPI
from sqladmin import Admin

from app.admin_auth import authentication_backend
from app.config.db import engine
from app.crafting.admin import RecipeAdmin, RecipeIngredientAdmin
from app.items.admin import ItemAdmin
from app.prices.admin import PricePointAdmin
from app.users.admin import UserAdmin


def setup_admin(app: FastAPI) -> Admin:
    admin = Admin(app, engine, authentication_backend=authentication_backend)
    admin.add_view(ItemAdmin)
    admin.add_view(PricePointAdmin)
    admin.add_view(RecipeAdmin)
    admin.add_view(RecipeIngredientAdmin)
    admin.add_view(UserAdmin)
    return admin
