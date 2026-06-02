"""add auth schema

Creates the dedicated `auth` Postgres schema that Better Auth owns. The
Better Auth tables themselves (user/session/account/verification) are created
and migrated by `@better-auth/cli migrate` from the UI, NOT by Alembic. This
migration only provisions the namespace so it is tracked and reproducible.

Alembic continues to own `public`; because env.py does not enable
`include_schemas`, autogenerate compares only `public` and will never touch
anything inside `auth`.

Deploy ordering note: this migration must run before `better-auth migrate`
(which needs the schema to exist), and the watchlist migration
(s8c9d0e1f2a3) must run after `better-auth migrate` because it adds a foreign
key to `auth."user"`.

Revision ID: r7b8c9d0e1f2
Revises: p5f6a7b8c9d0
Create Date: 2026-06-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'r7b8c9d0e1f2'
down_revision: Union[str, None] = 'p5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS auth")


def downgrade() -> None:
    # CASCADE so it also drops the Better Auth tables created inside it.
    op.execute("DROP SCHEMA IF EXISTS auth CASCADE")
