import uuid

from sqlmodel import Field, SQLModel, UniqueConstraint


class UserInventory(SQLModel, table=True):
    __tablename__ = "userinventory"
    __table_args__ = (UniqueConstraint("user_id", "item_id", name="uq_user_inventory"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    item_id: int = Field(foreign_key="item.id", index=True)
    quantity: int = Field(ge=0)
