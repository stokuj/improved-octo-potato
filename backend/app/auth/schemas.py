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


class UserUpdate(fu_schemas.BaseUserUpdate):
    pass
