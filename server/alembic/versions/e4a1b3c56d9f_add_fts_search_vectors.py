"""Add full-text search vectors, GIN indexes, and auto-update triggers

Revision ID: e4a1b3c56d9f
Revises: d9e3f2a56b8c
Create Date: 2026-02-06 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TSVECTOR


# revision identifiers, used by Alembic.
revision: str = 'e4a1b3c56d9f'
down_revision: Union[str, None] = 'd9e3f2a56b8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Add tsvector columns ---
    op.add_column('companies', sa.Column('search_vector', TSVECTOR, nullable=True))
    op.add_column('filings', sa.Column('search_vector', TSVECTOR, nullable=True))
    op.add_column('generated_content', sa.Column('search_vector', TSVECTOR, nullable=True))

    # --- Create GIN indexes for fast full-text search ---
    op.create_index('ix_companies_search_vector', 'companies', ['search_vector'],
                    postgresql_using='gin')
    op.create_index('ix_filings_search_vector', 'filings', ['search_vector'],
                    postgresql_using='gin')
    op.create_index('ix_generated_content_search_vector', 'generated_content', ['search_vector'],
                    postgresql_using='gin')

    # --- Backfill existing rows ---

    # Companies: weight A = name/ticker, B = display_name, C = SIC
    op.execute("""
        UPDATE companies SET search_vector =
            setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(ticker, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(display_name, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(sic_description, '')), 'C') ||
            setweight(to_tsvector('english', coalesce(sic, '')), 'C')
    """)

    # Filings: weight A = company name/ticker (via join), B = accession/form
    op.execute("""
        UPDATE filings f SET search_vector =
            setweight(to_tsvector('english', coalesce(c.name, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(c.ticker, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(f.accession_number, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(f.form, '')), 'B')
        FROM companies c WHERE c.id = f.company_id
    """)

    # Generated content: weight A = summary, B = description/ticker
    op.execute("""
        UPDATE generated_content gc SET search_vector =
            setweight(to_tsvector('english', coalesce(gc.summary, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(gc.description, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(c.ticker, '')), 'B')
        FROM companies c WHERE c.id = gc.company_id
    """)

    # Also backfill generated_content rows that have no company
    op.execute("""
        UPDATE generated_content SET search_vector =
            setweight(to_tsvector('english', coalesce(summary, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(description, '')), 'B')
        WHERE company_id IS NULL AND search_vector IS NULL
    """)

    # --- Create trigger functions ---

    # Company trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION companies_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', coalesce(NEW.name, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(NEW.ticker, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(NEW.display_name, '')), 'B') ||
                setweight(to_tsvector('english', coalesce(NEW.sic_description, '')), 'C') ||
                setweight(to_tsvector('english', coalesce(NEW.sic, '')), 'C');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER companies_search_vector_trigger
        BEFORE INSERT OR UPDATE OF name, ticker, display_name, sic, sic_description
        ON companies
        FOR EACH ROW EXECUTE FUNCTION companies_search_vector_update();
    """)

    # Filing trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION filings_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', coalesce(NEW.accession_number, '')), 'B') ||
                setweight(to_tsvector('english', coalesce(NEW.form, '')), 'B');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER filings_search_vector_trigger
        BEFORE INSERT OR UPDATE OF accession_number, form
        ON filings
        FOR EACH ROW EXECUTE FUNCTION filings_search_vector_update();
    """)

    # Generated content trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION generated_content_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', coalesce(NEW.summary, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(NEW.description, '')), 'B');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER generated_content_search_vector_trigger
        BEFORE INSERT OR UPDATE OF summary, description
        ON generated_content
        FOR EACH ROW EXECUTE FUNCTION generated_content_search_vector_update();
    """)


def downgrade() -> None:
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS generated_content_search_vector_trigger ON generated_content")
    op.execute("DROP FUNCTION IF EXISTS generated_content_search_vector_update()")
    op.execute("DROP TRIGGER IF EXISTS filings_search_vector_trigger ON filings")
    op.execute("DROP FUNCTION IF EXISTS filings_search_vector_update()")
    op.execute("DROP TRIGGER IF EXISTS companies_search_vector_trigger ON companies")
    op.execute("DROP FUNCTION IF EXISTS companies_search_vector_update()")

    # Drop indexes
    op.drop_index('ix_generated_content_search_vector', table_name='generated_content')
    op.drop_index('ix_filings_search_vector', table_name='filings')
    op.drop_index('ix_companies_search_vector', table_name='companies')

    # Drop columns
    op.drop_column('generated_content', 'search_vector')
    op.drop_column('filings', 'search_vector')
    op.drop_column('companies', 'search_vector')
