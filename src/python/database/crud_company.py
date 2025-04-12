import logging
from typing import Any, Dict, List, Optional

from .base import db_session as default_db_session
from .models import Company
from sqlalchemy import cast, String

# Configure logging
logger = logging.getLogger(__name__)

def create_company(company_data: Dict[str, Any], session=None) -> Company:
    """Create a new company record in the database."""
    session = session or default_db_session
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
    session = session or default_db_session
    return session.query(Company).filter(Company.id == company_id).first()


def get_company_by_cik(cik: int, session=None) -> Optional[Company]:
    """Get a company by CIK number."""
    session = session or default_db_session
    return session.query(Company).filter(Company.cik == cik).first()


def get_companies_by_ticker(ticker: str, session=None) -> List[Company]:
    """Get companies by ticker symbol (searches the JSON tickers field)."""
    session = session or default_db_session
    return (
        session.query(Company)
        .filter(cast(Company.tickers, String).contains(ticker))
        .all()
    )


def update_company(company_id: int, company_data: Dict[str, Any], session=None) -> Optional[Company]:
    """Update an existing company's information."""
    session = session or default_db_session
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
    """Delete a company from the database."""
    session = session or default_db_session
    try:
        db_company = session.query(Company).filter(Company.id == company_id).first()
        if db_company:
            session.delete(db_company)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting company: {e}")
        raise


def get_all_companies(skip: int = 0, limit: int = 100, session=None) -> List[Company]:
    """Get a paginated list of all companies."""
    session = session or default_db_session
    return session.query(Company).offset(skip).limit(limit).all()


def upsert_company(cik: int, company_data: Dict[str, Any], session=None) -> Company:
    """Insert if company doesn't exist, update if it does (by CIK)."""
    session = session or default_db_session
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