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
    admin_session_secret: str = "temporary-admin-session-secret-must-be-32-chars"
    cookie_secure: bool = False
    sql_echo: bool = False
    # Env format: JSON array string, e.g., '["http://localhost:3000"]'
    # Pydantic-settings automatically parses JSON arrays from env vars
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    @field_validator("auth_secret", "admin_session_secret")
    @classmethod
    def validate_secrets(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("Secret must be at least 32 characters long")
        return v


settings = Settings()
