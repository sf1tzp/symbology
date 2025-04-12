import logging

from config import settings
from ingestion.database import (
    close_session,
    get_companies_by_ticker,
    init_db,
    upsert_company,
)
from ingestion.edgar import debug, edgar_login, get_company


def main():
    # Set up logging
    logger = logging.getLogger(__name__)
    logger.info("Starting application")

    # Use the config class for Edgar API login
    logger.info(f"Using Edgar contact: {settings.api.edgar_contact}")
    edgar_login(settings.api.edgar_contact)

    ticker = "MSFT"

    # Get company information for MSFT
    company = get_company(ticker)
    logger.info(f"Retrieved company data for MSFT: {company.name}")
    logger.debug(debug(company))

    # Initialize the database (create tables if they don't exist)
    init_db()
    logger.info("Database initialized")

    # Convert Edgar company object to dictionary for database storage
    company_data = {
        'cik': company.cik,
        'name': company.name,
        'tickers': [ticker],
        'sic': company.sic,
        'sic_description': company.sic_description,
        'business_address': str(company.business_address),
        'mailing_address': str(company.mailing_address),
        'fiscal_year_end': company.fiscal_year_end
    }

    # Insert or update the company in the database
    db_company = upsert_company(company.cik, company_data)
    logger.info(f"Company upserted to database with ID: {db_company.id}")

    # Read back the MSFT data from the database
    # Now we can directly access attributes from the returned objects
    companies = get_companies_by_ticker("MSFT")
    if companies:
        logger.info(f"Retrieved company from database: {companies[0].name}")
        logger.info(f"Company details: {companies[0].to_dict()}")
    else:
        logger.error("Could not find MSFT in the database")

    # Close the session when you're done with all database operations
    close_session()


if __name__ == "__main__":
    main()

