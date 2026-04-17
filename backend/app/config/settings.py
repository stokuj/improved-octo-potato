from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "sqlite:///./app.db"
    async_database_url: str = "sqlite+aiosqlite:///./app.db"
    auth_secret: str = Field(...)  # No default, required
    sql_echo: bool = True

    @field_validator("auth_secret")
    @classmethod
    def validate_auth_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("AUTH_SECRET must be at least 32 characters long")
        if v == "zmien-na-losowy-string":
            raise ValueError("AUTH_SECRET must be changed from the default value")
        return v


settings = Settings()
