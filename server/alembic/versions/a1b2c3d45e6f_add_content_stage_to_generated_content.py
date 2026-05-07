"""add content_stage to generated_content

Revision ID: a1b2c3d45e6f
Revises: f2a3b4c56d7e
Create Date: 2026-02-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d45e6f'
down_revision: Union[str, None] = 'f2a3b4c56d7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    content_stage_enum = sa.Enum(
        'single_summary', 'aggregate_summary', 'frontpage_summary', 'company_group_analysis',
        name='content_stage_enum',
    )
    content_stage_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'generated_content',
        sa.Column('content_stage', content_stage_enum, nullable=True),
    )
    op.create_index('ix_generated_content_content_stage', 'generated_content', ['content_stage'])


def downgrade() -> None:
    op.drop_index('ix_generated_content_content_stage', table_name='generated_content')
    op.drop_column('generated_content', 'content_stage')
    op.execute("DROP TYPE IF EXISTS content_stage_enum")
