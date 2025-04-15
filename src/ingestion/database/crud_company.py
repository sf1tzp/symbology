import logging
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import cast, String, or_
from sqlalchemy.sql import text

from .base import get_db_session
from .models import Company

# Configure logging
logger = logging.getLogger(__name__)

def check_missing_fields(company_data: Dict[str, Any]) -> List[str]:
    """Check which fields are missing from company data."""
    # Define all fields in the Company model (except id, created_at, updated_at)
    all_fields = [
        'cik',
        'name',
        'display_name',
        'is_company',
        'tickers',
        'exchanges',
        'sic',
        'industry',
        'fiscal_year_end',
        'entity_type',
        'ein',
        'former_names',
    ]

    # Required fields that must not be None (as defined in the model)
    required_fields = ["name", "cik"]
    # Check which fields are missing
    missing_fields = [field for field in all_fields if field not in company_data]
    missing_required = [field for field in required_fields if field not in company_data]

    if missing_required:
        logger.error(f"Missing required fields: {missing_required}")

    if missing_fields:
        logger.warning(f"Company data is missing the following fields: {missing_fields}")

    return missing_fields

def create_company(company_data: Dict[str, Any], session=None) -> Company:
    """Create a new company record in the database.
    company_data =  {'cik': 789019,
      'name': 'MICROSOFT CORP',
      'display_name': 'MICROSOFT CORP',
      'is_company': True,
      'tickers': ['MSFT'],
      'exchanges': ['Nasdaq'],
      'sic': '7372',
      'industry': 'Services-Prepackaged Software',
      'fiscal_year_end': '0630',
      'entity_type': 'operating',
      'ein': '911144442',
      'former_names': []}
    """
    session = session or get_db_session()
    try:
        # Check for missing fields
        missing_fields = check_missing_fields(company_data)

        db_company = Company(**company_data)
        session.add(db_company)
        session.commit()
        session.refresh(db_company)

        return db_company
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating company: {e}")
        raise


def get_company(identifiers: Dict[str, Any], session=None) -> Union[Optional[Company], List[Company]]:
    """
    Get a company or companies by various identifiers.

    Args:
        identifiers: A dictionary that can contain any of these keys:
            - id: Company ID (returns single company)
            - cik: Company CIK number (returns single company)
            - ticker: Ticker symbol (returns list of companies)
        session: Database session

    Returns:
        A single Company object, a list of Company objects, or None if no match found

    Examples:
        # Get company by ID
        company = get_company({"id": 123})

        # Get company by CIK
        company = get_company({"cik": 1234567})

        # Get companies by ticker
        companies = get_company({"ticker": "AAPL"})
    """
    session = session or get_db_session()

    if not identifiers:
        logger.warning("No identifiers provided to get_company")
        return None

    # Handle ID lookup
    if "id" in identifiers:
        company_id = identifiers["id"]
        logger.debug(f"Looking up company by ID: {company_id}")
        return session.query(Company).filter(Company.id == company_id).first()

    # Handle CIK lookup
    if "cik" in identifiers:
        cik = identifiers["cik"]
        logger.debug(f"Looking up company by CIK: {cik}")
        return session.query(Company).filter(Company.cik == cik).first()

    # Handle ticker lookup
    if "ticker" in identifiers:
        ticker = identifiers["ticker"]
        logger.debug(f"Looking up companies by ticker: {ticker}")
        return (
            session.query(Company)
            .filter(cast(Company.tickers, String).contains(ticker))
            .all()
        )

    logger.warning(f"Unsupported identifiers provided: {list(identifiers.keys())}")
    return None


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
