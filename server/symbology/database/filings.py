from datetime import date
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union
from uuid import UUID

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from symbology.database.base import Base, get_db_session
from symbology.database.companies import Company
from symbology.utils.logging import get_logger
from uuid_extensions import uuid7

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from symbology.database.documents import Document
    from symbology.database.financial_values import FinancialValue

# Initialize structlog
logger = get_logger(__name__)

class Filing(Base):
    """Filing model representing SEC filings information."""

    __tablename__ = "filings"

    # Primary identifier
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

    # Foreign keys
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)

    # Relationships
    company: Mapped[Company] = relationship("Company", back_populates="filings", lazy="joined")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="filing", cascade="all, delete-orphan", lazy="selectin")
    financial_values: Mapped[List["FinancialValue"]] = relationship("FinancialValue", back_populates="filing", cascade="all, delete-orphan", lazy="noload")

    # Filing details
    accession_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    form: Mapped[str] = mapped_column(String(20), index=True)
    filing_date: Mapped[date] = mapped_column(Date, index=True)
    period_of_report: Mapped[Optional[date]] = mapped_column(Date, index=True)
    url: Mapped[Optional[str]] = mapped_column(String(255))

    # Full-text search vector (maintained by PostgreSQL trigger)
    search_vector = mapped_column(TSVECTOR, nullable=True)

    def __repr__(self) -> str:
        return f"{self.company.ticker} {self.period_of_report.year} {self.form}"

    @property
    def fiscal_year(self) -> str:
        return self.period_of_report.year


def get_filing_ids() -> List[UUID]:
    """Get a list of all filing IDs in the database.

    Returns:
        List of filing UUIDs
    """
    try:
        session = get_db_session()
        filing_ids = [filing_id for filing_id, in session.query(Filing.id).all()]
        logger.info("retrieved_filing_ids", count=len(filing_ids))
        return filing_ids
    except Exception as e:
        logger.error("get_filing_ids_failed", error=str(e), exc_info=True)
        raise


def get_filing(filing_id: Union[UUID, str]) -> Optional[Filing]:
    """Get a filing by its ID.

    Args:
        filing_id: UUID of the filing to retrieve

    Returns:
        Filing object if found, None otherwise
    """
    try:
        session = get_db_session()
        filing = session.query(Filing).filter(Filing.id == filing_id).first()
        if filing:
            logger.info("retrieved_filing", filing=filing)
        else:
            logger.warning("filing_not_found", filing_id=str(filing_id))
        return filing
    except Exception as e:
        logger.error("get_filing_failed", filing_id=str(filing_id), error=str(e), exc_info=True)
        raise


def create_filing(filing_data: Dict[str, Any]) -> Filing:
    """Create a new filing in the database.

    Args:
        filing_data: Dictionary containing filing attributes

    Returns:
        Newly created Filing object
    """
    try:
        session = get_db_session()

        # Check if company exists
        company_id = filing_data.get('company_id')
        company = session.query(Company).filter(Company.id == company_id).first()
        if not company:
            logger.error("create_filing_failed", error=f"Company with ID {company_id} not found")
            raise ValueError(f"Company with ID {company_id} not found")

        filing = Filing(**filing_data)
        session.add(filing)
        session.commit()
        logger.info("created_filing", filing_id=str(filing.id), company_id=str(filing.company_id))
        return filing
    except Exception as e:
        session.rollback()
        logger.error("create_filing_failed", error=str(e), exc_info=True)
        raise


def update_filing(filing_id: Union[UUID, str], filing_data: Dict[str, Any]) -> Optional[Filing]:
    """Update an existing filing in the database.

    Args:
        filing_id: UUID of the filing to update
        filing_data: Dictionary containing filing attributes to update

    Returns:
        Updated Filing object if found, None otherwise
    """
    try:
        session = get_db_session()
        filing = session.query(Filing).filter(Filing.id == filing_id).first()
        if not filing:
            logger.warning("update_filing_not_found", filing_id=str(filing_id))
            return None

        # If company_id is being updated, check if new company exists
        if 'company_id' in filing_data:
            company = session.query(Company).filter(Company.id == filing_data['company_id']).first()
            if not company:
                logger.error("update_filing_failed", error=f"Company with ID {filing_data['company_id']} not found")
                raise ValueError(f"Company with ID {filing_data['company_id']} not found")

        for key, value in filing_data.items():
            if hasattr(filing, key):
                setattr(filing, key, value)
            else:
                logger.warning("update_filing_invalid_attribute", filing_id=str(filing_id), attribute=key)

        session.commit()
        logger.info("updated_filing", filing_id=str(filing.id), company_id=str(filing.company_id))
        return filing
    except Exception as e:
        session.rollback()
        logger.error("update_filing_failed", filing_id=str(filing_id), error=str(e), exc_info=True)
        raise


def delete_filing(filing_id: Union[UUID, str]) -> bool:
    """Delete a filing from the database.

    Args:
        filing_id: UUID of the filing to delete

    Returns:
        True if filing was deleted, False if not found
    """
    try:
        session = get_db_session()
        filing = session.query(Filing).filter(Filing.id == filing_id).first()
        if not filing:
            logger.warning("delete_filing_not_found", filing_id=str(filing_id))
            return False

        session.delete(filing)
        session.commit()
        logger.info("deleted_filing", filing_id=str(filing_id))
        return True
    except Exception as e:
        session.rollback()
        logger.error("delete_filing_failed", filing_id=str(filing_id), error=str(e), exc_info=True)
        raise


def upsert_filing_by_accession_number(filing_data: Dict[str, Any]) -> Filing:
    """Create a filing or update it if it already exists based on accession number.

    Args:
        filing_data: Dictionary containing filing attributes

    Returns:
        Created or updated Filing object
    """
    try:
        session = get_db_session()
        accession_number = filing_data.get('accession_number')

        if not accession_number:
            logger.error("upsert_filing_failed", error="Accession number is required")
            raise ValueError("Accession number is required for filing upsert")

        existing_filing = session.query(Filing).filter(Filing.accession_number == accession_number).first()

        if existing_filing:
            # Update existing filing
            for key, value in filing_data.items():
                if hasattr(existing_filing, key):
                    setattr(existing_filing, key, value)

            session.commit()
            logger.info("updated_existing_filing",
                       filing_id=str(existing_filing.id),
                       accession_number=accession_number)
            return existing_filing
        else:
            # Create new filing
            # Check if company exists
            company_id = filing_data.get('company_id')
            company = session.query(Company).filter(Company.id == company_id).first()
            if not company:
                logger.error("upsert_filing_failed",
                            error=f"Company with ID {company_id} not found")
                raise ValueError(f"Company with ID {company_id} not found")

            filing = Filing(**filing_data)
            session.add(filing)
            session.commit()
            logger.info("created_new_filing",
                       filing_id=str(filing.id),
                       accession_number=accession_number)
            return filing
    except Exception as e:
        session.rollback()
        logger.error("upsert_filing_failed", error=str(e), exc_info=True)
        raise

def get_filing_by_accession_number(accession_number: str) -> Optional[Filing]:
    """Get a filing by its accession number.

    Args:
        accession_number: Accession number of the filing to retrieve

    Returns:
        Filing object if found, None otherwise
    """
    try:
        session = get_db_session()
        filing = session.query(Filing).filter(Filing.accession_number == accession_number).first()
        if filing:
            logger.info("retrieved_filing_by_accession_number",
                       filing_id=str(filing.id),
                       accession_number=accession_number)
        else:
            logger.warning("filing_by_accession_number_not_found",
                          accession_number=accession_number)
        return filing
    except Exception as e:
        logger.error("get_filing_by_accession_number_failed",
                    accession_number=accession_number,
                    error=str(e),
                    exc_info=True)
        raise

def get_filings_by_company(company_id: Union[UUID, str]) -> List[Filing]:
    """Get all filings associated with a company.

    Args:
        company_id: UUID of the company

    Returns:
        List of Filing objects
    """
    try:
        session = get_db_session()
        filings = session.query(Filing).filter(Filing.company_id == company_id).all()
        logger.info("retrieved_filings_by_company",
                   count=len(filings))
        return filings
    except Exception as e:
        logger.error("get_filings_by_company_failed",
                    company_id=str(company_id),
                    error=str(e),
                    exc_info=True)
        raise

