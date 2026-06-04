"""add diff_sets and section_diffs tables

Revision ID: p8d4e5f6a7b8
Revises: p7c3d4e5f6a7
Create Date: 2026-06-02 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'p8d4e5f6a7b8'
down_revision: Union[str, None] = 'p7c3d4e5f6a7'
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
    op.create_table(
        "diff_sets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_type", _document_type_enum, nullable=False),
        sa.Column("form", sa.String(length=20), nullable=True),
        sa.Column("left_filing_id", sa.Uuid(), sa.ForeignKey("filings.id", ondelete="SET NULL"), nullable=True),
        sa.Column("right_filing_id", sa.Uuid(), sa.ForeignKey("filings.id", ondelete="SET NULL"), nullable=True),
        sa.Column("counts", postgresql.JSON(), nullable=True),
        sa.Column("diff_lib", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_diff_sets_company_id", "diff_sets", ["company_id"])
    op.create_index("ix_diff_sets_scope", "diff_sets", ["company_id", "document_type", "created_at"])

    op.create_table(
        "section_diffs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("diff_set_id", sa.Uuid(), sa.ForeignKey("diff_sets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("topic_id", sa.Uuid(), sa.ForeignKey("chunk_topics.id", ondelete="SET NULL"), nullable=True),
        sa.Column("section_path", sa.String(length=512), nullable=True),
        sa.Column("heading", sa.Text(), nullable=True),
        sa.Column("change_kind", sa.String(length=16), nullable=False),
        sa.Column("ops", postgresql.JSON(), nullable=True),
        sa.Column("left_chunk_id", sa.Uuid(), nullable=True),
        sa.Column("right_chunk_id", sa.Uuid(), nullable=True),
        sa.Column("length_delta", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("tokens_added", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("tokens_removed", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("truncated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("summary_content_id", sa.Uuid(), sa.ForeignKey("generated_content.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_section_diffs_diff_set_id", "section_diffs", ["diff_set_id"])
    op.create_index("ix_section_diffs_set", "section_diffs", ["diff_set_id", "ordinal"])
    op.create_index("ix_section_diffs_topic_id", "section_diffs", ["topic_id"])


def downgrade() -> None:
    op.drop_index("ix_section_diffs_topic_id", table_name="section_diffs")
    op.drop_index("ix_section_diffs_set", table_name="section_diffs")
    op.drop_index("ix_section_diffs_diff_set_id", table_name="section_diffs")
    op.drop_table("section_diffs")
    op.drop_index("ix_diff_sets_scope", table_name="diff_sets")
    op.drop_index("ix_diff_sets_company_id", table_name="diff_sets")
    op.drop_table("diff_sets")
