"""Database models for generated content (consolidates Aggregates and Completions)."""
from datetime import datetime
from enum import Enum
import hashlib
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union
from uuid import UUID

from sqlalchemy import Column, DateTime, Float, ForeignKey, func, Integer, or_, String, Table, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from symbology.database.base import Base, get_db_session
from symbology.database.companies import Company
from symbology.database.documents import DocumentType
from symbology.utils.logging import get_logger
from uuid_extensions import uuid7

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from symbology.database.documents import Document
    from symbology.database.model_configs import ModelConfig
    from symbology.database.prompts import Prompt
    from symbology.database.ratings import Rating

# Initialize structlog
logger = get_logger(__name__)


class ContentSourceType(str, Enum):
    """Enumeration of content source types."""
    DOCUMENTS = "documents"
    GENERATED_CONTENT = "generated_content"
    BOTH = "both"


class ContentStage(str, Enum):
    """Pipeline stage that produced this content."""
    SINGLE_SUMMARY = "single_summary"
    AGGREGATE_SUMMARY = "aggregate_summary"
    FRONTPAGE_SUMMARY = "frontpage_summary"
    COMPANY_GROUP_ANALYSIS = "company_group_analysis"
    COMPANY_GROUP_FRONTPAGE = "company_group_frontpage"


# Association table for many-to-many relationship between GeneratedContent and Document
generated_content_document_association = Table(
    "generated_content_document_association",
    Base.metadata,
    Column("generated_content_id", ForeignKey("generated_content.id"), primary_key=True),
    Column("document_id", ForeignKey("documents.id"), primary_key=True)
)

# Association table for many-to-many relationship between GeneratedContent (parent and child)
generated_content_source_association = Table(
    "generated_content_source_association",
    Base.metadata,
    Column("parent_content_id", ForeignKey("generated_content.id"), primary_key=True),
    Column("source_content_id", ForeignKey("generated_content.id"), primary_key=True),
    # Add metadata for richer relationships
    Column("relationship_type", String, default="derived_from"),  # 'references', 'summarizes', etc.
    Column("created_at", DateTime, default=func.now())
)


class GeneratedContent(Base):
    """GeneratedContent model representing AI-generated content from various sources."""

    __tablename__ = "generated_content"

    # Primary identifier
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

    # Content hash for URL identification and verification
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True, unique=True)

    # Company Foreign Key (optional, for company-specific content)
    company_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    company: Mapped[Optional["Company"]] = relationship(
        "Company",
        foreign_keys=[company_id],
        backref="generated_content"
    )

    # Company Group Foreign Key (optional, for group-level content)
    company_group_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("company_groups.id", ondelete="SET NULL"), index=True, nullable=True
    )

    # description (optional, string description of the content)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Document type for disambiguation when content is generated from documents
    document_type: Mapped[Optional[DocumentType]] = mapped_column(
        SQLEnum(DocumentType, name="document_type_enum", values_callable=lambda obj: [e.value for e in obj]),
        nullable=True,
        index=True
    )

    # Form type (10-K, 10-Q, etc.) associated with source documents
    form_type: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, index=True)

    # Pipeline stage that produced this content
    content_stage: Mapped[Optional[ContentStage]] = mapped_column(
        SQLEnum(ContentStage, name="content_stage_enum", values_callable=lambda obj: [e.value for e in obj]),
        nullable=True, index=True,
    )

    # Source type - what kind of sources this content was generated from
    source_type: Mapped[ContentSourceType] = mapped_column(
        SQLEnum(ContentSourceType, name="content_source_type_enum", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=ContentSourceType.DOCUMENTS
    )

    # Timestamp fields
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    total_duration: Mapped[Optional[float]] = mapped_column(Float)

    # Token usage tracking
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Warning field for storing warnings like oversized input
    warning: Mapped[Optional[str]] = mapped_column(Text)

    # The actual content of the generated content
    content: Mapped[Optional[str]] = mapped_column(Text, deferred=True)

    # Generated summary of the content (optional)
    summary: Mapped[Optional[str]] = mapped_column(Text)

    # Full-text search vector (maintained by PostgreSQL trigger)
    search_vector = mapped_column(TSVECTOR, nullable=True)

    # Model configuration reference
    model_config_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("model_configs.id", ondelete="SET NULL"), index=True)
    model_config: Mapped[Optional["ModelConfig"]] = relationship(
        "ModelConfig",
        foreign_keys=[model_config_id],
        lazy="selectin"
    )

    # Prompt references
    system_prompt_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("prompts.id", ondelete="SET NULL"), index=True)
    system_prompt: Mapped[Optional["Prompt"]] = relationship(
        "Prompt",
        foreign_keys=[system_prompt_id],
        lazy="selectin"
    )

    user_prompt_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("prompts.id", ondelete="SET NULL"), index=True)
    user_prompt: Mapped[Optional["Prompt"]] = relationship(
        "Prompt",
        foreign_keys=[user_prompt_id],
        lazy="selectin"
    )

    # Source relationships
    source_documents: Mapped[List["Document"]] = relationship(
        "Document",
        secondary=generated_content_document_association,
        backref="generated_content",
        lazy="select"
    )

    source_content: Mapped[List["GeneratedContent"]] = relationship(
        "GeneratedContent",
        secondary=generated_content_source_association,
        primaryjoin=id == generated_content_source_association.c.parent_content_id,
        secondaryjoin=id == generated_content_source_association.c.source_content_id,
        lazy="select",
        order_by="GeneratedContent.created_at.desc()"
    )

    # Explicit reverse relationship instead of backref to prevent accidental deep loading
    derived_content: Mapped[List["GeneratedContent"]] = relationship(
        "GeneratedContent",
        secondary=generated_content_source_association,
        primaryjoin=id == generated_content_source_association.c.source_content_id,
        secondaryjoin=id == generated_content_source_association.c.parent_content_id,
        lazy="noload",  # Force explicit loading to prevent accidental deep loading
        overlaps="source_content"
    )

    ratings: Mapped[Optional[List["Rating"]]] = relationship("Rating", back_populates="generated_content", lazy="noload")

    def __repr__(self) -> str:
        doc_type = f", doc_type='{self.document_type.value}'" if self.document_type else ""
        form_type = f", form_type='{self.form_type}'" if self.form_type else ""
        return f"<GeneratedContent(id={self.id}, source_type='{self.source_type.value}'{doc_type}{form_type}, hash='{self.content_hash[:12] if self.content_hash else None}')>" # noqa: E501


    def generate_content_hash(self) -> str:
        """Generate SHA256 hash of the content for URL identification."""
        if not self.content:
            return ""

        return hashlib.sha256(self.content.encode('utf-8')).hexdigest()

    def get_short_hash(self, length: int = 12) -> str:
        """Get shortened version of content hash for URLs."""
        if not self.content_hash:
            return ""
        return self.content_hash[:length]

    def update_content_hash(self):
        """Update the content hash based on current content."""
        self.content_hash = self.generate_content_hash()

    def get_direct_derivatives(self, session=None):
        """Get content that directly uses this as a source.

        Args:
            session: Optional database session. If not provided, uses default session.

        Returns:
            List of GeneratedContent objects that use this content as a source
        """
        if session is None:
            session = get_db_session()

        return session.query(GeneratedContent)\
            .join(generated_content_source_association,
                  generated_content_source_association.c.parent_content_id == GeneratedContent.id)\
            .filter(generated_content_source_association.c.source_content_id == self.id)\
            .all()

    def get_source_chain_depth(self, max_depth: int = 10, visited: Optional[set] = None) -> int:
        """Calculate maximum derivation depth with cycle detection.

        Args:
            max_depth: Maximum depth to traverse (prevents infinite recursion)
            visited: Set of visited content IDs for cycle detection

        Returns:
            Maximum depth of source chain
        """
        if visited is None:
            visited = set()

        # Cycle detection
        if self.id in visited or max_depth <= 0:
            return 0

        visited.add(self.id)

        if not self.source_content:
            return 0

        max_source_depth = 0
        for source in self.source_content:
            source_depth = source.get_source_chain_depth(max_depth - 1, visited.copy())
            max_source_depth = max(max_source_depth, source_depth)

        return max_source_depth + 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert GeneratedContent to dictionary for API responses."""
        return {
            "id": str(self.id),
            "content_hash": self.content_hash,
            "short_hash": self.get_short_hash(),
            "company_id": str(self.company_id) if self.company_id else None,
            "company_group_id": str(self.company_group_id) if self.company_group_id else None,
            "document_type": self.document_type.value if self.document_type else None,
            "form_type": self.form_type,
            "content_stage": self.content_stage.value if self.content_stage else None,
            "description": self.description,
            "source_type": self.source_type.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "total_duration": self.total_duration,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "warning": self.warning,
            "content": self.content,
            "summary": self.summary,
            "model_config_id": str(self.model_config_id) if self.model_config_id else None,
            "system_prompt_id": str(self.system_prompt_id) if self.system_prompt_id else None,
            "user_prompt_id": str(self.user_prompt_id) if self.user_prompt_id else None,
            "source_document_ids": [str(doc.id) for doc in self.source_documents],
            "source_content_ids": [str(content.id) for content in self.source_content],
            "derived_content_ids": [str(content.id) for content in self.derived_content] if hasattr(self, '_derived_content_loaded') else None,
        }


def get_generated_content_ids() -> List[UUID]:
    """Get a list of all generated content IDs in the database.

    Returns:
        List of generated content UUIDs
    """
    try:
        session = get_db_session()
        content_ids = [content_id for content_id, in session.query(GeneratedContent.id).all()]
        logger.info("retrieved_generated_content_ids", count=len(content_ids))
        return content_ids
    except Exception as e:
        logger.error("get_generated_content_ids_failed", error=str(e), exc_info=True)
        raise


def get_generated_content(content_id: Union[UUID, str]) -> Optional[GeneratedContent]:
    """Get generated content by its ID.

    Args:
        content_id: UUID of the generated content to retrieve

    Returns:
        GeneratedContent object if found, None otherwise
    """
    try:
        session = get_db_session()
        content = session.query(GeneratedContent).filter(GeneratedContent.id == content_id).first()
        if content:
            logger.info("retrieved_generated_content", content_id=str(content_id))
        else:
            logger.warning("generated_content_not_found", content_id=str(content_id))
        return content
    except Exception as e:
        logger.error("get_generated_content_failed", content_id=str(content_id), error=str(e), exc_info=True)
        raise


def get_generated_content_by_hash(content_hash: str) -> Optional[GeneratedContent]:
    """Get generated content by its content hash.

    Args:
        content_hash: Full or partial SHA256 hash of the content

    Returns:
        GeneratedContent object if found, None otherwise
    """
    try:
        session = get_db_session()

        # Try exact match first
        content = session.query(GeneratedContent).filter(GeneratedContent.content_hash == content_hash).first()

        # If no exact match and hash is short, try prefix match
        if not content and len(content_hash) < 64:
            content = session.query(GeneratedContent).filter(
                GeneratedContent.content_hash.like(f"{content_hash}%")
            ).first()

        if content:
            logger.info("retrieved_generated_content_by_hash", content_hash=content_hash)
        else:
            logger.warning("generated_content_not_found_by_hash", content_hash=content_hash)
        return content
    except Exception as e:
        logger.error("get_generated_content_by_hash_failed", content_hash=content_hash, error=str(e), exc_info=True)
        raise


def get_generated_content_by_company_and_ticker(ticker: str, content_hash: str) -> Optional[GeneratedContent]:
    """Get generated content by ticker and content hash (for URL routing).

    Args:
        ticker: Company ticker symbol
        content_hash: Full or partial SHA256 hash of the content

    Returns:
        GeneratedContent object if found, None otherwise
    """
    try:
        session = get_db_session()

        # Join with company to filter by ticker
        query = (
            session.query(GeneratedContent)
            .join(Company, GeneratedContent.company_id == Company.id)
            .filter(Company.ticker == ticker.upper())
        )

        # Try exact hash match first
        content = query.filter(GeneratedContent.content_hash == content_hash).first()

        # If no exact match and hash is short, try prefix match
        if not content and len(content_hash) < 64:
            content = query.filter(GeneratedContent.content_hash.like(f"{content_hash}%")).first()

        if content:
            logger.info("retrieved_generated_content_by_ticker_and_hash", ticker=ticker, content_hash=content_hash)
        else:
            logger.warning("generated_content_not_found_by_ticker_and_hash", ticker=ticker, content_hash=content_hash)
        return content
    except Exception as e:
        logger.error("get_generated_content_by_ticker_and_hash_failed",
                    ticker=ticker, content_hash=content_hash, error=str(e), exc_info=True)
        raise


def get_recent_generated_content_by_ticker(ticker: str, limit: int = 10) -> List[GeneratedContent]:
    """Get the most recent generated content for each document type by ticker.

    Args:
        ticker: Company ticker symbol
        limit: Maximum number of results to return

    Returns:
        List of GeneratedContent objects - the most recent content for each document type
    """
    try:
        session = get_db_session()

        # Subquery to get the most recent content for each document type
        subquery = (
            session.query(
                GeneratedContent.document_type,
                func.max(GeneratedContent.created_at).label('latest_date')
            )
            .join(Company, GeneratedContent.company_id == Company.id)
            .filter(Company.ticker == ticker.upper())
            .filter(GeneratedContent.document_type.is_not(None))
            .group_by(GeneratedContent.document_type)
            .subquery()
        )

        # Main query to get the actual content records
        content_list = (
            session.query(GeneratedContent)
            .join(Company, GeneratedContent.company_id == Company.id)
            .join(subquery,
                  (GeneratedContent.document_type == subquery.c.document_type) &
                  (GeneratedContent.created_at == subquery.c.latest_date))
            .filter(Company.ticker == ticker.upper())
            .limit(limit)
            .all()
        )

        logger.info("retrieved_recent_generated_content_by_ticker", ticker=ticker, count=len(content_list))
        return content_list
    except Exception as e:
        logger.error("get_recent_generated_content_by_ticker_failed", ticker=ticker, error=str(e), exc_info=True)
        raise


def get_all_generated_content_by_ticker(ticker: str, limit: int = 100) -> List[GeneratedContent]:
    """Get all generated content for a company by ticker, ordered by most recent first.

    Unlike get_recent_generated_content_by_ticker, this returns every row
    (no GROUP BY) with deferred content loading for lightweight listing.

    Args:
        ticker: Company ticker symbol
        limit: Maximum number of results to return

    Returns:
        List of GeneratedContent objects
    """
    try:
        from sqlalchemy.orm import defer

        session = get_db_session()

        content_list = (
            session.query(GeneratedContent)
            .join(Company, GeneratedContent.company_id == Company.id)
            .filter(Company.ticker == ticker.upper())
            .options(defer(GeneratedContent.content))
            .order_by(GeneratedContent.created_at.desc())
            .limit(limit)
            .all()
        )

        logger.info("retrieved_all_generated_content_by_ticker", ticker=ticker, count=len(content_list))
        return content_list
    except Exception as e:
        logger.error("get_all_generated_content_by_ticker_failed", ticker=ticker, error=str(e), exc_info=True)
        raise


def get_aggregate_summaries_by_ticker(
    ticker: str, limit: int = 10, form_type: Optional[str] = None,
) -> List[GeneratedContent]:
    """Get the most recent aggregate summary content for a company by ticker.

    Uses structured ``content_stage`` field with a legacy fallback on
    ``description LIKE '%aggregate_summary%'`` for rows created before the
    metadata migration.

    Args:
        ticker: Company ticker symbol
        limit: Maximum number of results to return (default: 10)
        form_type: Optional form type filter (e.g. "10-K")

    Returns:
        List of GeneratedContent objects - the most recent aggregate summaries
    """
    try:
        session = get_db_session()

        stage_filter = or_(
            GeneratedContent.content_stage == ContentStage.AGGREGATE_SUMMARY,
            GeneratedContent.description.contains('aggregate_summary'),
        )

        # Group by (document_type, form_type) when structured, fall back to description
        group_col = func.coalesce(
            func.concat(
                func.cast(GeneratedContent.document_type, String),
                ':',
                GeneratedContent.form_type,
            ),
            GeneratedContent.description,
        )

        base_filter = [
            Company.ticker == ticker.upper(),
            stage_filter,
        ]
        if form_type:
            base_filter.append(GeneratedContent.form_type == form_type)

        subquery = (
            session.query(
                group_col.label('group_key'),
                func.max(GeneratedContent.created_at).label('latest_date'),
            )
            .join(Company, GeneratedContent.company_id == Company.id)
            .filter(*base_filter)
            .group_by(group_col)
            .subquery()
        )

        content_list = (
            session.query(GeneratedContent)
            .join(Company, GeneratedContent.company_id == Company.id)
            .join(subquery,
                  (group_col == subquery.c.group_key) &
                  (GeneratedContent.created_at == subquery.c.latest_date))
            .filter(Company.ticker == ticker.upper())
            .filter(stage_filter)
            .limit(limit)
            .all()
        )

        logger.info("retrieved_aggregate_summaries_by_ticker", ticker=ticker, count=len(content_list))
        return content_list
    except Exception as e:
        logger.error("get_aggregate_summaries_by_ticker_failed", ticker=ticker, error=str(e), exc_info=True)
        raise


def create_generated_content(content_data: Dict[str, Any]) -> tuple[GeneratedContent, bool]:
    """Create new generated content.

    Args:
        content_data: Dictionary containing generated content data

    Returns:
        Tuple of (GeneratedContent object, was_created: bool).
        was_created is True if a new content was created, False if existing was returned.
    """
    try:
        session = get_db_session()

        # Create a temporary content object to generate content hash
        temp_content = GeneratedContent(**content_data)
        if temp_content.content and not temp_content.content_hash:
            temp_content.update_content_hash()
        content_hash = temp_content.content_hash

        # Check if content with the same content hash already exists
        if content_hash:
            existing_content = session.query(GeneratedContent).filter(GeneratedContent.content_hash == content_hash).first()
            if existing_content:
                logger.info("found_existing_generated_content_with_same_content",
                           content_id=str(existing_content.id),
                           description=existing_content.description,
                           content_hash=content_hash)
                return existing_content, False

        # Create new content if no duplicate found
        content = GeneratedContent(**content_data)
        if content.content and not content.content_hash:
            content.update_content_hash()

        session.add(content)
        session.commit()
        logger.info("created_generated_content", content_id=str(content.id), hash=content.get_short_hash())
        return content, True
    except Exception as e:
        session.rollback()
        logger.error("create_generated_content_failed", error=str(e), exc_info=True)
        raise


def update_generated_content(content_id: Union[UUID, str], content_data: Dict[str, Any]) -> Optional[GeneratedContent]:
    """Update existing generated content.

    Args:
        content_id: UUID of the generated content to update
        content_data: Dictionary containing updated content data

    Returns:
        Updated GeneratedContent object if found, None otherwise
    """
    try:
        session = get_db_session()
        content = session.query(GeneratedContent).filter(GeneratedContent.id == content_id).first()

        if content:
            # Store original content to check if hash needs updating
            original_content = content.content

            for key, value in content_data.items():
                if hasattr(content, key):
                    setattr(content, key, value)

            # Update hash if content changed
            if 'content' in content_data and content.content != original_content:
                content.update_content_hash()

            session.commit()
            logger.info("updated_generated_content", content_id=str(content_id))
            return content
        else:
            logger.warning("generated_content_not_found_for_update", content_id=str(content_id))
            return None
    except Exception as e:
        session.rollback()
        logger.error("update_generated_content_failed", content_id=str(content_id), error=str(e), exc_info=True)
        raise


def delete_generated_content(content_id: Union[UUID, str]) -> bool:
    """Delete generated content.

    Args:
        content_id: UUID of the generated content to delete

    Returns:
        True if content was deleted, False if not found
    """
    try:
        session = get_db_session()
        content = session.query(GeneratedContent).filter(GeneratedContent.id == content_id).first()

        if content:
            session.delete(content)
            session.commit()
            logger.info("deleted_generated_content", content_id=str(content_id))
            return True
        else:
            logger.warning("generated_content_not_found_for_deletion", content_id=str(content_id))
            return False
    except Exception as e:
        session.rollback()
        logger.error("delete_generated_content_failed", content_id=str(content_id), error=str(e), exc_info=True)
        raise


def find_existing_content_for_document(
    document_id: Union[UUID, str],
    system_prompt_id: Union[UUID, str],
    model_config_id: Union[UUID, str],
) -> Optional[GeneratedContent]:
    """Find existing generated content for a (document, prompt, model_config) triple.

    Used to skip duplicate LLM calls when content has already been generated
    for the same source document with the same prompt and model configuration.

    Returns:
        The first matching GeneratedContent, or None.
    """
    session = get_db_session()
    return (
        session.query(GeneratedContent)
        .join(generated_content_document_association,
              GeneratedContent.id == generated_content_document_association.c.generated_content_id)
        .filter(
            generated_content_document_association.c.document_id == document_id,
            GeneratedContent.system_prompt_id == system_prompt_id,
            GeneratedContent.model_config_id == model_config_id,
        )
        .first()
    )


def get_generated_content_by_source_document(document_id: Union[UUID, str]) -> List[GeneratedContent]:
    """Get all generated content that uses a specific document as a source.

    Args:
        document_id: UUID of the document to filter content by

    Returns:
        List of GeneratedContent objects that reference the specified document
    """
    try:
        session = get_db_session()

        content_list = (
            session.query(GeneratedContent)
            .join(generated_content_document_association,
                  GeneratedContent.id == generated_content_document_association.c.generated_content_id)
            .filter(generated_content_document_association.c.document_id == document_id)
            .all()
        )

        logger.info("retrieved_generated_content_by_source_document",
                   document_id=str(document_id), count=len(content_list))
        return content_list
    except Exception as e:
        logger.error("get_generated_content_by_source_document_failed",
                    document_id=str(document_id), error=str(e), exc_info=True)
        raise


def get_generated_content_by_source_content(source_content_id: Union[UUID, str]) -> List[GeneratedContent]:
    """Get all generated content that uses another generated content as a source.

    Args:
        source_content_id: UUID of the source content to filter by

    Returns:
        List of GeneratedContent objects that reference the specified source content
    """
    try:
        session = get_db_session()

        content_list = (
            session.query(GeneratedContent)
            .join(generated_content_source_association,
                  GeneratedContent.id == generated_content_source_association.c.parent_content_id)
            .filter(generated_content_source_association.c.source_content_id == source_content_id)
            .all()
        )

        logger.info("retrieved_generated_content_by_source_content",
                   source_content_id=str(source_content_id), count=len(content_list))
        return content_list
    except Exception as e:
        logger.error("get_generated_content_by_source_content_failed",
                    source_content_id=str(source_content_id), error=str(e), exc_info=True)
        raise


def get_content_with_sources_loaded(content_id: Union[UUID, str]) -> Optional[GeneratedContent]:
    """Get content with sources efficiently loaded using selectinload.

    Args:
        content_id: UUID of the content to retrieve

    Returns:
        GeneratedContent with sources pre-loaded, or None if not found
    """
    try:
        from sqlalchemy.orm import selectinload

        session = get_db_session()
        content = session.query(GeneratedContent)\
            .options(selectinload(GeneratedContent.source_content))\
            .options(selectinload(GeneratedContent.source_documents))\
            .filter_by(id=content_id)\
            .first()

        if content:
            logger.info("retrieved_content_with_sources_loaded", content_id=str(content_id))
        else:
            logger.warning("content_not_found_for_sources_loading", content_id=str(content_id))

        return content
    except Exception as e:
        logger.error("get_content_with_sources_loaded_failed", content_id=str(content_id), error=str(e), exc_info=True)
        raise


def get_frontpage_summary_by_ticker(
    ticker: str, form_type: Optional[str] = None,
) -> Optional[str]:
    """Get the most recent frontpage summary content for a company by ticker.

    Uses structured ``content_stage`` + ``document_type`` fields with a
    legacy fallback on the description string for pre-migration rows.

    Args:
        ticker: Company ticker symbol
        form_type: Optional form type filter (e.g. "10-K")

    Returns:
        Content string of the frontpage summary if found, None otherwise
    """
    try:
        session = get_db_session()

        stage_filter = or_(
            (GeneratedContent.content_stage == ContentStage.FRONTPAGE_SUMMARY) &
            (GeneratedContent.document_type == DocumentType.DESCRIPTION),
            GeneratedContent.description == 'business_description_frontpage_summary',
        )

        query = (
            session.query(GeneratedContent)
            .join(Company, GeneratedContent.company_id == Company.id)
            .filter(Company.ticker == ticker.upper())
            .filter(stage_filter)
        )
        if form_type:
            query = query.filter(GeneratedContent.form_type == form_type)

        content = query.order_by(GeneratedContent.created_at.desc()).first()

        if content and content.content:
            logger.info("retrieved_frontpage_summary_by_ticker", ticker=ticker, content_id=str(content.id))
            return content.content
        else:
            logger.warning("frontpage_summary_not_found_by_ticker", ticker=ticker)
            return None

    except Exception as e:
        logger.error("get_frontpage_summary_by_ticker_failed", ticker=ticker, error=str(e), exc_info=True)
        raise


def get_generated_content_by_document_ids(document_ids: List[UUID]) -> Dict[UUID, List[GeneratedContent]]:
    """Batch-fetch generated content for multiple document IDs.

    Joins through generated_content_document_association to get all generated content
    linked to the given documents. Uses deferred content loading to avoid fetching
    full LLM output bodies — only summary/metadata fields are loaded.

    Args:
        document_ids: List of document UUIDs to fetch content for

    Returns:
        Dict mapping document_id -> list of GeneratedContent objects
    """
    if not document_ids:
        return {}

    try:
        from collections import defaultdict
        from sqlalchemy.orm import defer

        session = get_db_session()

        # Query generated content joined through the association table
        rows = (
            session.query(GeneratedContent, generated_content_document_association.c.document_id)
            .join(
                generated_content_document_association,
                GeneratedContent.id == generated_content_document_association.c.generated_content_id,
            )
            .filter(generated_content_document_association.c.document_id.in_(document_ids))
            .options(defer(GeneratedContent.content))
            .all()
        )

        result: Dict[UUID, List[GeneratedContent]] = defaultdict(list)
        for gc, doc_id in rows:
            result[doc_id].append(gc)

        logger.info("batch_fetched_generated_content_by_document_ids",
                    document_count=len(document_ids),
                    content_count=sum(len(v) for v in result.values()))
        return dict(result)
    except Exception as e:
        logger.error("get_generated_content_by_document_ids_failed",
                    error=str(e), exc_info=True)
        raise


def get_company_group_frontpage_summary(group_id: UUID) -> Optional[str]:
    """Get the most recent company group frontpage summary for a given group.

    Args:
        group_id: UUID of the company group

    Returns:
        Content string of the frontpage summary if found, None otherwise
    """
    try:
        session = get_db_session()

        content = (
            session.query(GeneratedContent)
            .filter(
                GeneratedContent.company_group_id == group_id,
                GeneratedContent.content_stage == ContentStage.COMPANY_GROUP_FRONTPAGE,
            )
            .order_by(GeneratedContent.created_at.desc())
            .first()
        )

        if content and content.content:
            logger.info("retrieved_company_group_frontpage_summary", group_id=str(group_id))
            return content.content
        else:
            logger.warning("company_group_frontpage_summary_not_found", group_id=str(group_id))
            return None
    except Exception as e:
        logger.error("get_company_group_frontpage_summary_failed", group_id=str(group_id), error=str(e), exc_info=True)
        raise


def get_company_group_analysis(group_id: UUID, limit: int = 5) -> List[GeneratedContent]:
    """Get the most recent company group analyses for a given group.

    Uses structured ``content_stage`` field with a legacy fallback on
    the description string for pre-migration rows.

    Args:
        group_id: UUID of the company group
        limit: Maximum number of results to return

    Returns:
        List of GeneratedContent objects that are group analyses
    """
    try:
        session = get_db_session()

        content_list = (
            session.query(GeneratedContent)
            .filter(
                GeneratedContent.company_group_id == group_id,
                or_(
                    GeneratedContent.content_stage == ContentStage.COMPANY_GROUP_ANALYSIS,
                    GeneratedContent.description.contains("company_group_analysis"),
                ),
            )
            .order_by(GeneratedContent.created_at.desc())
            .limit(limit)
            .all()
        )

        logger.info("retrieved_company_group_analysis", group_id=str(group_id), count=len(content_list))
        return content_list
    except Exception as e:
        logger.error("get_company_group_analysis_failed", group_id=str(group_id), error=str(e), exc_info=True)
        raise
