from datetime import datetime
import logging
from typing import Any, Dict, List, Optional

from .base import get_db_session
from .models import Filing

# Configure logging
logger = logging.getLogger(__name__)

def create_filing(filing_data: Dict[str, Any], session=None) -> Filing:
    """Create a new filing record in the database."""
    session = session or get_db_session()
    try:
        db_filing = Filing(**filing_data)
        session.add(db_filing)
        session.commit()
        session.refresh(db_filing)
        return db_filing
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating filing: {e}")
        raise


def get_filing_by_id(filing_id: int, session=None) -> Optional[Filing]:
    """Get a filing by ID."""
    session = session or get_db_session()
    return session.query(Filing).filter(Filing.id == filing_id).first()


def get_filing_by_accession_number(accession_number: str, session=None) -> Optional[Filing]:
    """Get a filing by accession number."""
    session = session or get_db_session()
    return session.query(Filing).filter(Filing.accession_number == accession_number).first()


def get_filings_by_company_id(company_id: int, skip: int = 0, limit: int = 100, session=None) -> List[Filing]:
    """Get filings for a specific company."""
    session = session or get_db_session()
    return session.query(Filing).filter(Filing.company_id == company_id).offset(skip).limit(limit).all()


def get_filings_by_type(filing_type: str, skip: int = 0, limit: int = 100, session=None) -> List[Filing]:
    """Get filings by filing type (e.g., 10-K, 10-Q)."""
    session = session or get_db_session()
    return session.query(Filing).filter(Filing.filing_type == filing_type).offset(skip).limit(limit).all()


def get_filings_by_date_range(start_date: datetime, end_date: datetime, skip: int = 0, limit: int = 100, session=None) -> List[Filing]:
    """Get filings within a specific date range."""
    session = session or get_db_session()
    return session.query(Filing).filter(
        Filing.filing_date >= start_date,
        Filing.filing_date <= end_date
    ).offset(skip).limit(limit).all()


def update_filing(filing_id: int, filing_data: Dict[str, Any], session=None) -> Optional[Filing]:
    """Update an existing filing's information."""
    session = session or get_db_session()
    try:
        db_filing = session.query(Filing).filter(Filing.id == filing_id).first()
        if db_filing:
            for key, value in filing_data.items():
                if hasattr(db_filing, key):
                    setattr(db_filing, key, value)
            session.commit()
            session.refresh(db_filing)
        return db_filing
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating filing: {e}")
        raise


def delete_filing(filing_id: int, session=None) -> bool:
    """Delete a filing from the database."""
    session = session or get_db_session()
    try:
        db_filing = session.query(Filing).filter(Filing.id == filing_id).first()
        if db_filing:
            session.delete(db_filing)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting filing: {e}")
        raise


def get_all_filings(skip: int = 0, limit: int = 100, session=None) -> List[Filing]:
    """Get a paginated list of all filings."""
    session = session or get_db_session()
    return session.query(Filing).offset(skip).limit(limit).all()


def upsert_filing(accession_number: str, filing_data: Dict[str, Any], session=None) -> Filing:
    """Insert if filing doesn't exist, update if it does (by accession number)."""
    session = session or get_db_session()
    try:
        db_filing = session.query(Filing).filter(Filing.accession_number == accession_number).first()
        if db_filing:
            # Update existing filing
            for key, value in filing_data.items():
                if hasattr(db_filing, key):
                    setattr(db_filing, key, value)
        else:
            # Create new filing
            filing_data["accession_number"] = accession_number
            db_filing = Filing(**filing_data)
            session.add(db_filing)

        session.commit()
        session.refresh(db_filing)
        return db_filing
    except Exception as e:
        session.rollback()
        logger.error(f"Error upserting filing: {e}")
        raise