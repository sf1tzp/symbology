"""add form to company_page_content

Revision ID: u4d5e6f7a8b9
Revises: t3c4d5e6f7a8
Create Date: 2026-06-06 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'u4d5e6f7a8b9'
down_revision: Union[str, None] = 't3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A company page is now scoped to the filing form it was synthesised from
    # (10-K vs 10-Q), so a company can publish one page per form and the UI can
    # fetch the right one. Existing rows are all 10-K-derived.
    op.add_column(
        'company_page_content',
        sa.Column('form', sa.String(length=10), nullable=True),
    )
    op.execute("UPDATE company_page_content SET form = '10-K' WHERE form IS NULL")
    op.alter_column('company_page_content', 'form', nullable=False)
    op.create_index(
        'ix_company_page_content_scope_form',
        'company_page_content',
        ['company_id', 'form', 'created_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_company_page_content_scope_form', table_name='company_page_content')
    op.drop_column('company_page_content', 'form')
