"""add filing_id and document_id scope FKs to generated_content

Revision ID: l1b2c3d4e5f6
Revises: k0a1b2c3d4e5
Create Date: 2026-05-30 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'l1b2c3d4e5f6'
down_revision: Union[str, None] = 'k0a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable subject/scope FKs (mirror company_group_id); provenance M2M unchanged."""
    op.add_column(
        'generated_content',
        sa.Column('filing_id', sa.Uuid(), sa.ForeignKey('filings.id', ondelete='SET NULL'), nullable=True),
    )
    op.add_column(
        'generated_content',
        sa.Column('document_id', sa.Uuid(), sa.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_generated_content_filing_id', 'generated_content', ['filing_id'])
    op.create_index('ix_generated_content_document_id', 'generated_content', ['document_id'])


def downgrade() -> None:
    op.drop_index('ix_generated_content_document_id', table_name='generated_content')
    op.drop_index('ix_generated_content_filing_id', table_name='generated_content')
    op.drop_column('generated_content', 'document_id')
    op.drop_column('generated_content', 'filing_id')
