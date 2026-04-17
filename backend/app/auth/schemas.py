import uuid

from fastapi_users import schemas as fu_schemas


class UserRead(fu_schemas.BaseUser[uuid.UUID]):
    def model_dump(self, **kwargs):
        d = super().model_dump(**kwargs)
        # Hide sensitive flags in public API
        d.pop("is_superuser", None)
        d.pop("is_active", None)
        d.pop("is_verified", None)
        return d


class UserCreate(fu_schemas.BaseUserCreate):
    pass


class UserUpdate(fu_schemas.BaseUserUpdate):
    pass
