"""Database model for generated content chunks with vector embeddings.

Mirrors :mod:`symbology.database.document_chunks` for AI-generated content so
that both source documents and derived content are searchable by vector
similarity through the same machinery.
"""
import hashlib
from typing import Any, Dict, List, Optional, Sequence, Union
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import backref, Mapped, mapped_column, relationship
from symbology.database.base import Base, get_db_session
from symbology.utils.config import settings
from symbology.utils.logging import get_logger
from uuid_extensions import uuid7

logger = get_logger(__name__)

EMBEDDING_DIM = settings.openai.embedding_dimensions


class GeneratedContentChunk(Base):
    """A contiguous, embeddable slice of a GeneratedContent's content."""

    __tablename__ = "generated_content_chunks"
    __table_args__ = (
        UniqueConstraint("generated_content_id", "chunk_index", name="uq_generated_content_chunk_index"),
    )

    # Primary identifier
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

    # Parent generated content (chunks are deleted with their parent)
    generated_content_id: Mapped[UUID] = mapped_column(
        ForeignKey("generated_content.id", ondelete="CASCADE"), index=True, nullable=False
    )
    generated_content = relationship(
        "GeneratedContent",
        backref=backref(
            "chunks",
            order_by="GeneratedContentChunk.chunk_index",
            cascade="all, delete-orphan",
            passive_deletes=True,
        ),
    )

    # Ordering within the parent content
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Chunk text and a hash for dedup / change detection
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)

    # Dense embedding (nullable: embedding can fail or be backfilled later)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<GeneratedContentChunk(generated_content_id={self.generated_content_id}, index={self.chunk_index}, embedded={self.embedding is not None})>"  # noqa: E501

    def generate_content_hash(self) -> str:
        """Generate SHA256 hash of the chunk content."""
        if not self.content:
            return ""
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()

    def update_content_hash(self) -> None:
        """Update the content hash based on current content."""
        self.content_hash = self.generate_content_hash()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for API responses (excludes the raw vector)."""
        return {
            "id": str(self.id),
            "generated_content_id": str(self.generated_content_id),
            "chunk_index": self.chunk_index,
            "content": self.content,
            "content_hash": self.content_hash,
            "embedding_model": self.embedding_model,
            "is_embedded": self.embedding is not None,
        }


def get_chunks_by_content(content_id: Union[UUID, str]) -> List[GeneratedContentChunk]:
    """Get all chunks for a generated content, ordered by chunk index."""
    session = get_db_session()
    return (
        session.query(GeneratedContentChunk)
        .filter(GeneratedContentChunk.generated_content_id == content_id)
        .order_by(GeneratedContentChunk.chunk_index)
        .all()
    )


def delete_chunks_for_content(content_id: Union[UUID, str]) -> int:
    """Delete all existing chunks for a generated content. Returns the number removed."""
    session = get_db_session()
    deleted = (
        session.query(GeneratedContentChunk)
        .filter(GeneratedContentChunk.generated_content_id == content_id)
        .delete(synchronize_session=False)
    )
    session.commit()
    logger.info("deleted_generated_content_chunks", content_id=str(content_id), count=deleted)
    return deleted


def replace_content_chunks(
    content_id: Union[UUID, str],
    contents: Sequence[str],
    embeddings: Sequence[Optional[Sequence[float]]],
    embedding_model: Optional[str] = None,
) -> List[GeneratedContentChunk]:
    """Replace a generated content's chunks atomically with a fresh ordered set.

    Args:
        content_id: The parent generated content.
        contents: Ordered chunk texts.
        embeddings: Per-chunk embedding vectors (``None`` entries allowed).
        embedding_model: Name of the model that produced the embeddings.

    Returns:
        The newly created GeneratedContentChunk rows.
    """
    if len(contents) != len(embeddings):
        raise ValueError(f"contents ({len(contents)}) and embeddings ({len(embeddings)}) length mismatch")

    session = get_db_session()
    try:
        session.query(GeneratedContentChunk).filter(
            GeneratedContentChunk.generated_content_id == content_id
        ).delete(synchronize_session=False)

        chunks: List[GeneratedContentChunk] = []
        for index, (content, embedding) in enumerate(zip(contents, embeddings)):
            chunk = GeneratedContentChunk(
                generated_content_id=content_id,
                chunk_index=index,
                content=content,
                embedding=list(embedding) if embedding is not None else None,
                embedding_model=embedding_model,
            )
            chunk.update_content_hash()
            session.add(chunk)
            chunks.append(chunk)

        session.commit()
        logger.info("replaced_generated_content_chunks", content_id=str(content_id), count=len(chunks))
        return chunks
    except Exception as e:
        session.rollback()
        logger.error("replace_content_chunks_failed", content_id=str(content_id), error=str(e), exc_info=True)
        raise


def search_content_chunks(
    query_embedding: Sequence[float],
    limit: int = 10,
) -> List[tuple[GeneratedContentChunk, float]]:
    """Find the most similar generated content chunks to a query embedding.

    Uses pgvector cosine distance. Returns (chunk, distance) pairs ordered by
    ascending distance (closest first).
    """
    session = get_db_session()
    distance = GeneratedContentChunk.embedding.cosine_distance(list(query_embedding)).label("distance")
    rows = (
        session.query(GeneratedContentChunk, distance)
        .filter(GeneratedContentChunk.embedding.is_not(None))
        .order_by(distance)
        .limit(limit)
        .all()
    )
    return [(chunk, dist) for chunk, dist in rows]
