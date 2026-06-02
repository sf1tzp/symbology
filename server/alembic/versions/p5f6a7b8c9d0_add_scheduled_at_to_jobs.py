"""add scheduled_at to jobs

Revision ID: p5f6a7b8c9d0
Revises: o4e5f6a7b8c9
Create Date: 2026-06-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'p5f6a7b8c9d0'
down_revision: Union[str, None] = 'o4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add deferred-claim support: a NULL scheduled_at job is eligible immediately."""
    op.add_column(
        'jobs',
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_jobs_scheduled', 'jobs', ['status', 'scheduled_at'])


def downgrade() -> None:
    op.drop_index('ix_jobs_scheduled', table_name='jobs')
    op.drop_column('jobs', 'scheduled_at')
