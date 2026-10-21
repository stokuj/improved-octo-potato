from fastapi.testclient import TestClient

from app.main import app


def test_openapi_user_read_matches_runtime():
    client = TestClient(app)
    spec = client.get("/openapi.json").json()
    user_read = spec["components"]["schemas"]["UserRead"]["properties"]
    for stripped in ("is_superuser", "is_active", "is_verified"):
        assert stripped not in user_read, f"{stripped} leaked into OpenAPI"
    assert "email" in user_read
    assert "id" in user_read
