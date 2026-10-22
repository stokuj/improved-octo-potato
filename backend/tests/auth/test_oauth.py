import uuid
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from httpx_oauth.exceptions import GetProfileError
from httpx_oauth.oauth2 import OAuth2Token
from sqlmodel import select

from app.auth.models import User
from app.auth.oauth import google_client
from app.main import app


def fake_google(
    monkeypatch, *, email: str, verified: bool = True, profile_error: bool = False
):
    async def get_access_token(code, redirect_uri, code_verifier=None):
        return OAuth2Token({"access_token": "t", "expires_in": 3600})

    async def get_profile(token):
        if profile_error:
            raise GetProfileError(response=httpx.Response(403))
        return {
            "resourceName": "people/1",
            "emailAddresses": [
                {"value": email, "metadata": {"primary": True, "verified": verified}}
            ],
        }

    monkeypatch.setattr(google_client, "get_access_token", get_access_token)
    monkeypatch.setattr(google_client, "get_profile", get_profile)


async def authorize_state(c: AsyncClient) -> str:
    r = await c.get("/api/auth/google/authorize")
    assert r.status_code == 200, r.text
    return parse_qs(urlparse(r.json()["authorization_url"]).query)["state"][0]


async def google_login(c: AsyncClient) -> httpx.Response:
    state = await authorize_state(c)
    return await c.get(f"/api/auth/google/callback?code=x&state={state}")


async def test_authorize_returns_google_url(client):
    r = await client.get("/api/auth/google/authorize")
    assert r.status_code == 200
    url = r.json()["authorization_url"]
    assert url.startswith("https://accounts.google.com/")
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A5173%2Fauth%2Fcallback" in url
    assert "fastapiusersoauthcsrf" in r.cookies


async def test_google_login_existing_superuser(client, make_user, monkeypatch):
    user, _ = await make_user(superuser=True)
    fake_google(monkeypatch, email=user.email)
    r = await google_login(client)
    assert r.status_code == 204, r.text
    assert "fastapiusersauth" in r.cookies
    me = await client.get("/api/users/me")
    assert me.status_code == 200
    assert me.json()["email"] == user.email


async def test_google_login_email_case_insensitive(client, make_user, monkeypatch):
    user, _ = await make_user(
        email=f"Mixed-{uuid.uuid4().hex[:8]}@Example.com", superuser=True
    )
    fake_google(monkeypatch, email=user.email.lower())
    r = await google_login(client)
    assert r.status_code == 204, r.text


async def test_google_login_unknown_email_refused(client, session, monkeypatch):
    email = f"nobody-{uuid.uuid4().hex[:8]}@example.com"
    fake_google(monkeypatch, email=email)
    r = await google_login(client)
    assert r.status_code == 400
    assert r.json()["detail"] == "LOGIN_BAD_CREDENTIALS"
    assert (await session.exec(select(User).where(User.email == email))).first() is None


async def test_google_login_non_superuser_refused(client, make_user, monkeypatch):
    user, _ = await make_user(superuser=False)
    fake_google(monkeypatch, email=user.email)
    r = await google_login(client)
    assert r.status_code == 400
    assert r.json()["detail"] == "LOGIN_BAD_CREDENTIALS"


async def test_google_login_inactive_refused(client, make_user, session, monkeypatch):
    user, _ = await make_user(superuser=True)
    user.is_active = False
    session.add(user)
    await session.commit()
    fake_google(monkeypatch, email=user.email)
    r = await google_login(client)
    assert r.status_code == 400
    assert r.json()["detail"] == "LOGIN_BAD_CREDENTIALS"


@pytest.mark.parametrize("kwargs", [{"verified": False}, {"profile_error": True}])
async def test_google_without_verified_email_refused(
    client, make_user, monkeypatch, kwargs
):
    # Covers both an unverified primary email and a failing People API call.
    user, _ = await make_user(superuser=True)
    fake_google(monkeypatch, email=user.email, **kwargs)
    r = await google_login(client)
    assert r.status_code == 400
    assert r.json()["detail"] == "OAUTH_NOT_AVAILABLE_EMAIL"


async def test_google_callback_without_csrf_cookie_refused(
    client, make_user, monkeypatch
):
    user, _ = await make_user(superuser=True)
    fake_google(monkeypatch, email=user.email)
    state = await authorize_state(client)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as fresh:
        r = await fresh.get(f"/api/auth/google/callback?code=x&state={state}")
    assert r.status_code == 400
    assert r.json()["detail"] == "OAUTH_INVALID_STATE"


async def test_email_without_metadata_is_not_verified(monkeypatch):
    from app.auth.oauth import VerifiedGoogleOAuth2

    client = VerifiedGoogleOAuth2("id", "secret")

    async def get_profile(token):
        return {
            "resourceName": "people/1",
            "emailAddresses": [{"value": "x@example.com"}],
        }

    monkeypatch.setattr(client, "get_profile", get_profile)
    assert await client.get_id_email("t") == ("people/1", None)


async def test_profile_error_logs_google_reason(monkeypatch, caplog):
    from app.auth.oauth import VerifiedGoogleOAuth2

    client = VerifiedGoogleOAuth2("id", "secret")

    async def get_profile(token):
        raise GetProfileError(
            response=httpx.Response(
                403, text="People API has not been used in project 1"
            )
        )

    monkeypatch.setattr(client, "get_profile", get_profile)
    assert await client.get_id_email("t") == ("", None)
    assert "People API has not been used" in caplog.text
