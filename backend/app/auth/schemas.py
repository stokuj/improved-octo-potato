import uuid

from fastapi_users import schemas as fu_schemas
from pydantic import BaseModel, ConfigDict, EmailStr


class UserRead(BaseModel):
    """Hand-rolled so is_active / is_verified stay out of the API.

    is_superuser is exposed: it is the caller's own flag and the frontend uses
    it to show the import page. Subclassing ``BaseUser`` would leak the rest.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    is_superuser: bool


class UserUpdate(fu_schemas.CreateUpdateDictModel):
    """BaseUserUpdate without ``email``: in prod the email is the Google sign-in
    key, so changing it would lock the owner out. fastapi-users already ignores
    the flags on /users/me (safe update); superusers may set them on /users/{id}."""

    model_config = ConfigDict(extra="forbid")

    password: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
    is_verified: bool | None = None
