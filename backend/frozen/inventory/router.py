from fastapi import APIRouter, Depends, Response, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.dependencies import current_user
from app.config.db import get_async_session
from app.user_inventory import services
from app.user_inventory.schemas import InventoryItem, InventoryUpsert
from app.users.models import User

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/", response_model=list[InventoryItem])
async def read_inventory(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[InventoryItem]:
    return await services.get_inventory(session=session, user_id=user.id)


@router.get("/for-recipe/{item_id}", response_model=dict[int, int])
async def get_inventory_for_recipe(
    item_id: int,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
) -> dict[int, int]:
    return await services.get_inventory_for_recipe(
        session=session, user_id=user.id, item_id=item_id
    )


@router.put("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def upsert_inventory(
    item_id: int,
    body: InventoryUpsert,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
) -> Response:
    await services.upsert_inventory(
        session=session, user_id=user.id, item_id=item_id, quantity=body.quantity
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
