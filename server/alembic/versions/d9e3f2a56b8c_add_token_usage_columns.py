"""add input_tokens and output_tokens to generated_content

Revision ID: d9e3f2a56b8c
Revises: c8d2e1f45a7b
Create Date: 2026-02-06 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9e3f2a56b8c'
down_revision: Union[str, None] = 'c8d2e1f45a7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('generated_content', sa.Column('input_tokens', sa.Integer(), nullable=True))
    op.add_column('generated_content', sa.Column('output_tokens', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('generated_content', 'output_tokens')
    op.drop_column('generated_content', 'input_tokens')
