import importlib

import pytest
from pydantic import ValidationError


_SECRET_ENV_KEYS = (
    "AUTH_SECRET",
    "ADMIN_SESSION_SECRET",
    "RESET_TOKEN_SECRET",
    "VERIFICATION_TOKEN_SECRET",
    "INGEST_TOKEN",
    "ENVIRONMENT",
)


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    """Run each test from an empty cwd with no secret env vars — validator sees
    only what the test passes in as kwargs."""
    monkeypatch.chdir(tmp_path)
    for k in _SECRET_ENV_KEYS:
        monkeypatch.delenv(k, raising=False)
    # Reload so a previous import doesn't keep stale env-derived state
    import app.config.settings as s

    importlib.reload(s)


def test_default_secrets_rejected_when_environment_is_prod(clean_env):
    from app.config.settings import Settings

    with pytest.raises(ValidationError) as exc:
        Settings(environment="prod")  # all secret fields fall back to defaults
    msg = str(exc.value).lower()
    assert "default" in msg or "must be set" in msg


def test_secrets_must_be_32_chars(clean_env):
    from app.config.settings import Settings

    with pytest.raises(ValidationError):
        Settings(environment="dev", auth_secret="too-short")


def test_auth_reset_verify_secrets_must_differ(clean_env):
    from app.config.settings import Settings

    same = "x" * 40
    with pytest.raises(ValidationError):
        Settings(
            environment="prod",
            auth_secret=same,
            admin_session_secret="a" * 40,
            reset_token_secret=same,
            verification_token_secret="v" * 40,
            ingest_token="i" * 40,
        )
