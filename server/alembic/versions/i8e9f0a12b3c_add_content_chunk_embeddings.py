"""add document and generated content chunk tables with vector embeddings

Revision ID: i8e9f0a12b3c
Revises: c3d4e5f67a8b
Create Date: 2026-05-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'i8e9f0a12b3c'
down_revision: Union[str, None] = 'c3d4e5f67a8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 1024


def upgrade() -> None:
    # --- Enable pgvector ---
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # --- document_chunks ---
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("embedding_model", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_content_hash", "document_chunks", ["content_hash"])
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding ON document_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    # --- generated_content_chunks ---
    op.create_table(
        "generated_content_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("generated_content_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("embedding_model", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["generated_content_id"], ["generated_content.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("generated_content_id", "chunk_index", name="uq_generated_content_chunk_index"),
    )
    op.create_index(
        "ix_generated_content_chunks_generated_content_id",
        "generated_content_chunks",
        ["generated_content_id"],
    )
    op.create_index(
        "ix_generated_content_chunks_content_hash",
        "generated_content_chunks",
        ["content_hash"],
    )
    op.execute(
        "CREATE INDEX ix_generated_content_chunks_embedding ON generated_content_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("ix_generated_content_chunks_embedding", table_name="generated_content_chunks")
    op.drop_index("ix_generated_content_chunks_content_hash", table_name="generated_content_chunks")
    op.drop_index("ix_generated_content_chunks_generated_content_id", table_name="generated_content_chunks")
    op.drop_table("generated_content_chunks")

    op.drop_index("ix_document_chunks_embedding", table_name="document_chunks")
    op.drop_index("ix_document_chunks_content_hash", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")

    # Leave the pgvector extension in place; other objects may depend on it.
