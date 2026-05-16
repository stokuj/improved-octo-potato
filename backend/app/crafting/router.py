# backend/app/crafting/router.py
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config.db import get_async_session
from app.crafting import services
from app.crafting.schemas import CalculateRequest, CraftResult, CraftSummary

router = APIRouter(prefix="/crafting", tags=["crafting"])


@router.get("/", response_model=list[CraftSummary])
async def list_recipes(
    session: AsyncSession = Depends(get_async_session),
) -> list[CraftSummary]:
    return await services.list_summaries(session)


@router.post("/{item_id}/calculate", response_model=CraftResult)
async def calculate(
    item_id: int,
    body: CalculateRequest,
    session: AsyncSession = Depends(get_async_session),
) -> CraftResult:
    return await services.calculate(session, item_id, body.multiplier, body.inventory)
