import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import cast, String

from .base import get_db_session
from .models import Company

# Configure logging
logger = logging.getLogger(__name__)

def create_company(company_data: Dict[str, Any], session=None) -> Company:
    """Create a new company record in the database."""
    session = session or get_db_session()
    try:
        db_company = Company(**company_data)
        session.add(db_company)
        session.commit()
        session.refresh(db_company)
        return db_company
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating company: {e}")
        raise


def get_company_by_id(company_id: int, session=None) -> Optional[Company]:
    """Get a company by ID."""
    session = session or get_db_session()
    return session.query(Company).filter(Company.id == company_id).first()


def get_company_by_cik(cik: int, session=None) -> Optional[Company]:
    """Get a company by CIK number."""
    session = session or get_db_session()
    return session.query(Company).filter(Company.cik == cik).first()


def get_companies_by_ticker(ticker: str, session=None) -> List[Company]:
    """Get companies by ticker symbol (searches the JSON tickers field)."""
    session = session or get_db_session()
    return (
        session.query(Company)
        .filter(cast(Company.tickers, String).contains(ticker))
        .all()
    )


def update_company(company_id: int, company_data: Dict[str, Any], session=None) -> Optional[Company]:
    """Update an existing company's information."""
    session = session or get_db_session()
    try:
        db_company = session.query(Company).filter(Company.id == company_id).first()
        if db_company:
            for key, value in company_data.items():
                if hasattr(db_company, key):
                    setattr(db_company, key, value)
            session.commit()
            session.refresh(db_company)
        return db_company
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating company: {e}")
        raise


def delete_company(company_id: int, session=None) -> bool:
    """
    Delete a company from the database.

    This will automatically cascade delete all associated filings, financial values,
    and source documents through SQLAlchemy's relationship cascade options.

    Returns True if company was found and deleted, False otherwise.
    """
    session = session or get_db_session()
    try:
        db_company = session.query(Company).filter(Company.id == company_id).first()
        if db_company:
            logger.info(f"Deleting company ID {company_id} (CIK: {db_company.cik}) and all associated data")
            session.delete(db_company)
            session.commit()
            logger.info(f"Successfully deleted company ID {company_id} and all its related data")
            return True
        logger.warning(f"Company ID {company_id} not found - nothing to delete")
        return False
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting company and its data: {e}")
        raise


def get_all_companies(skip: int = 0, limit: int = 100, session=None) -> List[Company]:
    """Get a paginated list of all companies."""
    session = session or get_db_session()
    return session.query(Company).offset(skip).limit(limit).all()


def upsert_company(cik: int, company_data: Dict[str, Any], session=None) -> Company:
    """Insert if company doesn't exist, update if it does (by CIK)."""
    session = session or get_db_session()
    try:
        db_company = session.query(Company).filter(Company.cik == cik).first()
        if db_company:
            # Update existing company
            for key, value in company_data.items():
                if hasattr(db_company, key):
                    setattr(db_company, key, value)
        else:
            # Create new company
            company_data["cik"] = cik
            db_company = Company(**company_data)
            session.add(db_company)

        session.commit()
        session.refresh(db_company)
        return db_company
    except Exception as e:
        session.rollback()
        logger.error(f"Error upserting company: {e}")
        raise