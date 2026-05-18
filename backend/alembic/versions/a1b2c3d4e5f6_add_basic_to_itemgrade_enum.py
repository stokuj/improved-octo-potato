"""add BASIC to itemgrade enum

Revision ID: a1b2c3d4e5f6
Revises: d23b9a1d1e22
Create Date: 2026-05-17 19:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "d23b9a1d1e22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE itemgrade ADD VALUE IF NOT EXISTS 'BASIC'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from an enum type.
    pass
