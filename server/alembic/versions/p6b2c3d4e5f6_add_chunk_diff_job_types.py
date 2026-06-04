"""add backfill_chunks, backfill_embeddings, and company_diff job types

Revision ID: p6b2c3d4e5f6
Revises: p5a1b2c3d4e5
Create Date: 2026-06-02 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'p6b2c3d4e5f6'
down_revision: Union[str, None] = 'p5a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE job_type_enum ADD VALUE IF NOT EXISTS 'backfill_chunks'")
    op.execute("ALTER TYPE job_type_enum ADD VALUE IF NOT EXISTS 'backfill_embeddings'")
    op.execute("ALTER TYPE job_type_enum ADD VALUE IF NOT EXISTS 'company_diff'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from enums.
    pass
