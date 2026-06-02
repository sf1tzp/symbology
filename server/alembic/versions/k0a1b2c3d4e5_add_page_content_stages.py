"""add page-content stages to content_stage_enum

Revision ID: k0a1b2c3d4e5
Revises: j9a0b1c2d3e4
Create Date: 2026-05-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'k0a1b2c3d4e5'
down_revision: Union[str, None] = 'j9a0b1c2d3e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_STAGES = (
    'change_report',
    'change_report_intro',
    'company_main_content',
    'company_intro',
    'group_main_content',
    'group_intro',
    'filing_main_content',
    'filing_intro',
    'document_page_intro',
)


def upgrade() -> None:
    for value in _NEW_STAGES:
        op.execute(f"ALTER TYPE content_stage_enum ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from enums.
    # The values remain but are harmless if unused.
    pass
