"""resize embedding vectors to 768 dims (nomic-embed-text-v1.5)

The system standardizes on ``text-embedding-nomic-embed-text-v1.5`` (768-dim),
which LM Studio can serve as an embedding-type instance; the qwen3-architecture
jina model could not be served from ``/v1/embeddings``. No embeddings are stored
yet, so this is a pure type change (the HNSW indexes must be dropped first
because their operator class is bound to the column's vector dimension).

Revision ID: q9e5f6a7b8c9
Revises: p8d4e5f6a7b8
Create Date: 2026-06-04
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'q9e5f6a7b8c9'
down_revision: Union[str, None] = 'p8d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_DIM = 768
_OLD_DIM = 1024

# (table, column, hnsw_index_name | None)
_VECTOR_COLUMNS = [
    ("document_chunks", "embedding", "ix_document_chunks_embedding"),
    ("generated_content_chunks", "embedding", "ix_generated_content_chunks_embedding"),
    ("chunk_topics", "centroid", None),
]


def _resize(dim: int) -> None:
    # Drop HNSW indexes first; the cosine operator class is bound to the column's
    # declared dimension, so the type change fails while the index exists.
    for table, column, index in _VECTOR_COLUMNS:
        if index:
            op.execute(f"DROP INDEX IF EXISTS {index}")
    for table, column, _index in _VECTOR_COLUMNS:
        # No USING cast needed: every value is NULL (nothing embedded yet).
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE vector({dim})")
    for table, column, index in _VECTOR_COLUMNS:
        if index:
            op.execute(
                f"CREATE INDEX {index} ON {table} "
                f"USING hnsw ({column} vector_cosine_ops)"
            )


def upgrade() -> None:
    _resize(_NEW_DIM)


def downgrade() -> None:
    _resize(_OLD_DIM)
