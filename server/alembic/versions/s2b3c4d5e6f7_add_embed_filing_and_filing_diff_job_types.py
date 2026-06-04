"""add embed_filing and filing_diff job types

Revision ID: s2b3c4d5e6f7
Revises: r1a2b3c4d5e6
Create Date: 2026-06-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 's2b3c4d5e6f7'
down_revision: Union[str, None] = 'r1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE job_type_enum ADD VALUE IF NOT EXISTS 'embed_filing'")
    op.execute("ALTER TYPE job_type_enum ADD VALUE IF NOT EXISTS 'filing_diff'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from enums.
    pass
