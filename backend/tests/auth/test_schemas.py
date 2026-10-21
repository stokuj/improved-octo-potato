from fastapi.testclient import TestClient

from app.main import app


def test_openapi_user_read_matches_runtime():
    client = TestClient(app)
    spec = client.get("/openapi.json").json()
    user_read = spec["components"]["schemas"]["UserRead"]["properties"]
    assert set(user_read) == {"id", "email", "is_superuser"}
