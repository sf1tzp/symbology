"""Database models for precomputed year-over-year section diffs.

A :class:`DiffSet` is one computed comparison of a ``(company, document_type)``
section between two consecutive filings (left = older, right = newer). Its child
:class:`SectionDiff` rows hold, per aligned topic, the token-level diff ops, a
change classification, and a link to an optional per-topic LLM summary.

Diffs are structured data the UI renders directly (the token ops reconstruct both
side-by-side columns), so they live in dedicated tables rather than in the prose
``GeneratedContent`` store. Versioning mirrors ``page_content``: the "current"
diff set for a scope is the most recently created one.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from symbology.database.base import Base, get_db_session
from symbology.database.documents import DocumentType
from symbology.utils.logging import get_logger
from uuid_extensions import uuid7

logger = get_logger(__name__)


class ChangeKind(str, Enum):
    """How a topic changed between the two filings (stored as a plain string)."""
    NEW = "new"                    # present in the newer filing only
    REMOVED = "removed"            # present in the older filing only
    ESCALATED = "escalated"        # materially expanded
    DE_EMPHASISED = "de_emphasised"  # materially shortened
    REWORDED = "reworded"          # changed without a large length shift
    UNCHANGED = "unchanged"        # negligible change


class DiffSet(Base):
    """One year-over-year diff of a section between two consecutive filings."""

    __tablename__ = "diff_sets"
    __table_args__ = (
        Index("ix_diff_sets_scope", "company_id", "document_type", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    document_type: Mapped[DocumentType] = mapped_column(
        SQLEnum(DocumentType, name="document_type_enum", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    form: Mapped[Optional[str]] = mapped_column(String(20))

    # Older (left) and newer (right) filings being compared.
    left_filing_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("filings.id", ondelete="SET NULL"), nullable=True
    )
    right_filing_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("filings.id", ondelete="SET NULL"), nullable=True
    )

    # Aggregate change counts (e.g. {"new": 2, "removed": 1, "escalated": 4, ...}).
    counts: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)
    # Which differ produced the ops (provenance).
    diff_lib: Mapped[Optional[str]] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    section_diffs: Mapped[List["SectionDiff"]] = relationship(
        "SectionDiff",
        back_populates="diff_set",
        cascade="all, delete-orphan",
        order_by="SectionDiff.ordinal",
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "company_id": str(self.company_id),
            "document_type": self.document_type.value if self.document_type else None,
            "form": self.form,
            "left_filing_id": str(self.left_filing_id) if self.left_filing_id else None,
            "right_filing_id": str(self.right_filing_id) if self.right_filing_id else None,
            "counts": self.counts or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SectionDiff(Base):
    """The diff of one aligned topic between the two filings of its parent set."""

    __tablename__ = "section_diffs"
    __table_args__ = (
        Index("ix_section_diffs_set", "diff_set_id", "ordinal"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    diff_set_id: Mapped[UUID] = mapped_column(
        ForeignKey("diff_sets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    diff_set: Mapped[DiffSet] = relationship("DiffSet", back_populates="section_diffs")

    # Display order within the set.
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # The aligned topic (NULL if the chunk wasn't clustered).
    topic_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("chunk_topics.id", ondelete="SET NULL"), index=True, nullable=True
    )
    # Denormalized locator + label so the UI needn't join through topics/chunks.
    section_path: Mapped[Optional[str]] = mapped_column(String(512))
    heading: Mapped[Optional[str]] = mapped_column(Text)

    change_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    # Ordered token ops: [{"op": "equal|insert|delete", "text": "..."}].
    # left column = equal+delete, right column = equal+insert (lossless).
    ops: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, default=list)

    # Provenance to the exact chunks diffed (NULL on the absent side).
    left_chunk_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)
    right_chunk_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)

    length_delta: Mapped[int] = mapped_column(Integer, default=0)
    tokens_added: Mapped[int] = mapped_column(Integer, default=0)
    tokens_removed: Mapped[int] = mapped_column(Integer, default=0)
    truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Optional per-topic "what changed" prose (a GeneratedContent row).
    summary_content_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("generated_content.id", ondelete="SET NULL"), nullable=True
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "ordinal": self.ordinal,
            "topic_id": str(self.topic_id) if self.topic_id else None,
            "section_path": self.section_path,
            "heading": self.heading,
            "change_kind": self.change_kind,
            "ops": self.ops or [],
            "length_delta": self.length_delta,
            "tokens_added": self.tokens_added,
            "tokens_removed": self.tokens_removed,
            "truncated": self.truncated,
            "summary_content_id": str(self.summary_content_id) if self.summary_content_id else None,
        }


def delete_diff_sets_for_pair(
    company_id: Union[UUID, str],
    document_type: DocumentType,
    left_filing_id: Optional[Union[UUID, str]],
    right_filing_id: Optional[Union[UUID, str]],
) -> int:
    """Delete prior diff sets for a specific filing pair (re-run idempotency)."""
    session = get_db_session()
    deleted = (
        session.query(DiffSet)
        .filter(
            DiffSet.company_id == company_id,
            DiffSet.document_type == document_type,
            DiffSet.left_filing_id == left_filing_id,
            DiffSet.right_filing_id == right_filing_id,
        )
        .delete(synchronize_session=False)
    )
    session.commit()
    return deleted


def get_current_diff_set(
    company_id: Union[UUID, str],
    document_type: DocumentType,
    right_filing_id: Optional[Union[UUID, str]] = None,
) -> Optional[DiffSet]:
    """The most recent diff set for a scope (optionally pinned to a newer filing)."""
    session = get_db_session()
    q = session.query(DiffSet).filter(
        DiffSet.company_id == company_id,
        DiffSet.document_type == document_type,
    )
    if right_filing_id is not None:
        q = q.filter(DiffSet.right_filing_id == right_filing_id)
    return q.order_by(DiffSet.created_at.desc()).first()
