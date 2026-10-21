def test_session_lasts_seven_days():
    from app.auth.backend import SESSION_SECONDS, cookie_transport, get_jwt_strategy

    assert SESSION_SECONDS == 604800
    assert cookie_transport.cookie_max_age == 604800
    assert get_jwt_strategy().lifetime_seconds == 604800
