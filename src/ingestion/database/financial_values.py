from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from sqlalchemy import Date, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.ingestion.database.base import Base, get_db_session
from src.ingestion.utils.logging import get_logger

# Initialize structlog
logger = get_logger(__name__)

class FinancialValue(Base):
    """FinancialValue model representing financial data points for companies."""

    __tablename__ = "financial_values"

    # Primary identifier
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Foreign keys
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    concept_id: Mapped[UUID] = mapped_column(ForeignKey("financial_concepts.id", ondelete="CASCADE"), index=True)
    filing_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("filings.id", ondelete="CASCADE"), index=True, nullable=True)

    # Relationships
    company = relationship("Company", back_populates="financial_values")
    concept = relationship("FinancialConcept", back_populates="financial_values")
    filing = relationship("Filing", back_populates="financial_values")

    # Financial value details
    value_date: Mapped[date] = mapped_column(Date, index=True)
    value: Mapped[Decimal] = mapped_column(Numeric(precision=28, scale=10))

    def __repr__(self) -> str:
        return f"<FinancialValue(id={self.id}, company_id={self.company_id}, concept_id={self.concept_id}, value_date={self.value_date})>"


def get_financial_value_ids() -> List[UUID]:
    """Get a list of all financial value IDs in the database.

    Returns:
        List of financial value UUIDs
    """
    try:
        session = get_db_session()
        value_ids = [value_id for value_id, in session.query(FinancialValue.id).all()]
        logger.info("retrieved_financial_value_ids", count=len(value_ids))
        return value_ids
    except Exception as e:
        logger.error("get_financial_value_ids_failed", error=str(e), exc_info=True)
        raise


def get_financial_value(value_id: Union[UUID, str]) -> Optional[FinancialValue]:
    """Get a financial value by its ID.

    Args:
        value_id: UUID of the financial value to retrieve

    Returns:
        FinancialValue object if found, None otherwise
    """
    try:
        session = get_db_session()
        value = session.query(FinancialValue).filter(FinancialValue.id == value_id).first()
        if value:
            logger.info("retrieved_financial_value", value_id=str(value_id))
        else:
            logger.warning("financial_value_not_found", value_id=str(value_id))
        return value
    except Exception as e:
        logger.error("get_financial_value_failed", value_id=str(value_id), error=str(e), exc_info=True)
        raise


def create_financial_value(value_data: Dict[str, Any]) -> FinancialValue:
    """Create a new financial value in the database.

    Args:
        value_data: Dictionary containing financial value attributes

    Returns:
        Newly created FinancialValue object
    """
    try:
        session = get_db_session()
        financial_value = FinancialValue(**value_data)
        session.add(financial_value)
        session.commit()
        logger.info(
            "created_financial_value",
            value_id=str(financial_value.id),
            company_id=str(financial_value.company_id),
            concept_id=str(financial_value.concept_id)
        )
        return financial_value
    except Exception as e:
        session.rollback()
        logger.error("create_financial_value_failed", error=str(e), exc_info=True)
        raise


def update_financial_value(value_id: Union[UUID, str], value_data: Dict[str, Any]) -> Optional[FinancialValue]:
    """Update an existing financial value in the database.

    Args:
        value_id: UUID of the financial value to update
        value_data: Dictionary containing financial value attributes to update

    Returns:
        Updated FinancialValue object if found, None otherwise
    """
    try:
        session = get_db_session()
        financial_value = session.query(FinancialValue).filter(FinancialValue.id == value_id).first()
        if not financial_value:
            logger.warning("update_financial_value_not_found", value_id=str(value_id))
            return None

        for key, value in value_data.items():
            if hasattr(financial_value, key):
                setattr(financial_value, key, value)
            else:
                logger.warning("update_financial_value_invalid_attribute", value_id=str(value_id), attribute=key)

        session.commit()
        logger.info(
            "updated_financial_value",
            value_id=str(financial_value.id),
            company_id=str(financial_value.company_id),
            concept_id=str(financial_value.concept_id)
        )
        return financial_value
    except Exception as e:
        session.rollback()
        logger.error("update_financial_value_failed", value_id=str(value_id), error=str(e), exc_info=True)
        raise


def delete_financial_value(value_id: Union[UUID, str]) -> bool:
    """Delete a financial value from the database.

    Args:
        value_id: UUID of the financial value to delete

    Returns:
        True if financial value was deleted, False if not found
    """
    try:
        session = get_db_session()
        financial_value = session.query(FinancialValue).filter(FinancialValue.id == value_id).first()
        if not financial_value:
            logger.warning("delete_financial_value_not_found", value_id=str(value_id))
            return False

        session.delete(financial_value)
        session.commit()
        logger.info("deleted_financial_value", value_id=str(value_id))
        return True
    except Exception as e:
        session.rollback()
        logger.error("delete_financial_value_failed", value_id=str(value_id), error=str(e), exc_info=True)
        raise
