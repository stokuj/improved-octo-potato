import pytest

from cogs import _http


@pytest.fixture(autouse=True)
def _reset_http_singleton():
    _http._client = None
    yield
    _http._client = None
