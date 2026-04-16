import uuid

from fastapi_users import schemas as fu_schemas


class UserRead(fu_schemas.BaseUser[uuid.UUID]):
    pass


class UserCreate(fu_schemas.BaseUserCreate):
    pass


class UserUpdate(fu_schemas.BaseUserUpdate):
    pass
