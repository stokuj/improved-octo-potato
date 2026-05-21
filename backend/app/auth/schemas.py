import uuid

from fastapi_users import schemas as fu_schemas
from pydantic import BaseModel, ConfigDict, EmailStr


class UserRead(BaseModel):
    """Hand-rolled to suppress is_active / is_verified / is_superuser leakage.

    fastapi-users only needs ``response_model`` to be a valid pydantic schema; it does
    not require subclassing ``BaseUser``. Inheriting from ``BaseUser`` previously
    caused those internal flags to appear in the generated OpenAPI spec even though
    a ``@model_serializer`` stripped them at runtime, producing client/server drift.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr


class UserCreate(fu_schemas.BaseUserCreate):
    pass


class UserUpdate(fu_schemas.BaseUserUpdate):
    pass
