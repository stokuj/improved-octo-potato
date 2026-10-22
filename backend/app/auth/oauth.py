# Google OAuth client: verified primary email only.
import logging

from httpx_oauth.clients.google import GoogleOAuth2
from httpx_oauth.exceptions import GetProfileError

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
            status = e.response.status_code if e.response is not None else None
            log.warning("Google profile request failed (status %s): %s", status, body)
            return "", None
        primary = next(
            (
                e
                for e in profile.get("emailAddresses", [])
                if e.get("metadata", {}).get("primary")
            ),
            None,
        )
        if primary is None or not primary.get("metadata", {}).get("verified"):
            return profile.get("resourceName", ""), None
        return profile["resourceName"], primary["value"]


google_client = (
    VerifiedGoogleOAuth2(settings.google_client_id, settings.google_client_secret)
    if settings.google_client_id and settings.google_client_secret
    else None
)
