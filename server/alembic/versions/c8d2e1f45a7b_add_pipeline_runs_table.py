"""add pipeline_runs table

Revision ID: c8d2e1f45a7b
Revises: a3f7c2d91e4b
Create Date: 2026-02-06 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c8d2e1f45a7b'
down_revision: Union[str, Sequence[str], None] = 'a3f7c2d91e4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create pipeline_runs table and enums."""
    # Create enums idempotently via raw SQL
    op.execute(sa.text(
        "DO $$ BEGIN "
        "CREATE TYPE pipeline_trigger_enum AS ENUM ('MANUAL', 'SCHEDULED'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    ))
    op.execute(sa.text(
        "DO $$ BEGIN "
        "CREATE TYPE pipeline_run_status_enum AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'PARTIAL'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    ))

    # Use postgresql.ENUM with create_type=False to reference existing enums
    trigger_col_type = postgresql.ENUM('MANUAL', 'SCHEDULED', name='pipeline_trigger_enum', create_type=False)
    status_col_type = postgresql.ENUM(
        'PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'PARTIAL',
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


def downgrade() -> None:
    """Drop pipeline_runs table and enums."""
    op.drop_index('ix_pipeline_runs_company_status', table_name='pipeline_runs')
    op.drop_index('ix_pipeline_runs_company_id', table_name='pipeline_runs')
    op.drop_table('pipeline_runs')

    # Drop enums
    sa.Enum(name='pipeline_run_status_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='pipeline_trigger_enum').drop(op.get_bind(), checkfirst=True)
