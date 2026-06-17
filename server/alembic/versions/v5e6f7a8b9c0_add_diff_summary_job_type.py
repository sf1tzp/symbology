"""add diff_summary job type

Decouples per-topic diff summaries from the FILING_DIFF job: the structural diff
is published immediately and a separate low-priority DIFF_SUMMARY job fills in the
LLM summaries asynchronously.

Revision ID: v5e6f7a8b9c0
Revises: u4d5e6f7a8b9
Create Date: 2026-06-08 08:30:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'v5e6f7a8b9c0'
down_revision: Union[str, None] = 'u4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE job_type_enum ADD VALUE IF NOT EXISTS 'diff_summary'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from enums.
    pass
