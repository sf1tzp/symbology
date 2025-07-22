from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union
from uuid import UUID

from sqlalchemy import Column, DateTime, Float, ForeignKey, func, Integer, String, Table, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import attributes, Mapped, mapped_column, relationship
from src.database.base import Base, get_db_session
from src.database.companies import Company
from src.database.documents import DocumentType
from src.utils.logging import get_logger
from uuid_extensions import uuid7

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from src.database.completions import Completion
    from src.database.prompts import Prompt
    from src.database.ratings import Rating

# Initialize structlog
logger = get_logger(__name__)

# Association table for many-to-many relationship between Aggregate and Completion
aggregate_completion_association = Table(
    "aggregate_completion_association",
    Base.metadata,
    Column("aggregate_id", ForeignKey("aggregates.id"), primary_key=True),
    Column("completion_id", ForeignKey("completions.id"), primary_key=True)
)

class Aggregate(Base):
    """Aggregate model representing AI aggregates from multiple completions."""

    __tablename__ = "aggregates"

    # Primary identifier
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

    # Company Foreign Key
    company_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    company: Mapped[Optional["Company"]] = relationship(
        "Company",
        foreign_keys=[company_id],
        backref="aggregates"
    )

    # document_type
    document_type: Mapped[Optional[DocumentType]] = mapped_column(
        SQLEnum(DocumentType, name="document_type_enum"), nullable=True
    )
    # Timestamp fields
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    total_duration: Mapped[Optional[float]] = mapped_column(Float)

    # The actual content of the aggregate
    content: Mapped[Optional[str]] = mapped_column(Text)

    # Generated summary of the aggregate content
    summary: Mapped[Optional[str]] = mapped_column(Text)

    source_completions: Mapped[List["Completion"]] = relationship(
        "Completion",
        secondary=aggregate_completion_association,
        backref="aggregates"
    )

    system_prompt_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("prompts.id", ondelete="SET NULL"), index=True)
    system_prompt: Mapped[Optional["Prompt"]] = relationship(
        "Prompt",
        foreign_keys=[system_prompt_id],
    )

    # OpenAI parameters
    model: Mapped[str] = mapped_column(String(50))
    temperature: Mapped[Optional[float]] = mapped_column(Float, default=0.7)
    top_p: Mapped[Optional[float]] = mapped_column(Float, default=1.0)
    top_k: Mapped[Optional[float]] = mapped_column(Integer, default=20)
    num_ctx: Mapped[Optional[int]] = mapped_column(Integer, default=4096)

    ratings: Mapped[Optional[List["Rating"]]] = relationship("Rating", back_populates="aggregate")

    def __repr__(self) -> str:
        return f"<Aggregate(id={self.id}, model='{self.model}')>"


def get_aggregate_ids() -> List[UUID]:
    """Get a list of all aggregate IDs in the database.

    Returns:
        List of aggregate UUIDs
    """
    try:
        session = get_db_session()
        aggregate_ids = [aggregate_id for aggregate_id, in session.query(Aggregate.id).all()]
        logger.info("retrieved_aggregate_ids", count=len(aggregate_ids))
        return aggregate_ids
    except Exception as e:
        logger.error("get_aggregate_ids_failed", error=str(e), exc_info=True)
        raise


def get_aggregates_by_completion(completion_id: Union[UUID, str]) -> List[Aggregate]:
    """Get all aggregates that use a specific completion as a source.

    Args:
        completion_id: UUID of the completion to filter aggregates by

    Returns:
        List of Aggregate objects that reference the specified completion
    """
    try:
        session = get_db_session()

        # Query aggregates that have the specified completion in source_completions
        aggregates = (
            session.query(Aggregate)
            .join(aggregate_completion_association, Aggregate.id == aggregate_completion_association.c.aggregate_id)
            .filter(aggregate_completion_association.c.completion_id == completion_id)
            .all()
        )

        logger.info("retrieved_aggregates_by_completion", completion_id=str(completion_id), count=len(aggregates))
        return aggregates
    except Exception as e:
        logger.error("get_aggregates_by_completion_failed", completion_id=str(completion_id),
                     error=str(e), exc_info=True)
        raise


def get_aggregate(aggregate_id: Union[UUID, str]) -> Optional[Aggregate]:
    """Get an aggregate by its ID.

    Args:
        aggregate_id: UUID of the aggregate to retrieve

    Returns:
        Aggregate object if found, None otherwise
    """
    try:
        session = get_db_session()
        aggregate = session.query(Aggregate).filter(Aggregate.id == aggregate_id).first()
        if aggregate:
            logger.info("retrieved_aggregate", aggregate_id=str(aggregate_id))
        else:
            logger.warning("aggregate_not_found", aggregate_id=str(aggregate_id))
        return aggregate
    except Exception as e:
        logger.error("get_aggregate_failed", aggregate_id=str(aggregate_id), error=str(e), exc_info=True)
        raise


def create_aggregate(aggregate_data: Dict[str, Any]) -> Aggregate:
    """Create a new aggregate in the database.

    Args:
        aggregate_data: Dictionary containing aggregate attributes

    Returns:
        Newly created Aggregate object
    """
    try:
        session = get_db_session()

        # Handle completion associations if provided
        completions = aggregate_data.pop('completions', None)

        aggregate = Aggregate(**aggregate_data)
        session.add(aggregate)

        # Add completion associations if provided
        if completions:
            aggregate.source_completions.extend(completions)

        session.commit()
        logger.info("created_aggregate", aggregate_id=str(aggregate.id), model=aggregate.model)
        return aggregate
    except Exception as e:
        session.rollback()
        logger.error("create_aggregate_failed", error=str(e), exc_info=True)
        raise


def update_aggregate(aggregate_id: Union[UUID, str], aggregate_data: Dict[str, Any]) -> Optional[Aggregate]:
    """Update an existing aggregate in the database.

    Args:
        aggregate_id: UUID of the aggregate to update
        aggregate_data: Dictionary containing aggregate attributes to update

    Returns:
        Updated Aggregate object if found, None otherwise
    """
    try:
        session = get_db_session()
        aggregate = session.query(Aggregate).filter(Aggregate.id == aggregate_id).first()
        if not aggregate:
            logger.warning("update_aggregate_not_found", aggregate_id=str(aggregate_id))
            return None

        # Handle completion associations if provided
        if 'completion_ids' in aggregate_data:
            from src.database.completions import Completion
            completion_ids = aggregate_data.pop('completion_ids')

            # Clear existing associations and add new ones
            aggregate.source_completions.clear()
            completions = session.query(Completion).filter(Completion.id.in_(completion_ids)).all()
            aggregate.source_completions.extend(completions)

        for key, value in aggregate_data.items():
            if hasattr(aggregate, key):
                setattr(aggregate, key, value)
                # Flag JSON fields as modified to ensure changes are detected
                if key == 'content':
                    attributes.flag_modified(aggregate, key)
            else:
                logger.warning("update_aggregate_invalid_attribute", aggregate_id=str(aggregate_id), attribute=key)

        session.commit()
        logger.info("updated_aggregate", aggregate_id=str(aggregate.id))
        return aggregate
    except Exception as e:
        session.rollback()
        logger.error("update_aggregate_failed", aggregate_id=str(aggregate_id), error=str(e), exc_info=True)
        raise


def delete_aggregate(aggregate_id: Union[UUID, str]) -> bool:
    """Delete an aggregate from the database.

    Args:
        aggregate_id: UUID of the aggregate to delete

    Returns:
        True if aggregate was deleted, False if not found
    """
    try:
        session = get_db_session()
        aggregate = session.query(Aggregate).filter(Aggregate.id == aggregate_id).first()
        if not aggregate:
            logger.warning("delete_aggregate_not_found", aggregate_id=str(aggregate_id))
            return False

        session.delete(aggregate)
        session.commit()
        logger.info("deleted_aggregate", aggregate_id=str(aggregate_id))
        return True
    except Exception as e:
        session.rollback()
        logger.error("delete_aggregate_failed", aggregate_id=str(aggregate_id), error=str(e), exc_info=True)
        raise


def get_recent_aggregates_by_company(company_id: Union[UUID, str]) -> List[Aggregate]:
    """Get the most recent aggregates for each document type associated with a company.

    Args:
        company_id: UUID of the company to filter aggregates by

    Returns:
        List of Aggregate objects - the most recent aggregate for each document type
    """
    try:
        session = get_db_session()

        # Subquery to get the max created_at for each document_type for this company
        max_dates_subquery = (
            session.query(
                Aggregate.document_type,
                func.max(Aggregate.created_at).label('max_created_at')
            )
            .filter(Aggregate.company_id == company_id)
            .filter(Aggregate.document_type.isnot(None))
            .group_by(Aggregate.document_type)
            .subquery()
        )

        # Main query to get the actual aggregates
        aggregates = (
            session.query(Aggregate)
            .join(
                max_dates_subquery,
                (Aggregate.document_type == max_dates_subquery.c.document_type) &
                (Aggregate.created_at == max_dates_subquery.c.max_created_at)
            )
            .filter(Aggregate.company_id == company_id)
            .order_by(Aggregate.document_type)
            .all()
        )

        logger.info(
            "retrieved_recent_aggregates_by_company",
            company_id=str(company_id),
            count=len(aggregates),
            document_types=[agg.document_type.value if agg.document_type else None for agg in aggregates]
        )
        return aggregates
    except Exception as e:
        logger.error(
            "get_recent_aggregates_by_company_failed",
            company_id=str(company_id),
            error=str(e),
            exc_info=True
        )
        raise


def get_recent_aggregates_by_ticker(ticker: str) -> List[Aggregate]:
    """Get the most recent aggregates for each document type associated with a company by ticker.

    Args:
        ticker: Ticker symbol of the company

    Returns:
        List of Aggregate objects - the most recent aggregate for each document type
    """
    try:
        # First get the company by ticker
        from src.database.companies import get_company_by_ticker
        company = get_company_by_ticker(ticker)

        if not company:
            logger.warning("get_recent_aggregates_by_ticker_company_not_found", ticker=ticker)
            return []

        return get_recent_aggregates_by_company(company.id)
    except Exception as e:
        logger.error(
            "get_recent_aggregates_by_ticker_failed",
            ticker=ticker,
            error=str(e),
            exc_info=True
        )
        raise