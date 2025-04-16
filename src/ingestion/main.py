import argparse

from src.database.base import close_session, get_db_session, init_db
from src.database.companies import Company, delete_company
from src.ingestion.config import settings
from src.utils.logging import configure_logging, get_logger

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

    # Add a "delete" command for deleting companies by ticker
    delete_parser = subparsers.add_parser("delete", help="Delete a company and all its associated data")
    delete_parser.add_argument(
        "--ticker",
        "-t",
        type=str,
        required=True,
        help="Ticker symbol of the company to delete (e.g., AAPL)"
    )
    delete_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force deletion without confirmation"
    )






def delete_company_by_ticker(ticker, force=False):
    """
    Delete a company by its ticker symbol.

    Args:
        ticker: The ticker symbol of the company to delete
        force: If True, skip confirmation prompt

    Returns:
        True if the company was found and deleted, False otherwise
    """
    logger.info(f"Looking up company with ticker: {ticker}")

    # Initialize the database
    init_db(settings.database.url)

    # Find the company by ticker
    session = get_db_session()
    companies = session.query(Company).filter(Company.tickers.contains([ticker])).all()
    session.close()

    if not companies:
        logger.error(f"No company found with ticker: {ticker}")
        return False

    if len(companies) > 1:
        logger.warning(f"Multiple companies found with ticker {ticker}. Will delete them all.")

    # Confirm deletion if not forced
    if not force:
        company_names = ", ".join([company.name for company in companies])
        confirmation = input(f"Are you sure you want to delete {company_names} and all associated data? This cannot be undone. [y/N]: ")
        if confirmation.lower() not in ["y", "yes"]:
            logger.info("Deletion cancelled.")
            return False

    # Delete all companies with this ticker
    deleted_count = 0
    for company in companies:
        logger.info(f"Deleting company: {company.name} (ID: {company.id}, CIK: {company.cik})")
        result = delete_company(company.id)
        if result:
            deleted_count += 1
            logger.info(f"Successfully deleted company {company.name}")
        else:
            logger.error(f"Failed to delete company {company.name}")

    logger.info(f"Deleted {deleted_count} out of {len(companies)} companies with ticker {ticker}")

    # Close the session when done
    close_session()

    return deleted_count > 0




def main():
    # Set up logging
    configure_logging()

    # Parse command line arguments
    _args = parse_args()

    # TODO: Implement command handling based on args


if __name__ == "__main__":
    main()
