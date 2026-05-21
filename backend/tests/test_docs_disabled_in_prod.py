"""Verify that /docs, /redoc and /openapi.json are 404 when ENVIRONMENT=prod.

The settings `environment` field is added in Task 0.6; this test uses an env-var
override and reloads the settings + main modules so it works whether or not the
field exists on Settings (uses getattr fallback to "dev").
"""

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_docs_404_in_prod(monkeypatch, path):
    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setenv("AUTH_SECRET", "a" * 40)
    monkeypatch.setenv("ADMIN_SESSION_SECRET", "b" * 40)
    monkeypatch.setenv("RESET_TOKEN_SECRET", "r" * 40)
    monkeypatch.setenv("VERIFICATION_TOKEN_SECRET", "v" * 40)
    monkeypatch.setenv("INGEST_TOKEN", "i" * 40)
    import app.config.settings as s

    importlib.reload(s)
    import app.main as m

    importlib.reload(m)
    client = TestClient(m.app)
    assert client.get(path).status_code == 404
