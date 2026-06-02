"""add filing_page_content job type

Revision ID: n3d4e5f6a7b8
Revises: m2c3d4e5f6a7
Create Date: 2026-05-30 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'n3d4e5f6a7b8'
down_revision: Union[str, None] = 'm2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE job_type_enum ADD VALUE IF NOT EXISTS 'filing_page_content'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from enums.
    pass
