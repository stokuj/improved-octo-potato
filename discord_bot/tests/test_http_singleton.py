from cogs._http import get_http_client


def test_get_http_client_returns_same_instance():
    a = get_http_client()
    b = get_http_client()
    assert a is b
