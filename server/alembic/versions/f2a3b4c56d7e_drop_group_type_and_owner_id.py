"""drop group_type and owner_id from company_groups

Revision ID: f2a3b4c56d7e
Revises: e1f4a3b67c9d
Create Date: 2026-02-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f2a3b4c56d7e'
down_revision: Union[str, None] = 'e1f4a3b67c9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('company_groups', 'group_type')
    op.execute("DROP TYPE IF EXISTS company_group_type_enum")
    op.drop_column('company_groups', 'owner_id')


def downgrade() -> None:
    op.execute("CREATE TYPE company_group_type_enum AS ENUM ('sector', 'custom')")
    company_group_type_col = postgresql.ENUM(
        'sector', 'custom', name='company_group_type_enum', create_type=False,
    )
    op.add_column(
        'company_groups',
        sa.Column('group_type', company_group_type_col, nullable=False, server_default='sector'),
    )
    op.add_column(
        'company_groups',
        sa.Column('owner_id', sa.Uuid(), nullable=True),
    )
