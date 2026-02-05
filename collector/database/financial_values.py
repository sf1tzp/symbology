from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from collector.database.base import Base, get_db_session
from collector.utils.logging import get_logger
from uuid_extensions import uuid7

# Initialize structlog
logger = get_logger(__name__)

class FinancialValue(Base):
    """FinancialValue model representing financial data points for companies."""

    __tablename__ = "financial_values"

    # Primary identifier
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

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


def upsert_financial_value(company_id: UUID, concept_id: UUID, value_date: date,
                          value: Decimal, filing_id: Optional[UUID] = None) -> FinancialValue:
    """Create or update a financial value for a company, concept, and date.

    Args:
        company_id: UUID of the company
        concept_id: UUID of the financial concept
        value_date: Date of the financial value
        value: Numeric value of the financial data point
        filing_id: UUID of the related filing (optional)

    Returns:
        Created or updated FinancialValue object
    """
    try:
        session = get_db_session()

        # Build query
        query = session.query(FinancialValue).filter(
            FinancialValue.company_id == company_id,
            FinancialValue.concept_id == concept_id,
            FinancialValue.value_date == value_date
        )

        if filing_id:
            query = query.filter(FinancialValue.filing_id == filing_id)
        else:
            query = query.filter(FinancialValue.filing_id.is_(None))

        existing_value = query.first()

        if existing_value:
            # Update value
            existing_value.value = value
            session.commit()
            logger.info("updated_existing_financial_value",
                       value_id=str(existing_value.id),
                       company_id=str(company_id),
                       concept_id=str(concept_id))
            return existing_value
        else:
            # Create new financial value
            value_data = {
                'company_id': company_id,
                'concept_id': concept_id,
                'value_date': value_date,
                'value': value
            }
            if filing_id:
                value_data['filing_id'] = filing_id

            financial_value = FinancialValue(**value_data)
            session.add(financial_value)
            session.commit()
            logger.info("created_new_financial_value",
                       value_id=str(financial_value.id),
                       company_id=str(company_id),
                       concept_id=str(concept_id))
            return financial_value
    except Exception as e:
        session.rollback()
        logger.error("upsert_financial_value_failed", error=str(e), exc_info=True)
        raise

def get_financial_values_by_filing(filing_id: UUID) -> List[FinancialValue]:
    """Get all financial values associated with a filing.

    Args:
        filing_id: UUID of the filing

    Returns:
        List of FinancialValue objects
    """
    try:
        session = get_db_session()
        values = session.query(FinancialValue).filter(FinancialValue.filing_id == filing_id).all()
        logger.info("retrieved_financial_values_by_filing",
                   filing_id=str(filing_id),
                   count=len(values))
        return values
    except Exception as e:
        logger.error("get_financial_values_by_filing_failed",
                    filing_id=str(filing_id),
                    error=str(e),
                    exc_info=True)
        raise

def get_financial_values_by_company_and_date(company_id: UUID, value_date: date) -> List[FinancialValue]:
    """Get all financial values for a company on a specific date.

    Args:
        company_id: UUID of the company
        value_date: Date of the financial values

    Returns:
        List of FinancialValue objects
    """
    try:
        session = get_db_session()
        values = session.query(FinancialValue).filter(
            FinancialValue.company_id == company_id,
            FinancialValue.value_date == value_date
        ).all()
        logger.info("retrieved_financial_values_by_company_and_date",
                   company_id=str(company_id),
                   value_date=str(value_date),
                   count=len(values))
        return values
    except Exception as e:
        logger.error("get_financial_values_by_company_and_date_failed",
                    company_id=str(company_id),
                    value_date=str(value_date),
                    error=str(e),
                    exc_info=True)
        raise
