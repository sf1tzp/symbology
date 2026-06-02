"""add company_page_content job type

Revision ID: o4e5f6a7b8c9
Revises: n3d4e5f6a7b8
Create Date: 2026-05-30 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'o4e5f6a7b8c9'
down_revision: Union[str, None] = 'n3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE job_type_enum ADD VALUE IF NOT EXISTS 'company_page_content'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from enums.
    pass
