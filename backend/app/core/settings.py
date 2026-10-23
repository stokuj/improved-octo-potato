# App settings from env/.env, with prod secret checks.
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_DEFAULT_AUTH_SECRET = "temporary-development-secret-must-be-32-chars"
_DEFAULT_ADMIN_SECRET = "temporary-admin-session-secret-must-be-32-chars"
_DEFAULT_RESET_SECRET = "temporary-reset-token-secret-must-be-32-chars-x"
_DEFAULT_VERIFY_SECRET = "temporary-verify-token-secret-must-be-32-chars"

_DEFAULTS = {
    _DEFAULT_AUTH_SECRET,
    _DEFAULT_ADMIN_SECRET,
    _DEFAULT_RESET_SECRET,
    _DEFAULT_VERIFY_SECRET,
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    environment: Literal["dev", "test", "prod"] = "dev"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/app"
    async_database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/app"
    )

    auth_secret: str = _DEFAULT_AUTH_SECRET
    admin_session_secret: str = _DEFAULT_ADMIN_SECRET
    reset_token_secret: str = _DEFAULT_RESET_SECRET
    verification_token_secret: str = _DEFAULT_VERIFY_SECRET

    # Google sign-in; the OAuth router is mounted only when both are set.
    google_client_id: str = ""
    google_client_secret: str = ""
    # Where Google sends the browser back (/auth/callback) and /admin sends anonymous users.
    frontend_url: str = "http://localhost:5173"

    # Item icons fetched from ArcheAge Codex; a volume in compose, never committed.
    icon_cache_dir: str = "/app/icon-cache"

    cookie_secure: bool = False
    sql_echo: bool = False
    log_level: str = "INFO"
    # Env format: JSON array string, e.g., '["http://localhost:3000"]'
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    @field_validator("frontend_url")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        # Used as f"{frontend_url}/auth/callback"; Google rejects "//auth".
        return value.rstrip("/")

    @model_validator(mode="after")
    def _check_secrets(self) -> "Settings":
        secrets = {
            "auth_secret": self.auth_secret,
            "admin_session_secret": self.admin_session_secret,
            "reset_token_secret": self.reset_token_secret,
            "verification_token_secret": self.verification_token_secret,
        }
        for name, value in secrets.items():
            if len(value) < 32:
                raise ValueError(f"{name} must be at least 32 characters long")
        if self.environment == "prod":
            for name, value in secrets.items():
                if value in _DEFAULTS:
                    raise ValueError(
                        f"{name} is using default value — must be set explicitly in prod"
                    )
            if not (self.google_client_id and self.google_client_secret):
                raise ValueError(
                    "google_client_id and google_client_secret are required in prod"
                )
        token_secrets = {
            self.auth_secret,
            self.reset_token_secret,
            self.verification_token_secret,
        }
        if len(token_secrets) != 3:
            raise ValueError(
                "auth_secret, reset_token_secret, verification_token_secret must all differ"
            )
        return self


settings = Settings()
