import pytest
from sqlalchemy.sql.dml import Delete

from app.user_items.services import unfollow_item


@pytest.mark.asyncio
async def test_unfollow_is_idempotent_and_single_roundtrip(
    session, sample_user, sample_item, mocker
):
    """`unfollow_item` should be:
    - Idempotent: calling on a non-existent follow row must be a silent no-op.
    - Single round trip: exactly one `session.exec` per call (a DELETE), no SELECT.
    """
    spy = mocker.spy(session, "exec")
    await unfollow_item(session, user_id=sample_user.id, item_id=sample_item.id)
    await unfollow_item(
        session, user_id=sample_user.id, item_id=sample_item.id
    )  # no-op
    # Expect exactly 2 exec calls (one DELETE per unfollow), no SELECT
    assert spy.call_count == 2
    # Each invocation must be a DELETE statement (not a SELECT)
    for call in spy.call_args_list:
        stmt = call.args[0]
        assert isinstance(stmt, Delete), f"Expected DELETE, got {type(stmt).__name__}"
