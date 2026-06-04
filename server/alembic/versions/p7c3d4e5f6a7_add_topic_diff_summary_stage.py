"""add topic_diff_summary content stage

Revision ID: p7c3d4e5f6a7
Revises: p6b2c3d4e5f6
Create Date: 2026-06-02 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'p7c3d4e5f6a7'
down_revision: Union[str, None] = 'p6b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE content_stage_enum ADD VALUE IF NOT EXISTS 'topic_diff_summary'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from enums.
    pass
