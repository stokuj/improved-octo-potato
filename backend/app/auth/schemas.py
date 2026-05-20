import uuid
from typing import Any

from fastapi_users import schemas as fu_schemas
from pydantic import model_serializer


class UserRead(fu_schemas.BaseUser[uuid.UUID]):
    @model_serializer(mode="wrap")
    def _hide_internal_flags(self, handler: Any) -> dict[str, Any]:
        d = handler(self)
        d.pop("is_superuser", None)
        d.pop("is_active", None)
        d.pop("is_verified", None)
        return d


class UserCreate(fu_schemas.BaseUserCreate):
    pass


class UserUpdate(fu_schemas.BaseUserUpdate):
    pass
