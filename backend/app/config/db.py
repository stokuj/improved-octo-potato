from collections.abc import AsyncGenerator, Generator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, Session, create_engine

from app.config.settings import settings

DATABASE_URL = settings.database_url
ASYNC_DATABASE_URL = settings.async_database_url

engine = create_engine(DATABASE_URL, echo=settings.sql_echo)
async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=settings.sql_echo)
async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False)


def create_db() -> None:
    from app.items import models as items_models  # noqa: F401
    from app.users import models as users_models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
