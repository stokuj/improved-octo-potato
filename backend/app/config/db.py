from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config.settings import settings

DATABASE_URL = settings.database_url
ASYNC_DATABASE_URL = settings.async_database_url

engine = create_engine(DATABASE_URL, echo=settings.sql_echo)
async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=settings.sql_echo)
async_session_maker = async_sessionmaker(
    async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
