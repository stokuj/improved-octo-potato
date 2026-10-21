import uuid

import pytest

from app.config.exceptions import AppError, NotFoundError
from app.user_inventory.services import get_inventory_for_recipe


@pytest.mark.asyncio
async def test_for_recipe_raises_not_found_for_unknown_item(session):
    with pytest.raises(NotFoundError):
        await get_inventory_for_recipe(session, user_id=uuid.uuid4(), item_id=10**9)


@pytest.mark.asyncio
async def test_for_recipe_propagates_app_error_from_broken_recipe(
    session, item_with_broken_recipe, sample_user
):
    with pytest.raises(AppError):
        await get_inventory_for_recipe(
            session, user_id=sample_user.id, item_id=item_with_broken_recipe.id
        )


@pytest.mark.asyncio
async def test_for_recipe_returns_empty_for_leaf_item(
    session, sample_leaf_item, sample_user
):
    result = await get_inventory_for_recipe(
        session, user_id=sample_user.id, item_id=sample_leaf_item.id
    )
    assert result == {}
