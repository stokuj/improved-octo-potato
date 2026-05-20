from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config.db import get_async_session
from app.items.models import ItemCategory, ItemGrade
from app.items.schemas import ItemRead, PaginatedItems
from app.items import services


router = APIRouter(prefix="/items", tags=["items"])


@router.get("/", response_model=PaginatedItems)
async def read_items(
    q: str | None = Query(default=None, max_length=200),
    category: ItemCategory | None = Query(default=None),
    grade: ItemGrade | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    session: AsyncSession = Depends(get_async_session),
) -> PaginatedItems:
    return await services.get_items(
        session=session,
        q=q,
        category=category,
        grade=grade,
        offset=offset,
        limit=limit,
    )


@router.get("/{item_id}", response_model=ItemRead)
async def read_item(
    item_id: int, session: AsyncSession = Depends(get_async_session)
) -> ItemRead:
    item = await services.get_item(session, item_id)
    return ItemRead(
        id=item.id,
        name=item.name,
        category=item.category,
        grade=item.grade,
        current_price=item.current_price,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
