"""Database model for chunk topics — stable cross-filing identity for sections.

A :class:`ChunkTopic` is a cluster of :class:`~symbology.database.document_chunks.DocumentChunk`
rows that all express the *same* underlying topic (e.g. one risk factor) across a
single company's filings over time. Numbering and headings drift year to year, so a
topic's identity is its embedding centroid — not its position or heading text.

Scope is **(company_id, document_type)**: topics are never shared across companies
(that roll-up is a separate ``group_topics`` concern) and never across section types.

The clustering *algorithm* (nearest-centroid assignment, running-mean updates,
idempotency) lives in :mod:`symbology.worker.topic_clustering`; this module owns the
table and the primitive reads/writes it needs.
"""
import math
from datetime import datetime
from typing import List, Optional, Sequence, Tuple, Union
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from symbology.database.base import Base, get_db_session
from symbology.database.documents import DocumentType
from symbology.utils.config import settings
from symbology.utils.logging import get_logger
from uuid_extensions import uuid7

logger = get_logger(__name__)

EMBEDDING_DIM = settings.openai.embedding_dimensions


class ChunkTopic(Base):
    """A stable topic that document chunks cluster into, scoped to a company+section."""

    __tablename__ = "chunk_topics"
    __table_args__ = (
        Index("ix_chunk_topics_company_doctype", "company_id", "document_type"),
    )

    # Primary identifier (stable: never reassigned once created)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

    # Clustering scope
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    document_type: Mapped[DocumentType] = mapped_column(
        SQLEnum(DocumentType, name="document_type_enum", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )

    # Running-mean centroid of member-chunk embeddings (kept unit-normalized).
    centroid: Mapped[List[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)

    # Human-readable label, seeded from the first member chunk's heading.
    canonical_label: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Number of chunks contributing to the centroid (for the incremental mean).
    member_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return (
            f"<ChunkTopic(company_id={self.company_id}, document_type={self.document_type}, "
            f"label={self.canonical_label!r}, members={self.member_count})>"
        )

    def to_dict(self) -> dict:
        """Convert to a dictionary for API responses (excludes the raw centroid)."""
        return {
            "id": str(self.id),
            "company_id": str(self.company_id),
            "document_type": self.document_type.value if self.document_type else None,
            "canonical_label": self.canonical_label,
            "member_count": self.member_count,
        }


def _normalize(vector: Sequence[float]) -> List[float]:
    """Return a unit-length copy of ``vector`` (cosine distance is scale-invariant,
    but normalized centroids keep the running mean numerically stable)."""
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return list(vector)
    return [v / norm for v in vector]


def is_noise_label(label: Optional[str]) -> bool:
    """True when a topic/heading label carries no readable content.

    These arise when the section chunker mistakes a separator artifact for a
    heading — e.g. an underline rule (``"__________"``) between officer/signature
    rows. Such labels are not used: the topic keeps its body but the diff
    pipeline substitutes a readable member heading (or the section path) so a
    change card never shows the artifact.

    An *absent* label (``None`` / blank) is **not** noise: a real topic can
    legitimately lack a heading and fall back to its section path. Only a
    non-empty label with no alphanumeric character is treated as noise.
    """
    return bool(label and label.strip()) and not any(ch.isalnum() for ch in label)


def get_topics_for_scope(
    company_id: Union[UUID, str], document_type: DocumentType
) -> List[ChunkTopic]:
    """All topics for a (company, document_type) scope, oldest first."""
    session = get_db_session()
    return (
        session.query(ChunkTopic)
        .filter(ChunkTopic.company_id == company_id, ChunkTopic.document_type == document_type)
        .order_by(ChunkTopic.created_at)
        .all()
    )


def nearest_topic(
    company_id: Union[UUID, str],
    document_type: DocumentType,
    embedding: Sequence[float],
) -> Optional[Tuple[ChunkTopic, float]]:
    """Find the closest topic centroid within scope.

    Returns ``(topic, cosine_distance)`` (distance in ``[0, 2]``, smaller is closer)
    or ``None`` if the scope has no topics yet.
    """
    session = get_db_session()
    distance = ChunkTopic.centroid.cosine_distance(list(embedding)).label("distance")
    row = (
        session.query(ChunkTopic, distance)
        .filter(ChunkTopic.company_id == company_id, ChunkTopic.document_type == document_type)
        .order_by(distance)
        .first()
    )
    if row is None:
        return None
    topic, dist = row
    return topic, float(dist)


def create_chunk_topic(
    company_id: Union[UUID, str],
    document_type: DocumentType,
    centroid: Sequence[float],
    canonical_label: Optional[str] = None,
    *,
    commit: bool = True,
) -> ChunkTopic:
    """Create a new topic seeded with a single chunk's embedding."""
    session = get_db_session()
    topic = ChunkTopic(
        company_id=company_id,
        document_type=document_type,
        centroid=_normalize(centroid),
        canonical_label=canonical_label,
        member_count=1,
    )
    session.add(topic)
    if commit:
        session.commit()
    else:
        session.flush()
    return topic


def add_member_to_topic(
    topic: ChunkTopic, embedding: Sequence[float], *, commit: bool = True
) -> ChunkTopic:
    """Fold a new member embedding into a topic via an incremental running mean."""
    n = topic.member_count or 0
    current = list(topic.centroid) if topic.centroid is not None else [0.0] * len(embedding)
    merged = [(current[i] * n + embedding[i]) / (n + 1) for i in range(len(embedding))]
    topic.centroid = _normalize(merged)
    topic.member_count = n + 1
    if commit:
        get_db_session().commit()
    return topic


def delete_topics_for_scope(
    company_id: Union[UUID, str], document_type: DocumentType
) -> int:
    """Delete all topics for a scope (used by the recompute-from-scratch repair path).

    Member chunks' ``topic_id`` is set to NULL by the FK ``ondelete=SET NULL``.
    Returns the number of topics removed.
    """
    session = get_db_session()
    deleted = (
        session.query(ChunkTopic)
        .filter(ChunkTopic.company_id == company_id, ChunkTopic.document_type == document_type)
        .delete(synchronize_session=False)
    )
    session.commit()
    logger.info(
        "deleted_chunk_topics",
        company_id=str(company_id),
        document_type=document_type.value if document_type else None,
        count=deleted,
    )
    return deleted
