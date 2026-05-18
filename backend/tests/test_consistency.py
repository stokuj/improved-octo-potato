"""
Cross-file consistency checks.

These tests guard invariants that span multiple files and would otherwise
only be caught at runtime (e.g. source mismatch between seed data and
frontend chart queries).
"""

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent


def test_seed_uses_ah_source():
    """seed.py must use source='ah' — the same source the frontend chart queries."""
    seed = (REPO_ROOT / "backend" / "seed.py").read_text()
    assert 'source="ah"' in seed, (
        "seed.py must use source='ah' to match the frontend chart. "
        "Found a different source — update seed.py or frontend/src/routes/items/[id]/+page.svelte."
    )
    assert 'source="market"' not in seed, (
        "seed.py still contains source='market' which the frontend no longer queries."
    )


def test_frontend_chart_uses_ah_source():
    """Frontend price chart must query source='ah' — matching seed and bot."""
    page = (
        REPO_ROOT / "frontend" / "src" / "routes" / "items" / "[id]" / "+page.svelte"
    ).read_text()
    assert "const SOURCE = 'ah'" in page, (
        "Frontend chart SOURCE constant must be 'ah'. "
        "Check frontend/src/routes/items/[id]/+page.svelte."
    )
