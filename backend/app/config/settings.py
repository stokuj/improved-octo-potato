from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/app"
    async_database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/app"
    )
    auth_secret: str = "temporary-development-secret-must-be-32-chars"
    sql_echo: bool = False

    @field_validator("auth_secret")
    @classmethod
    def validate_auth_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("AUTH_SECRET must be at least 32 characters long")
        if v == "zmien-na-losowy-string":
            raise ValueError("AUTH_SECRET must be changed from the default value")
        return v


settings = Settings()
