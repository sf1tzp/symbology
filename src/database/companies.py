from datetime import date
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, String
from sqlalchemy.dialects.postgresql import ARRAY, JSON
from sqlalchemy.orm import attributes, Mapped, mapped_column, relationship

from src.database.base import Base, get_db_session
from src.utils.logging import get_logger

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from src.database.documents import Document
    from src.database.filings import Filing
    from src.database.financial_values import FinancialValue

# Initialize structlog
logger = get_logger(__name__)

class Company(Base):
    """Company model representing company information."""

    __tablename__ = "companies"

    # Primary identifiers
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    cik: Mapped[Optional[str]] = mapped_column(String(10), unique=True, index=True)

    # Relationships
    filings: Mapped[List["Filing"]] = relationship("Filing", back_populates="company", cascade="all, delete-orphan")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="company", cascade="all, delete-orphan")
    financial_values: Mapped[List["FinancialValue"]] = relationship("FinancialValue", back_populates="company", cascade="all, delete-orphan")

    # Company details
    name: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    is_company: Mapped[bool] = mapped_column(Boolean, default=True)
    tickers: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    exchanges: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    sic: Mapped[Optional[str]] = mapped_column(String(4), index=True)
    sic_description: Mapped[Optional[str]] = mapped_column(String(255))
    fiscal_year_end: Mapped[Optional[date]] = mapped_column(Date)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50))
    ein: Mapped[Optional[str]] = mapped_column(String(20), unique=True, index=True)
    former_names: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)

    def __repr__(self) -> str:
        return f"<Company(id={self.id}, name='{self.name}', cik='{self.cik}')>"


def get_company_ids() -> List[UUID]:
    """Get a list of all company IDs in the database.

    Returns:
        List of company UUIDs
    """
    try:
        session = get_db_session()
        company_ids = [company_id for company_id, in session.query(Company.id).all()]
        logger.info("retrieved_company_ids", count=len(company_ids))
        return company_ids
    except Exception as e:
        logger.error("get_company_ids_failed", error=str(e), exc_info=True)
        raise


def get_company(company_id: Union[UUID, str]) -> Optional[Company]:
    """Get a company by its ID.

    Args:
        company_id: UUID of the company to retrieve

    Returns:
        Company object if found, None otherwise
    """
    try:
        session = get_db_session()
        company = session.query(Company).filter(Company.id == company_id).first()
        if company:
            logger.info("retrieved_company", company_id=str(company_id))
        else:
            logger.warning("company_not_found", company_id=str(company_id))
        return company
    except Exception as e:
        logger.error("get_company_failed", company_id=str(company_id), error=str(e), exc_info=True)
        raise


def create_company(company_data: Dict[str, Any]) -> Company:
    """Create a new company in the database.

    Args:
        company_data: Dictionary containing company attributes

    Returns:
        Newly created Company object
    """
    try:
        session = get_db_session()
        company = Company(**company_data)
        session.add(company)
        session.commit()
        logger.info("created_company", company_id=str(company.id), name=company.name)
        return company
    except Exception as e:
        session.rollback()
        logger.error("create_company_failed", error=str(e), exc_info=True)
        raise


def update_company(company_id: Union[UUID, str], company_data: Dict[str, Any]) -> Optional[Company]:
    """Update an existing company in the database.

    Args:
        company_id: UUID of the company to update
        company_data: Dictionary containing company attributes to update

    Returns:
        Updated Company object if found, None otherwise
    """
    try:
        session = get_db_session()
        company = session.query(Company).filter(Company.id == company_id).first()
        if not company:
            logger.warning("update_company_not_found", company_id=str(company_id))
            return None

        for key, value in company_data.items():
            if hasattr(company, key):
                setattr(company, key, value)
                # Flag JSON fields as modified to ensure changes are detected
                if key == 'former_names':
                    attributes.flag_modified(company, key)
            else:
                logger.warning("update_company_invalid_attribute", company_id=str(company_id), attribute=key)

        session.commit()
        logger.info("updated_company", company_id=str(company.id), name=company.name)
        return company
    except Exception as e:
        session.rollback()
        logger.error("update_company_failed", company_id=str(company_id), error=str(e), exc_info=True)
        raise


def delete_company(company_id: Union[UUID, str]) -> bool:
    """Delete a company from the database.

    Args:
        company_id: UUID of the company to delete

    Returns:
        True if company was deleted, False if not found
    """
    try:
        session = get_db_session()
        company = session.query(Company).filter(Company.id == company_id).first()
        if not company:
            logger.warning("delete_company_not_found", company_id=str(company_id))
            return False

        session.delete(company)
        session.commit()
        logger.info("deleted_company", company_id=str(company_id))
        return True
    except Exception as e:
        session.rollback()
        logger.error("delete_company_failed", company_id=str(company_id), error=str(e), exc_info=True)
        raise


def upsert_company_by_cik(company_data: Dict[str, Any]) -> Company:
    """Create a company or update it if it already exists based on CIK.

    Args:
        company_data: Dictionary containing company attributes

    Returns:
        Created or updated Company object
    """
    try:
        session = get_db_session()
        cik = company_data.get('cik')

        if not cik:
            logger.error("upsert_company_failed", error="CIK is required")
            raise ValueError("CIK is required for company upsert")

        # Ensure CIK is a string when querying the database
        existing_company = session.query(Company).filter(Company.cik == str(cik)).first()

        if existing_company:
            # Update existing company
            for key, value in company_data.items():
                if hasattr(existing_company, key):
                    setattr(existing_company, key, value)
                    # Flag JSON fields as modified to ensure changes are detected
                    if key == 'former_names':
                        attributes.flag_modified(existing_company, key)

            session.commit()
            logger.info("updated_existing_company", company_id=str(existing_company.id), cik=cik)
            return existing_company
        else:
            # Create new company
            company = Company(**company_data)
            session.add(company)
            session.commit()
            logger.info("created_new_company", company_id=str(company.id), cik=cik)
            return company
    except Exception as e:
        session.rollback()
        logger.error("upsert_company_failed", error=str(e), exc_info=True)
        raise

def get_company_by_cik(cik: str) -> Optional[Company]:
    """Get a company by its CIK.

    Args:
        cik: CIK of the company to retrieve

    Returns:
        Company object if found, None otherwise
    """
    try:
        session = get_db_session()
        company = session.query(Company).filter(Company.cik == cik).first()
        if company:
            logger.info("retrieved_company_by_cik", company_id=str(company.id), cik=cik)
        else:
            logger.warning("company_by_cik_not_found", cik=cik)
        return company
    except Exception as e:
        logger.error("get_company_by_cik_failed", cik=cik, error=str(e), exc_info=True)
        raise
