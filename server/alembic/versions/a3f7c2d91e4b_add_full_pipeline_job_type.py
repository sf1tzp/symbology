"""add full_pipeline job type

Revision ID: a3f7c2d91e4b
Revises: 481ecc895dd9
Create Date: 2026-02-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a3f7c2d91e4b'
down_revision: Union[str, Sequence[str], None] = '481ecc895dd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add FULL_PIPELINE to job_type_enum."""
    op.execute("ALTER TYPE job_type_enum ADD VALUE IF NOT EXISTS 'FULL_PIPELINE'")


def downgrade() -> None:
    """PostgreSQL does not support removing values from enums.

    The FULL_PIPELINE value will remain in the enum but will not be used
    after downgrade.  This is safe because no constraint references it
    exclusively.
    """
    pass
