"""add is_substantive to documents

Adds ``documents.is_substantive`` (NOT NULL, default true). Non-substantive
sections — too short, or structural artifacts like a bare table of contents —
are still stored so the original source stays viewable on the site, but are
excluded from the page-content generation path. Existing rows backfill to true
via the server default (they were all stored because they passed validation).

Revision ID: t9d0e1f2a3b4
Revises: s8c9d0e1f2a3
Create Date: 2026-06-04 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 't9d0e1f2a3b4'
down_revision: Union[str, None] = 's8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'documents',
        sa.Column(
            'is_substantive',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true'),
        ),
    )


def downgrade() -> None:
    op.drop_column('documents', 'is_substantive')
