"""add chunk_topics table and section-aware columns on document_chunks

Revision ID: p5a1b2c3d4e5
Revises: t9d0e1f2a3b4
Create Date: 2026-06-02 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'p5a1b2c3d4e5'
down_revision: Union[str, None] = 't9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 1024

# Reference the existing document_type_enum without re-creating it.
_document_type_enum = postgresql.ENUM(
    "management_discussion", "risk_factors", "business_description",
    "controls_procedures", "legal_proceedings", "market_risk",
    "executive_compensation", "directors_officers",
    name="document_type_enum", create_type=False,
)


def upgrade() -> None:
    # --- chunk_topics (stable cross-filing identity, scoped to company+section) ---
    op.create_table(
        "chunk_topics",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_type", _document_type_enum, nullable=False),
        sa.Column("centroid", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("canonical_label", sa.Text(), nullable=True),
        sa.Column("member_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_chunk_topics_company_id", "chunk_topics", ["company_id"])
    op.create_index("ix_chunk_topics_company_doctype", "chunk_topics", ["company_id", "document_type"])

    # --- section-aware columns on document_chunks ---
    op.add_column("document_chunks", sa.Column("section_path", sa.String(length=512), nullable=True))
    op.add_column("document_chunks", sa.Column("heading", sa.Text(), nullable=True))
    op.add_column("document_chunks", sa.Column("char_start", sa.Integer(), nullable=True))
    op.add_column("document_chunks", sa.Column("char_end", sa.Integer(), nullable=True))
    op.add_column(
        "document_chunks",
        sa.Column("is_semantic", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column("document_chunks", sa.Column("topic_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_document_chunks_topic_id", "document_chunks", "chunk_topics",
        ["topic_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_document_chunks_section_path", "document_chunks", ["section_path"])
    op.create_index("ix_document_chunks_topic_id", "document_chunks", ["topic_id"])


def downgrade() -> None:
    op.drop_index("ix_document_chunks_topic_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_section_path", table_name="document_chunks")
    op.drop_constraint("fk_document_chunks_topic_id", "document_chunks", type_="foreignkey")
    op.drop_column("document_chunks", "topic_id")
    op.drop_column("document_chunks", "is_semantic")
    op.drop_column("document_chunks", "char_end")
    op.drop_column("document_chunks", "char_start")
    op.drop_column("document_chunks", "heading")
    op.drop_column("document_chunks", "section_path")

    op.drop_index("ix_chunk_topics_company_doctype", table_name="chunk_topics")
    op.drop_index("ix_chunk_topics_company_id", table_name="chunk_topics")
    op.drop_table("chunk_topics")
