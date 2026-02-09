"""add company_group_pipeline job type

Revision ID: g6c7d8e90f1a
Revises: f5b6a7c89d0e
Create Date: 2026-02-07 12:01:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'g6c7d8e90f1a'
down_revision: Union[str, None] = 'f5b6a7c89d0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add COMPANY_GROUP_PIPELINE to job_type_enum."""
    op.execute("ALTER TYPE job_type_enum ADD VALUE IF NOT EXISTS 'company_group_pipeline'")


def downgrade() -> None:
    """PostgreSQL does not support removing values from enums.

    The company_group_pipeline value will remain in the enum but will not
    be used after downgrade.
    """
    pass
