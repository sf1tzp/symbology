"""remove company_diff job type usage

Diffs are filing-domain: the per-filing FILING_DIFF (enqueued at ingestion) builds
the period-over-period chain directly, so the COMPANY_DIFF orchestrator is gone.
Its handler / enum member are removed in code; here we delete any lingering
company_diff job rows so loading the queue doesn't trip over a value the ORM enum
no longer knows.

The 'company_diff' label is left in the Postgres ``job_type_enum`` (Postgres can't
drop an enum value without a type recreate). It's harmless once no rows reference
it; a future cleanup can recreate the type if we want it gone entirely.

Revision ID: w6f7a8b9c0d1
Revises: v5e6f7a8b9c0
Create Date: 2026-06-08 09:10:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'w6f7a8b9c0d1'
down_revision: Union[str, None] = 'v5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # COMPANY_DIFF jobs are pure orchestration (they only enqueued FILING_DIFFs),
    # so deleting them loses no diff data.
    op.execute("DELETE FROM jobs WHERE job_type = 'company_diff'")


def downgrade() -> None:
    # The deleted orchestration jobs cannot be reconstructed; nothing to do.
    pass
