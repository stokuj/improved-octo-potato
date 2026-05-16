from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.admin import setup_admin
from app.auth.router import router as auth_router
from app.config.exceptions import register_exception_handlers
from app.config.settings import settings
from app.items.router import router as items_router
from app.prices.router import router as prices_router
from app.profiles.router import router as profiles_router
from app.crafting.router import router as crafting_router
from app.user_items.router import router as user_items_router
from app.users.router import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

# All API routes live under /api — admin stays at /admin (sqladmin)
api = APIRouter(prefix="/api")
api.include_router(auth_router)
api.include_router(users_router)
api.include_router(profiles_router)
api.include_router(items_router)
api.include_router(prices_router)
api.include_router(user_items_router)
api.include_router(crafting_router)
app.include_router(api)

setup_admin(app)
