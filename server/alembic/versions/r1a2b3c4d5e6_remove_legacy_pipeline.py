"""remove legacy pipeline: drop pipeline_runs + full_pipeline/ingest_pipeline job types

Drops the pipeline_runs tracking table (and its enums) and removes the
``full_pipeline`` and ``ingest_pipeline`` values from job_type_enum. These
backed the legacy FULL_PIPELINE orchestrator and the scheduler, both of which
have been removed in favor of the FILING_PAGE_CONTENT / COMPANY_PAGE_CONTENT
flow.

Revision ID: r1a2b3c4d5e6
Revises: q9e5f6a7b8c9
Create Date: 2026-06-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'r1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'q9e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# job_type_enum values after the legacy types are removed (current order minus
# ingest_pipeline + full_pipeline).
JOB_TYPE_VALUES = (
    'company_ingestion',
    'filing_ingestion',
    'content_generation',
    'bulk_ingest',
    'company_group_pipeline',
    'filing_page_content',
    'company_page_content',
    'backfill_chunks',
    'backfill_embeddings',
    'company_diff',
    'test',
)


def upgrade() -> None:
    # 1. Drop the pipeline_runs tracking table and its dedicated enums.
    op.drop_index('ix_pipeline_runs_company_status', table_name='pipeline_runs')
    op.drop_index('ix_pipeline_runs_company_id', table_name='pipeline_runs')
    op.drop_table('pipeline_runs')
    sa.Enum(name='pipeline_run_status_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='pipeline_trigger_enum').drop(op.get_bind(), checkfirst=True)

    # 2. Remove full_pipeline / ingest_pipeline from job_type_enum. Postgres has
    #    no "drop enum value", so recreate the type. Any leftover rows of those
    #    legacy types are dropped first so the column cast succeeds.
    op.execute("DELETE FROM jobs WHERE job_type IN ('full_pipeline', 'ingest_pipeline')")
    op.execute("ALTER TYPE job_type_enum RENAME TO job_type_enum_old")
    values_sql = ", ".join(f"'{v}'" for v in JOB_TYPE_VALUES)
    op.execute(f"CREATE TYPE job_type_enum AS ENUM ({values_sql})")
    op.execute(
        "ALTER TABLE jobs ALTER COLUMN job_type TYPE job_type_enum "
        "USING job_type::text::job_type_enum"
    )
    op.execute("DROP TYPE job_type_enum_old")


def downgrade() -> None:
    # Restore the two legacy job_type_enum values.
    op.execute("ALTER TYPE job_type_enum ADD VALUE IF NOT EXISTS 'ingest_pipeline'")
    op.execute("ALTER TYPE job_type_enum ADD VALUE IF NOT EXISTS 'full_pipeline'")

    # Recreate the pipeline_runs table and enums (lowercase, matching the
    # post-normalization state this migration removed).
    op.execute(sa.text(
        "DO $$ BEGIN "
        "CREATE TYPE pipeline_trigger_enum AS ENUM ('manual', 'scheduled'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    ))
    op.execute(sa.text(
        "DO $$ BEGIN "
        "CREATE TYPE pipeline_run_status_enum AS ENUM ('pending', 'running', 'completed', 'failed', 'partial'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    ))

    trigger_col_type = postgresql.ENUM(
        'manual', 'scheduled', name='pipeline_trigger_enum', create_type=False
    )
    status_col_type = postgresql.ENUM(
        'pending', 'running', 'completed', 'failed', 'partial',
        name='pipeline_run_status_enum', create_type=False,
    )

    op.create_table('pipeline_runs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('trigger', trigger_col_type, nullable=False),
        sa.Column('status', status_col_type, nullable=False),
        sa.Column('forms', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('jobs_created', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('jobs_completed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('jobs_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_pipeline_runs_company_id', 'pipeline_runs', ['company_id'], unique=False)
    op.create_index('ix_pipeline_runs_company_status', 'pipeline_runs', ['company_id', 'status'], unique=False)
