# Google OAuth client: verified primary email only.
import logging

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from httpx_oauth.clients.google import GoogleOAuth2
from httpx_oauth.exceptions import GetProfileError
from httpx_oauth.integrations.fastapi import OAuth2AuthorizeCallbackError

from app.core.settings import settings

log = logging.getLogger(__name__)


class VerifiedGoogleOAuth2(GoogleOAuth2):
    async def get_id_email(self, token: str) -> tuple[str, str | None]:
        # The email is the only link to an account, so an unverified one is no email.
        # Returning None makes fastapi-users answer 400 OAUTH_NOT_AVAILABLE_EMAIL.
        try:
            profile = await self.get_profile(token)
        except GetProfileError as e:
            # Body says why, e.g. "People API has not been used in project …".
            body = e.response.text[:300] if e.response is not None else ""
            code = e.response.status_code if e.response is not None else None
            log.warning("Google profile request failed (status %s): %s", code, body)
            # Not the user's email: usually the People API is disabled in the project.
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GOOGLE_PROFILE_UNAVAILABLE",
            ) from e
        primary = next(
            (
                addr
                for addr in profile.get("emailAddresses", [])
                if addr.get("metadata", {}).get("primary")
            ),
            None,
        )
        if primary is None or not primary.get("metadata", {}).get("verified"):
            return profile.get("resourceName", ""), None
        return profile["resourceName"], primary["value"]


async def oauth_callback_error_handler(
    request: Request, exc: OAuth2AuthorizeCallbackError
) -> JSONResponse:
    """httpx-oauth answers a failed code exchange (a reused code after a reload, a
    wrong client secret) with 500 and Google's raw text; log that, send a code."""
    if exc.status_code < 500:  # e.g. ?error=access_denied when consent is cancelled
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    log.warning("Google code exchange failed: %s", exc.detail)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "OAUTH_CODE_EXCHANGE_FAILED"},
    )


google_client = (
    VerifiedGoogleOAuth2(settings.google_client_id, settings.google_client_secret)
    if settings.google_client_id and settings.google_client_secret
    else None
)
