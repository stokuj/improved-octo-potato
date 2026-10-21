from seed import seed


async def test_seed_is_idempotent(session) -> None:
    await seed(session)
    second = await seed(session)
    assert [r.kind for r in second] == ["market", "listings"]
    assert all(
        r.inserted == 0 and r.updated == 0 and r.error_count == 0 for r in second
    )
