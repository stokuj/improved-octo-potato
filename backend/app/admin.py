from fastapi import FastAPI
from sqladmin import Admin

from app.config.db import engine
from app.items.admin import ItemAdmin
from app.users.admin import UserAdmin


def setup_admin(app: FastAPI) -> Admin:
    admin = Admin(app, engine)
    admin.add_view(ItemAdmin)
    admin.add_view(UserAdmin)
    return admin
