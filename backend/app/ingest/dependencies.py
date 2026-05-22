import hmac

from fastapi import Header, HTTPException, status

from app.config.settings import settings


async def verify_ingest_token(authorization: str | None = Header(default=None)) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(token, settings.ingest_token):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid ingest token")
