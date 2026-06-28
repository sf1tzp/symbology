"""add supporter_grants table

Creates `public.supporter_grants`, a per-user ledger of supporter purchases.
Owned by Alembic (lives in `public`). The matching SQLAlchemy model is
`symbology.database.supporter_grants` so autogenerate keeps it.

One row per completed payment. A user's *active* supporter window is the max
`expires_at` across their grants; top-ups stack (each new grant's `expires_at`
is computed off the previous max, in the UI's grant helper). Rows are written
by the Stripe webhook and read by the SvelteKit UI (via Kysely); the Python
services don't use it.

The `user_id` foreign key targets `auth."user"(id)` (Better Auth's user table,
TEXT id), so — like the watchlist migration — this MUST run after
`better-auth migrate`. Order:
    1. alembic upgrade -> r7b8c9d0e1f2  (CREATE SCHEMA auth)
    2. better-auth migrate              (creates auth."user", etc.)
    3. alembic upgrade -> y8b9c0d1e2f3  (this migration)

`provider_txn_id` is unique so the webhook can upsert idempotently (Stripe may
deliver `checkout.session.completed` more than once).

Revision ID: y8b9c0d1e2f3
Revises: x7a8b9c0d1e2
Create Date: 2026-06-19 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'y8b9c0d1e2f3'
down_revision: Union[str, None] = 'x7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ordering guard: the FK below targets auth."user", created by
    # `@better-auth/cli migrate`, NOT Alembic. Fail early with an actionable
    # message rather than a cryptic missing-relation error. (`just db-init`
    # from the repo root sequences the whole bootstrap.)
    if op.get_bind().execute(sa.text('SELECT to_regclass(\'auth."user"\')')).scalar() is None:
        raise RuntimeError(
            'auth."user" is missing — run `npx @better-auth/cli migrate` (from ui/) '
            "before continuing this migration. From the repo root, `just db-init` "
            "sequences the whole bootstrap. See server/alembic/README."
        )

    op.create_table(
        'supporter_grants',
        sa.Column('id', sa.Uuid(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.Text(), nullable=False),
        # Amount charged, in cents. $20 flat -> 2000; $1/day -> days * 100.
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        # Days of supporter status this grant adds.
        sa.Column('days', sa.Integer(), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # End of the supporter window this grant extends to (granted_at-based,
        # stacked onto any prior remaining days).
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        # Payment provider + its transaction id (Stripe PaymentIntent/session id).
        sa.Column('provider', sa.Text(), nullable=False),
        sa.Column('provider_txn_id', sa.Text(), nullable=False),
        # 'one' (flat $20 / 14 days) or 'duration' ($1/day slider).
        sa.Column('plan_type', sa.Text(), nullable=False),
        sa.UniqueConstraint('provider_txn_id', name='uq_supporter_grants_provider_txn_id'),
    )
    # Cross-schema FK to Better Auth's user table (auth."user").
    op.create_foreign_key(
        'fk_supporter_grants_user_id',
        source_table='supporter_grants',
        referent_table='user',
        local_cols=['user_id'],
        remote_cols=['id'],
        ondelete='CASCADE',
        referent_schema='auth',
    )
    op.create_index('ix_supporter_grants_user_id', 'supporter_grants', ['user_id'])
    op.create_index('ix_supporter_grants_expires_at', 'supporter_grants', ['expires_at'])


def downgrade() -> None:
    op.drop_index('ix_supporter_grants_expires_at', table_name='supporter_grants')
    op.drop_index('ix_supporter_grants_user_id', table_name='supporter_grants')
    op.drop_constraint('fk_supporter_grants_user_id', 'supporter_grants', type_='foreignkey')
    op.drop_table('supporter_grants')
