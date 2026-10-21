# Registers sqladmin views.
from fastapi import FastAPI
from sqladmin import Admin

from app.admin.auth import authentication_backend
from app.core.db import engine
from app.items.admin import ItemAdmin
from app.auth.admin import UserAdmin


def setup_admin(app: FastAPI) -> Admin:
    admin = Admin(app, engine, authentication_backend=authentication_backend)
    admin.add_view(ItemAdmin)
    admin.add_view(UserAdmin)
    return admin
