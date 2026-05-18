from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class WatcherSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WATCHER_", env_file=".env", extra="ignore")

    jsonl_path: Path = Path("prices.jsonl")
    state_path: Path = Path(".watcher_state")
    api_url: str = "http://localhost:8000/api/ingest/prices"
    batch_size: int = 100
    poll_interval_seconds: float = 2.0
    request_timeout_seconds: float = 10.0
    backoff_initial_seconds: float = 2.0
    backoff_max_seconds: float = 60.0


def load_settings() -> WatcherSettings:
    return WatcherSettings()
