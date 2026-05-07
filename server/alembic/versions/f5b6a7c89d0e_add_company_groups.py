"""add company groups

Revision ID: f5b6a7c89d0e
Revises: e4a1b3c56d9f
Create Date: 2026-02-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import TSVECTOR


# revision identifiers, used by Alembic.
revision: str = 'f5b6a7c89d0e'
down_revision: Union[str, None] = 'e4a1b3c56d9f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Create company_groups table ---
    # Use postgresql.ENUM with create_type=False so create_table doesn't
    # try to CREATE TYPE again after we've already created it.
    op.execute("CREATE TYPE company_group_type_enum AS ENUM ('sector', 'custom')")
    company_group_type_col = postgresql.ENUM(
        'sector', 'custom', name='company_group_type_enum', create_type=False,
    )
    op.create_table(
        'company_groups',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('group_type', company_group_type_col, nullable=False, server_default='sector'),
        sa.Column('sic_codes', sa.ARRAY(sa.String()), nullable=True, server_default='{}'),
        sa.Column('owner_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('search_vector', TSVECTOR, nullable=True),
    )
    op.create_index('ix_company_groups_slug', 'company_groups', ['slug'], unique=True)

    # --- Create company_group_membership association table ---
    op.create_table(
        'company_group_membership',
        sa.Column('company_group_id', sa.Uuid(), sa.ForeignKey('company_groups.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('company_id', sa.Uuid(), sa.ForeignKey('companies.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('added_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # --- Add company_group_id FK to generated_content ---
    op.add_column(
        'generated_content',
        sa.Column('company_group_id', sa.Uuid(), sa.ForeignKey('company_groups.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_generated_content_company_group_id', 'generated_content', ['company_group_id'])

    # --- Create GIN index on company_groups.search_vector ---
    op.create_index(
        'ix_company_groups_search_vector',
        'company_groups',
        ['search_vector'],
        postgresql_using='gin',
    )

    # --- Create TSVECTOR trigger for company_groups ---
    op.execute("""
        CREATE OR REPLACE FUNCTION company_groups_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', coalesce(NEW.name, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(NEW.slug, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(NEW.description, '')), 'B');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER company_groups_search_vector_trigger
        BEFORE INSERT OR UPDATE OF name, slug, description
        ON company_groups
        FOR EACH ROW EXECUTE FUNCTION company_groups_search_vector_update();
    """)

    # NOTE: COMPANY_GROUP_PIPELINE job type enum value is added in a separate
    # migration (g6c7d8e90f1a) because ALTER TYPE ADD VALUE cannot run
    # inside a transaction with other DDL statements.


def downgrade() -> None:
    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS company_groups_search_vector_trigger ON company_groups")
    op.execute("DROP FUNCTION IF EXISTS company_groups_search_vector_update()")

    # Drop index and column from generated_content
    op.drop_index('ix_generated_content_company_group_id', table_name='generated_content')
    op.drop_column('generated_content', 'company_group_id')

    # Drop tables
    op.drop_table('company_group_membership')
    op.drop_index('ix_company_groups_slug', table_name='company_groups')
    op.drop_index('ix_company_groups_search_vector', table_name='company_groups')
    op.drop_table('company_groups')

    # Drop enum
    sa.Enum(name='company_group_type_enum').drop(op.get_bind(), checkfirst=True)
