"""add backoff job status and backoff_count

Revision ID: t3c4d5e6f7a8
Revises: s2b3c4d5e6f7
Create Date: 2026-06-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 't3c4d5e6f7a8'
down_revision: Union[str, None] = 's2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New lifecycle state for dependency-wait deferrals (distinct from failures).
    op.execute("ALTER TYPE job_status_enum ADD VALUE IF NOT EXISTS 'backoff'")
    # Exponential-backoff attempt counter for the dependency wait, separate from
    # retry_count so a benign wait never looks like a crash.
    op.add_column(
        'jobs',
        sa.Column('backoff_count', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_column('jobs', 'backoff_count')
    # PostgreSQL does not support removing values from enums.
    # The 'backoff' value will remain but is harmless if unused.
