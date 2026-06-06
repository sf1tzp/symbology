"""add watchlist table

Creates `public.watchlist`, a per-user list of starred companies. Owned by
Alembic (lives in `public`). The matching SQLAlchemy model is
`symbology.database.watchlist` so autogenerate keeps it.

The `user_id` foreign key targets `auth."user"(id)` (Better Auth's user
table, TEXT id). Because that table is created by `better-auth migrate`,
this migration MUST run after that step. Order:
    1. alembic upgrade -> r7b8c9d0e1f2  (CREATE SCHEMA auth)
    2. better-auth migrate              (creates auth."user", etc.)
    3. alembic upgrade -> s8c9d0e1f2a3  (this migration)

Revision ID: s8c9d0e1f2a3
Revises: r7b8c9d0e1f2
Create Date: 2026-06-02 12:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 's8c9d0e1f2a3'
down_revision: Union[str, None] = 'r7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ordering guard: the FK below targets auth."user", which is created by
    # `@better-auth/cli migrate`, NOT Alembic. If someone runs a straight
    # `alembic upgrade head` on a fresh DB they'd otherwise hit a cryptic
    # `relation "auth.user" does not exist`. Fail early with an actionable
    # message instead. (`just db-init` from the repo root sequences this for you.)
    if op.get_bind().execute(sa.text('SELECT to_regclass(\'auth."user"\')')).scalar() is None:
        raise RuntimeError(
            'auth."user" is missing — run `npx @better-auth/cli migrate` (from ui/) '
            "before continuing this migration. From the repo root, `just db-init` "
            "sequences the whole bootstrap. See server/alembic/README."
        )

    op.create_table(
        'watchlist',
        sa.Column('id', sa.Uuid(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column(
            'company_id',
            sa.Uuid(),
            sa.ForeignKey('companies.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('user_id', 'company_id', name='uq_watchlist_user_company'),
    )
    # Cross-schema FK to Better Auth's user table (auth."user").
    # Done separately so the reserved-word identifier is quoted correctly.
    op.create_foreign_key(
        'fk_watchlist_user_id',
        source_table='watchlist',
        referent_table='user',
        local_cols=['user_id'],
        remote_cols=['id'],
        ondelete='CASCADE',
        referent_schema='auth',
    )
    op.create_index('ix_watchlist_user_id', 'watchlist', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_watchlist_user_id', table_name='watchlist')
    op.drop_constraint('fk_watchlist_user_id', 'watchlist', type_='foreignkey')
    op.drop_table('watchlist')
