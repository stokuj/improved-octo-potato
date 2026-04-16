import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    is_private: bool
    display_name: str | None = None
    avatar_url: str | None = None
    created_at: datetime
    updated_at: datetime


class ProfileUpdate(BaseModel):
    is_private: bool | None = None
    display_name: str | None = None
    avatar_url: str | None = None
