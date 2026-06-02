"""add page content tables (publishing layer)

Revision ID: m2c3d4e5f6a7
Revises: l1b2c3d4e5f6
Create Date: 2026-05-30 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'm2c3d4e5f6a7'
down_revision: Union[str, None] = 'l1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Reference the existing document_type_enum without re-creating it.
_document_type_enum = postgresql.ENUM(
    "management_discussion", "risk_factors", "business_description",
    "controls_procedures", "legal_proceedings", "market_risk",
    "executive_compensation", "directors_officers",
    name="document_type_enum", create_type=False,
)


def upgrade() -> None:
    # --- page-content tables (scope FK CASCADE; content slots RESTRICT) ---
    op.create_table(
        "document_page_content",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("summary_content_id", sa.Uuid(), sa.ForeignKey("generated_content.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("intro_content_id", sa.Uuid(), sa.ForeignKey("generated_content.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_document_page_content_scope", "document_page_content", ["document_id", "created_at"])

    op.create_table(
        "filing_page_content",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("filing_id", sa.Uuid(), sa.ForeignKey("filings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("main_content_id", sa.Uuid(), sa.ForeignKey("generated_content.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("intro_content_id", sa.Uuid(), sa.ForeignKey("generated_content.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_filing_page_content_scope", "filing_page_content", ["filing_id", "created_at"])

    op.create_table(
        "company_page_content",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("main_content_id", sa.Uuid(), sa.ForeignKey("generated_content.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("intro_content_id", sa.Uuid(), sa.ForeignKey("generated_content.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_company_page_content_scope", "company_page_content", ["company_id", "created_at"])

    op.create_table(
        "group_page_content",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("company_group_id", sa.Uuid(), sa.ForeignKey("company_groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("main_content_id", sa.Uuid(), sa.ForeignKey("generated_content.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("intro_content_id", sa.Uuid(), sa.ForeignKey("generated_content.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_group_page_content_scope", "group_page_content", ["company_group_id", "created_at"])

    # --- change-report map (report + intro per doc_type) ---
    op.create_table(
        "company_page_content_change_report",
        sa.Column("company_page_content_id", sa.Uuid(), sa.ForeignKey("company_page_content.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("document_type", _document_type_enum, primary_key=True, nullable=False),
        sa.Column("change_report_id", sa.Uuid(), sa.ForeignKey("generated_content.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("change_report_intro_id", sa.Uuid(), sa.ForeignKey("generated_content.id", ondelete="RESTRICT"), nullable=True),
    )

    # --- provenance M2M (to domain entities) ---
    op.create_table(
        "filing_page_content_document",
        sa.Column("filing_page_content_id", sa.Uuid(), sa.ForeignKey("filing_page_content.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "company_page_content_filing",
        sa.Column("company_page_content_id", sa.Uuid(), sa.ForeignKey("company_page_content.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("filing_id", sa.Uuid(), sa.ForeignKey("filings.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "group_page_content_company",
        sa.Column("group_page_content_id", sa.Uuid(), sa.ForeignKey("group_page_content.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("group_page_content_company")
    op.drop_table("company_page_content_filing")
    op.drop_table("filing_page_content_document")
    op.drop_table("company_page_content_change_report")
    op.drop_index("ix_group_page_content_scope", table_name="group_page_content")
    op.drop_table("group_page_content")
    op.drop_index("ix_company_page_content_scope", table_name="company_page_content")
    op.drop_table("company_page_content")
    op.drop_index("ix_filing_page_content_scope", table_name="filing_page_content")
    op.drop_table("filing_page_content")
    op.drop_index("ix_document_page_content_scope", table_name="document_page_content")
    op.drop_table("document_page_content")
