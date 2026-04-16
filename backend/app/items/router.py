from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.config.db import get_session
from app.config.exceptions import NotFoundError
from app.items.models import Item
from app.items.schemas import ItemCreate, ItemRead, ItemUpdate

router = APIRouter(prefix="/items", tags=["items"])


@router.post("/", response_model=ItemRead)
def create_item(item_in: ItemCreate, session: Session = Depends(get_session)) -> Item:
    item = Item(**item_in.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.get("/", response_model=list[ItemRead])
def read_items(session: Session = Depends(get_session)) -> list[Item]:
    return session.exec(select(Item)).all()


@router.get("/{item_id}", response_model=ItemRead)
def read_item(item_id: int, session: Session = Depends(get_session)) -> Item:
    item = session.get(Item, item_id)
    if not item:
        raise NotFoundError()
    return item


@router.patch("/{item_id}", response_model=ItemRead)
def update_item(
    item_id: int, item_in: ItemUpdate, session: Session = Depends(get_session)
) -> Item:
    item = session.get(Item, item_id)
    if not item:
        raise NotFoundError()

    updates = item_in.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(item, field, value)

    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: int, session: Session = Depends(get_session)) -> None:
    item = session.get(Item, item_id)
    if not item:
        raise NotFoundError()

    session.delete(item)
    session.commit()
