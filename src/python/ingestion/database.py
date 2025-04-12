import logging
from typing import Any, Dict, List, Optional

# Import config using absolute import
from config import settings
from sqlalchemy import cast, create_engine, String
from sqlalchemy.orm import scoped_session, sessionmaker

from .models import Base, Company

# Configure logging
logger = logging.getLogger(__name__)

# Create SQLAlchemy engine using the config settings
engine = create_engine(settings.database.url)

# Create a scoped session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(SessionLocal)


def init_db() -> None:
    """Initialize the database by creating tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def close_session() -> None:
    """Close the current session and remove it from the registry.
    Call this when you're done with a series of database operations.
    """
    db_session.remove()
    logger.debug("Database session closed and removed")


# CRUD Operations for Company model


def create_company(company_data: Dict[str, Any]) -> Company:
    """Create a new company record in the database."""
    try:
        db_company = Company(**company_data)
        db_session.add(db_company)
        db_session.commit()
        db_session.refresh(db_company)
        return db_company
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error creating company: {e}")
        raise


def get_company_by_id(company_id: int) -> Optional[Company]:
    """Get a company by ID."""
    return db_session.query(Company).filter(Company.id == company_id).first()


def get_company_by_cik(cik: int) -> Optional[Company]:
    """Get a company by CIK number."""
    return db_session.query(Company).filter(Company.cik == cik).first()


def get_companies_by_ticker(ticker: str) -> List[Company]:
    """Get companies by ticker symbol (searches the JSON tickers field)."""
    return (
        db_session.query(Company)
        .filter(cast(Company.tickers, String).contains(ticker))
        .all()
    )


def update_company(company_id: int, company_data: Dict[str, Any]) -> Optional[Company]:
    """Update an existing company's information."""
    try:
        db_company = db_session.query(Company).filter(Company.id == company_id).first()
        if db_company:
            for key, value in company_data.items():
                if hasattr(db_company, key):
                    setattr(db_company, key, value)
            db_session.commit()
            db_session.refresh(db_company)
        return db_company
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error updating company: {e}")
        raise


def delete_company(company_id: int) -> bool:
    """Delete a company from the database."""
    try:
        db_company = db_session.query(Company).filter(Company.id == company_id).first()
        if db_company:
            db_session.delete(db_company)
            db_session.commit()
            return True
        return False
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error deleting company: {e}")
        raise


def get_all_companies(skip: int = 0, limit: int = 100) -> List[Company]:
    """Get a paginated list of all companies."""
    return db_session.query(Company).offset(skip).limit(limit).all()


def upsert_company(cik: int, company_data: Dict[str, Any]) -> Company:
    """Insert if company doesn't exist, update if it does (by CIK)."""
    try:
        db_company = db_session.query(Company).filter(Company.cik == cik).first()
        if db_company:
            # Update existing company
            for key, value in company_data.items():
                if hasattr(db_company, key):
                    setattr(db_company, key, value)
        else:
            # Create new company
            company_data["cik"] = cik
            db_company = Company(**company_data)
            db_session.add(db_company)

        db_session.commit()
        db_session.refresh(db_company)
        return db_company
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error upserting company: {e}")
        raise
