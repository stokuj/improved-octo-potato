from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.admin import setup_admin
from app.auth.router import router as auth_router
from app.config.db import create_db
from app.config.exceptions import register_exception_handlers
from app.items.router import router as items_router
from app.prices.router import router as prices_router
from app.profiles.router import router as profiles_router
from app.user_items.router import router as user_items_router
from app.users.router import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db()
    yield


app = FastAPI(lifespan=lifespan)

# Konfiguracja CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(profiles_router)
app.include_router(items_router)
app.include_router(prices_router)
app.include_router(user_items_router)
setup_admin(app)
