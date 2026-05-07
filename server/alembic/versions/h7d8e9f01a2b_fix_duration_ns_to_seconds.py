"""convert total_duration from nanoseconds to seconds

After switching from Ollama to Anthropic, total_duration was stored in
nanoseconds instead of seconds.  Values > 1000 are clearly nanosecond
artifacts (no LLM call takes > 16 minutes) so we divide them by 1e9.

Revision ID: h7d8e9f01a2b
Revises: g6c7d8e90f1a
Create Date: 2026-02-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'h7d8e9f01a2b'
down_revision: Union[str, None] = 'g6c7d8e90f1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE generated_content "
        "SET total_duration = total_duration / 1e9 "
        "WHERE total_duration > 1000"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE generated_content "
        "SET total_duration = total_duration * 1e9 "
        "WHERE total_duration IS NOT NULL AND total_duration < 1000"
    )
