"""add cik column and bulk_ingest job type

Revision ID: e1f4a3b67c9d
Revises: d9e3f2a56b8c
Create Date: 2026-02-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f4a3b67c9d'
down_revision: Union[str, Sequence[str], None] = 'h7d8e9f01a2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cik column to companies and bulk_ingest to job_type_enum."""
    op.add_column('companies', sa.Column('cik', sa.String(20), nullable=True))
    op.create_unique_constraint('uq_companies_cik', 'companies', ['cik'])
    op.create_index('ix_companies_cik', 'companies', ['cik'])

    op.execute("ALTER TYPE job_type_enum ADD VALUE IF NOT EXISTS 'BULK_INGEST'")


def downgrade() -> None:
    """Remove cik column. bulk_ingest enum value cannot be removed in PostgreSQL."""
    op.drop_index('ix_companies_cik', table_name='companies')
    op.drop_constraint('uq_companies_cik', 'companies', type_='unique')
    op.drop_column('companies', 'cik')
