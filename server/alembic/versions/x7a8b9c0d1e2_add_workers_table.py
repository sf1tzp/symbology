"""add workers table

Introduces `public.workers`, making a worker a first-class, self-heartbeating
entity rather than something inferred from the jobs it holds. Liveness moves off
the job row (which conflated "job progressing" with "worker alive") and onto the
worker, so the reap sweep can declare a *worker* dead and reclaim its in-progress
jobs operationally — without burning the job's retry budget.

Revision ID: x7a8b9c0d1e2
Revises: w6f7a8b9c0d1
Create Date: 2026-06-08 22:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'x7a8b9c0d1e2'
down_revision: Union[str, None] = 'w6f7a8b9c0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    worker_status = postgresql.ENUM(
        'idle', 'running', 'stopped', 'dead',
        name='worker_status_enum',
        create_type=False,
    )
    worker_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'workers',
        sa.Column('id', sa.String(length=255), primary_key=True),
        sa.Column('hostname', sa.String(length=255), nullable=True),
        sa.Column('pid', sa.Integer(), nullable=True),
        sa.Column('status', worker_status, nullable=False, server_default='idle'),
        # Loose reference to jobs.id (no FK — symmetric with jobs.worker_id).
        sa.Column('current_job_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    # Drives the reap sweep: live workers whose heartbeat has lapsed.
    op.create_index('ix_workers_liveness', 'workers', ['status', 'last_heartbeat'])


def downgrade() -> None:
    op.drop_index('ix_workers_liveness', table_name='workers')
    op.drop_table('workers')
    postgresql.ENUM(name='worker_status_enum').drop(op.get_bind(), checkfirst=True)
