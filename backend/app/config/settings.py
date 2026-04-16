from dataclasses import dataclass
import os


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    async_database_url: str = os.getenv(
        "ASYNC_DATABASE_URL", "sqlite+aiosqlite:///./app.db"
    )
    auth_secret: str = os.getenv("AUTH_SECRET", "zmien-na-losowy-string")
    sql_echo: bool = _as_bool(os.getenv("SQL_ECHO"), default=True)


settings = Settings()
