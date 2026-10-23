from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.admin.setup import setup_admin
from app.auth.oauth import oauth_callback_error_handler
from app.auth.router import router as auth_router
from app.imports.router import router as imports_router
from app.inventory.router import router as inventory_router
from httpx_oauth.integrations.fastapi import OAuth2AuthorizeCallbackError
from app.core.errors import register_exception_handlers
from app.core.rate_limit import limiter
from app.core.settings import settings
from app.market.router import router as market_router


_is_prod = settings.environment == "prod"

app = FastAPI(
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url=None if _is_prod else "/openapi.json",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.add_exception_handler(OAuth2AuthorizeCallbackError, oauth_callback_error_handler)

# All API routes live under /api — admin stays at /admin (sqladmin)
api = APIRouter(prefix="/api")
api.include_router(auth_router)
api.include_router(market_router)
api.include_router(imports_router)
api.include_router(inventory_router)
app.include_router(api)

setup_admin(app)
