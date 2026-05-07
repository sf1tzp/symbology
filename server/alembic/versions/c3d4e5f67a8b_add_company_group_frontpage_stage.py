"""add company_group_frontpage content stage

Revision ID: c3d4e5f67a8b
Revises: b2c3d4e56f7a
Create Date: 2026-02-14 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f67a8b'
down_revision: Union[str, None] = 'b2c3d4e56f7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE content_stage_enum ADD VALUE IF NOT EXISTS 'company_group_frontpage'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from enums.
    # The value will remain but is harmless if unused.
    pass
