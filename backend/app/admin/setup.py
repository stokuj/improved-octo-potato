# Registers sqladmin views.
from fastapi import FastAPI
from sqladmin import Admin
from starlette.requests import Request
from starlette.responses import Response

from app.admin.auth import sign_in_redirect, authentication_backend
from app.core.db import engine
from app.market.admin import ItemAdmin, ListingAdmin, MarketDayAdmin
from app.auth.admin import UserAdmin


class AppAdmin(Admin):
    async def login(self, request: Request) -> Response:
        # Signing in happens on the frontend; never show sqladmin's password form.
        return sign_in_redirect()


def setup_admin(app: FastAPI) -> Admin:
    admin = AppAdmin(app, engine, authentication_backend=authentication_backend)
    admin.add_view(ItemAdmin)
    admin.add_view(MarketDayAdmin)
    admin.add_view(ListingAdmin)
    admin.add_view(UserAdmin)
    return admin
