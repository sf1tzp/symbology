from datetime import date
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union
from uuid import UUID

from sqlalchemy import Date, func, String
from sqlalchemy.dialects.postgresql import ARRAY, JSON, TSVECTOR
from sqlalchemy.orm import attributes, Mapped, mapped_column, relationship
from symbology.database.base import Base, get_db_session
from symbology.utils.logging import get_logger
from uuid_extensions import uuid7

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from symbology.database.documents import Document
    from symbology.database.filings import Filing
    from symbology.database.financial_values import FinancialValue

# Initialize structlog
logger = get_logger(__name__)

class Company(Base):
    """Company model representing company information."""

    __tablename__ = "companies"

    # Primary identifiers
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

    # Relationships
    filings: Mapped[List["Filing"]] = relationship("Filing", back_populates="company", cascade="all, delete-orphan", lazy="selectin")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="company", cascade="all, delete-orphan", lazy="selectin")
    financial_values: Mapped[List["FinancialValue"]] = relationship("FinancialValue", back_populates="company", cascade="all, delete-orphan", lazy="noload")

    # Company details
    name: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    ticker: Mapped[str] = mapped_column(String(10))
    exchanges: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    sic: Mapped[Optional[str]] = mapped_column(String(4), index=True)
    cik: Mapped[Optional[str]] = mapped_column(String(20), unique=True, index=True)
    sic_description: Mapped[Optional[str]] = mapped_column(String(255))
    fiscal_year_end: Mapped[Optional[date]] = mapped_column(Date)
    former_names: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)

    # Full-text search vector (maintained by PostgreSQL trigger)
    search_vector = mapped_column(TSVECTOR, nullable=True)

    def __repr__(self) -> str:
        return f"<Company(id={self.id}, name='{self.name}', ticker='{self.ticker}')>"


def get_company_ids() -> List[UUID]:
    """Get a list of all company IDs in the database.

    Returns:
        List of company UUIDs
    """
    try:
        session = get_db_session()
        company_ids = [company_id for company_id, in session.query(Company.id).all()]
        logger.debug("retrieved_company_ids", count=len(company_ids))
        return company_ids
    except Exception as e:
        logger.error("get_company_ids_failed", error=str(e), exc_info=True)
        raise


def get_all_company_tickers() -> List[str]:
    """Get a list of all unique ticker symbols from companies in the database.

    Returns:
        List of unique ticker symbols
    """
    try:
        session = get_db_session()
        companies = session.query(Company).all()

        # Extract all tickers from all companies and flatten the list
        all_tickers = []
        for company in companies:
            if company.ticker:
                all_tickers.append(company.ticker)

        # Remove duplicates and sort
        unique_tickers = sorted(list(set(all_tickers)))

        logger.debug("retrieved_all_company_tickers", count=len(unique_tickers))
        return unique_tickers
    except Exception as e:
        logger.error("get_all_company_tickers_failed", error=str(e), exc_info=True)
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
            logger.info("retrieved_company", company=company.name, ticker=company.ticker)
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


def get_company_by_cik(cik: str) -> Optional[Company]:
    """Get a company by its CIK number.

    Args:
        cik: Central Index Key of the company

    Returns:
        Company object if found, None otherwise
    """
    try:
        session = get_db_session()
        company = session.query(Company).filter(Company.cik == cik).first()
        if company:
            logger.info("retrieved_company_by_cik", company=company.name, cik=cik)
        else:
            logger.debug("company_by_cik_not_found", cik=cik)
        return company
    except Exception as e:
        logger.error("get_company_by_cik_failed", cik=cik, error=str(e), exc_info=True)
        raise


def get_company_by_ticker(ticker: str) -> Optional[Company]:
    """Get a company by one of its ticker symbols.

    Args:
        ticker: Ticker symbol of the company to retrieve

    Returns:
        Company object if found, None otherwise
    """
    try:
        session = get_db_session()
        company = session.query(Company).filter(ticker.upper() == Company.ticker).first()
        if company:
            logger.info("retrieved_company_by_ticker", company=company.name, ticker=company.ticker)
        else:
            logger.warning("company_by_ticker_not_found", ticker=ticker)
        return company
    except Exception as e:
        logger.error("get_company_by_ticker_failed", ticker=ticker, error=str(e), exc_info=True)
        raise

def search_companies_by_query(query: str, limit: int = 10) -> List[Company]:
    """Search for companies by partial ticker or name.

    Uses full-text search for queries of 3+ characters and falls back
    to prefix matching on ticker for very short queries.

    Args:
        query: Search string to match against company names or tickers
        limit: Maximum number of results to return

    Returns:
        List of matching Company objects
    """
    try:
        session = get_db_session()
        stripped = query.strip()

        if len(stripped) < 3:
            # Short queries: prefix match on ticker (fast with btree index)
            upper_query = stripped.upper()
            companies = (
                session.query(Company)
                .filter(Company.ticker.ilike(f'{upper_query}%'))
                .limit(limit)
                .all()
            )
        else:
            # Full-text search for longer queries
            ts_query = func.websearch_to_tsquery('english', stripped)
            companies = (
                session.query(Company)
                .filter(Company.search_vector.op('@@')(ts_query))
                .order_by(func.ts_rank(Company.search_vector, ts_query).desc())
                .limit(limit)
                .all()
            )

            # Fall back to ILIKE if FTS returns no results (e.g. partial words)
            if not companies:
                companies = (
                    session.query(Company)
                    .filter(
                        (Company.name.ilike(f'%{stripped}%')) |
                        (Company.ticker.ilike(f'%{stripped.upper()}%'))
                    )
                    .limit(limit)
                    .all()
                )

        logger.info("search_companies_by_query", query=query, result_count=len(companies))
        return companies
    except Exception as e:
        logger.error("search_companies_by_query_failed", query=query, error=str(e), exc_info=True)
        try:
            session = get_db_session()
            session.rollback()
        except Exception:
            pass
        return []


def list_all_companies(offset: int = 0, limit: int = 50) -> List[Company]:
    """Get a paginated list of all companies that have summaries.

    Args:
        offset: Number of companies to skip
        limit: Maximum number of companies to return

    Returns:
        List of Company objects that have summaries
    """
    try:
        session = get_db_session()
        companies = session.query(Company).filter().order_by(Company.name).offset(offset).limit(limit).all()

        logger.info("list_all_companies", offset=offset, limit=limit, result_count=len(companies))
        return companies
    except Exception as e:
        logger.error("list_all_companies_failed", offset=offset, limit=limit, error=str(e), exc_info=True)
        raise
