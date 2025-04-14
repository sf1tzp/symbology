import argparse
import sys

from ingestion.edgar.accessors import edgar_login, get_company
from src.ingestion.config import settings
from src.ingestion.database.base import close_session, get_db_session, init_db
from src.ingestion.database.crud_business_description import get_business_descriptions_by_company_id
from src.ingestion.database.crud_company import get_companies_by_ticker, upsert_company
from src.ingestion.ten_k import batch_process_10k_filings, process_10k_filing
from src.ingestion.utils.logging import configure_logging, get_logger

# Initialize structlog
logger = get_logger(__name__)


def parse_args():
    """
    Parse command line arguments for the 10-K data ingestion pipeline.
    """
    parser = argparse.ArgumentParser(
        description="Symbology: Financial data processing CLI"
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Add a "demo" command that runs the original demo code
    _ = subparsers.add_parser("demo", help="Run the original demo code")

    # Add a "10k" command for processing 10-K filings
    tenk_parser = subparsers.add_parser("10k", help="Process 10-K filings from EDGAR")
    tenk_parser.add_argument(
        "--tickers",
        "-t",
        nargs="+",
        required=True,
        help="List of ticker symbols (e.g., AAPL MSFT GOOGL)"
    )
    tenk_parser.add_argument(
        "--years",
        "-y",
        type=int,
        nargs="+",
        required=True,
        help="List of years to process (e.g., 2022 2023)"
    )
    tenk_parser.add_argument(
        "--edgar-contact",
        type=str,
        help="Email to use for EDGAR API (defaults to value from config)"
    )

    # If no arguments are provided, show help and exit
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    return parser.parse_args()


def run_demo():
    """
    Run the original demo functionality that queries information for Microsoft.
    """
    logger.info("Starting demo application")

    # Use the config class for Edgar API login
    logger.info(f"Using Edgar contact: {settings.api.edgar_contact}")
    edgar_login(settings.api.edgar_contact)

    ticker = "MSFT"

    # Get company information for MSFT
    company = get_company(ticker)
    logger.info(f"Retrieved company data for MSFT: {company.name}")
    logger.debug(company)

    # Initialize the database (create tables if they don't exist)
    # Pass the database URL from settings instead of importing settings in the database module
    init_db(settings.database.url)
    logger.info("Database initialized")

    # Convert Edgar company object to dictionary for database storage
    company_data = {
        "cik": company.cik,
        "name": company.name,
        "tickers": [ticker],
        "sic": company.sic,
        "sic_description": company.sic_description,
        "business_address": str(company.business_address),
        "mailing_address": str(company.mailing_address),
        "fiscal_year_end": company.fiscal_year_end,
    }

    # Insert or update the company in the database
    # Using default session since we're in the main application flow
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

    # Process MSFT 2024 10-K filing
    logger.info("Processing MSFT 2024 10-K filing")
    result = process_10k_filing(ticker, 2024, settings.api.edgar_contact)

    if result["success"]:
        logger.info(f"Successfully processed 10-K filing: {result['message']}")

        # Get the business description from the database
        session = get_db_session()
        business_descriptions = get_business_descriptions_by_company_id(session, result["company_id"])

        if business_descriptions:
            # Get the most recent business description
            latest_business_desc = max(business_descriptions, key=lambda x: x.report_date)

            # Truncate the content to 140 characters
            truncated_content = latest_business_desc.content[:540] + "..." if len(latest_business_desc.content) > 140 else latest_business_desc.content

            logger.info(f"Business Description (truncated): {truncated_content}")
        else:
            logger.warning("No business description found for MSFT")

        session.close()
    else:
        logger.error(f"Failed to process 10-K filing: {result['message']}")
        if result.get("errors"):
            for error in result["errors"]:
                logger.error(f"Error: {error}")

    # Close the session when you're done with all database operations
    close_session()


def run_10k_ingestion(tickers, years, edgar_contact=None):
    """
    Run the 10-K data ingestion pipeline for the specified tickers and years.
    """
    logger.info(f"Starting 10-K data ingestion for {len(tickers)} tickers and {len(years)} years")

    # Initialize the database
    init_db(settings.database.url)
    logger.info("Database initialized")

    # Use the contact email from settings if not provided
    if edgar_contact is None:
        edgar_contact = settings.api.edgar_contact

    # Process the 10-K filings
    logger.info(f"Using Edgar contact: {edgar_contact}")
    results = batch_process_10k_filings(tickers, years, edgar_contact)

    # Log the results
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    logger.info(f"Processed {len(results)} filings")
    logger.info(f"  - Successful: {len(successful)}")
    logger.info(f"  - Failed: {len(failed)}")

    # Log details about failures if any
    if failed:
        logger.warning("Failed filings:")
        for f in failed:
            logger.warning(f"  - {f['ticker']} ({f['year']}): {f['message']}")

    # Close the session when you're done with all database operations
    close_session()

    return results


def main():
    # Set up logging
    configure_logging()

    # Parse command line arguments
    args = parse_args()

    # Run the appropriate command
    if args.command == "demo":
        run_demo()
    elif args.command == "10k":
        run_10k_ingestion(
            tickers=args.tickers,
            years=args.years,
            edgar_contact=args.edgar_contact
        )
    else:
        logger.error(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
