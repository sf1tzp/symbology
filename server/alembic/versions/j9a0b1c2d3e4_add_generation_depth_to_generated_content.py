"""add generation_depth to generated_content

Revision ID: j9a0b1c2d3e4
Revises: i8e9f0a12b3c
Create Date: 2026-05-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'j9a0b1c2d3e4'
down_revision: Union[str, None] = 'i8e9f0a12b3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the heuristic generation_depth column (nullable; computed at write time)."""
    op.add_column(
        'generated_content',
        sa.Column('generation_depth', sa.Integer(), nullable=True),
    )
    op.create_index(
        'ix_generated_content_generation_depth',
        'generated_content',
        ['generation_depth'],
    )


def downgrade() -> None:
    op.drop_index('ix_generated_content_generation_depth', table_name='generated_content')
    op.drop_column('generated_content', 'generation_depth')
