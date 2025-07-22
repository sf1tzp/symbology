#!/usr/bin/env python3
"""
EDGAR data ingestion script.

This script provides functionality for retrieving data from EDGAR and storing
it in the database using ingestion helper functions.

Usage:
    python -m src.bin.edgar_ingestion

Note: This script requires a valid EDGAR database connection.
"""

import argparse
from datetime import datetime
import sys
from typing import List, Union
from uuid import UUID

from src.database.base import close_session, init_db
from src.ingestion.edgar_db.accessors import edgar_login
from src.ingestion.ingestion_helpers import ingest_company, ingest_filing, ingest_filing_documents
from src.utils.config import settings
from src.utils.logging import configure_logging, get_logger

# Configure logging using application settings
configure_logging(
    log_level=settings.logging.level,
    json_format=settings.logging.json_format
)

logger = get_logger(__name__)

def parse_tickers(ticker_input: str) -> List[str]:
    """
    Parse ticker input that can be comma-separated or space-separated.

    Args:
        ticker_input: String containing one or more ticker symbols

    Returns:
        List of ticker symbols, cleaned and uppercased
    """
    if not ticker_input:
        return []

    # Split by comma or space and clean up
    tickers = []
    for ticker in ticker_input.replace(',', ' ').split():
        ticker = ticker.strip().upper()
        if ticker:
            tickers.append(ticker)

    return tickers

def get_years_to_process(year_arg: Union[str, int], last_n_years: int = None) -> List[int]:
    """
    Generate list of years to process based on arguments.

    Args:
        year_arg: Year specification (single year, range like "2020-2023", or None)
        last_n_years: Number of recent years to process

    Returns:
        List of years to process
    """
    current_year = datetime.now().year

    if last_n_years:
        # Process the last N years including current year
        return list(range(current_year - last_n_years + 1, current_year + 1))

    if isinstance(year_arg, int):
        return [year_arg]

    if isinstance(year_arg, str) and '-' in year_arg:
        # Handle year ranges like "2020-2023"
        try:
            start_year, end_year = map(int, year_arg.split('-'))
            if start_year > end_year:
                start_year, end_year = end_year, start_year
            return list(range(start_year, end_year + 1))
        except ValueError as err:
            raise ValueError(f"Invalid year range format: {year_arg}. Use format like '2020-2023'") from err

    # Default to last 5 years if no specific year provided
    return list(range(current_year - 4, current_year + 1))

def process_company(ticker: str) -> UUID:
    """
    Ingest company data from EDGAR.

    Args:
        ticker: Stock ticker symbol to fetch

    Returns:
        UUID of the company in the database
    """
    logger.info("Processing company ingestion", ticker=ticker)
    try:
        edgar_company, company_id = ingest_company(ticker)
        logger.info("Company ingestion successful",
                   company_id=str(company_id),
                   company_name=edgar_company.name,
                   cik=edgar_company.cik)
        return company_id, edgar_company
    except Exception as e:
        logger.error("Company ingestion failed", ticker=ticker, error=str(e), exc_info=True)
        raise

def process_filing(company_id: UUID, edgar_company, year: int):
    """
    Ingest 10-K filing data from EDGAR.

    Args:
        company_id: UUID of the company in the database
        edgar_company: EDGAR company data
        year: Year of the filing to fetch

    Returns:
        Tuple of (filing, filing_id) or (None, None) if not found
    """
    logger.info("Processing filing ingestion", company_id=str(company_id), year=year)
    try:
        filing, filing_id = ingest_filing(company_id, edgar_company, year)

        if filing and filing_id:
            logger.info("Filing ingestion successful",
                       filing_id=str(filing_id),
                       accession_number=filing.accession_number,
                       filing_date=filing.filing_date)
        else:
            logger.warning("No filing found", company_id=str(company_id), year=year)

        return filing, filing_id
    except Exception as e:
        logger.error("Filing ingestion failed", company_id=str(company_id), year=year, error=str(e), exc_info=True)
        raise

def process_documents(company_id: UUID, filing_id: UUID, filing, company_name: str = None):
    """
    Ingest document sections from a filing.

    Args:
        company_id: UUID of the company in the database
        filing_id: UUID of the filing in the database
        filing: EDGAR filing data
        company_name: Name of the company (optional)

    Returns:
        Dictionary of document UUIDs
    """
    logger.info("Processing document ingestion", company_id=str(company_id), filing_id=str(filing_id))
    try:
        document_uuids = ingest_filing_documents(company_id, filing_id, filing, company_name)

        logger.info("Document ingestion successful",
                   document_count=len(document_uuids),
                   document_types=list(document_uuids.keys()))

        return document_uuids
    except Exception as e:
        logger.error("Document ingestion failed",
                    company_id=str(company_id),
                    filing_id=str(filing_id),
                    error=str(e),
                    exc_info=True)
        raise

def process_end_to_end(ticker: str, year: int):
    """
    Run a complete end-to-end ingestion pipeline.

    This function executes the complete workflow from retrieving a company,
    to fetching its filings, to extracting and storing document sections.

    Args:
        ticker: Stock ticker symbol to fetch
        year: Year of the filing to fetch

    Returns:
        Dictionary containing results with counts and IDs
    """
    logger.info("Starting end-to-end ingestion", ticker=ticker, year=year)
    results = {
        "company": None,
        "filing": None,
        "documents": None,
        "success": False
    }

    try:
        # Step 1: Ingest company
        edgar_company, company_id = ingest_company(ticker)
        results["company"] = {
            "id": str(company_id),
            "name": edgar_company.name,
            "cik": edgar_company.cik
        }

        # Step 2: Ingest filing
        filing, filing_id = ingest_filing(company_id, edgar_company, year)
        if filing and filing_id:
            results["filing"] = {
                "id": str(filing_id),
                "accession_number": filing.accession_number,
                "filing_date": filing.filing_date,
                "filing_type": filing.form
            }

            # Step 3: Ingest documents
            document_uuids = ingest_filing_documents(company_id, filing_id, filing, edgar_company.name)
            if document_uuids:
                results["documents"] = {
                    "count": len(document_uuids),
                    "types": list(document_uuids.keys()),
                    "ids": {k: str(v) for k, v in document_uuids.items()}
                }

        # Mark as successful if we at least got company data
        results["success"] = True
        logger.info("End-to-end ingestion completed successfully",
                   company_id=results["company"]["id"] if results["company"] else None,
                   document_count=results["documents"]["count"] if results["documents"] else 0)

    except Exception as e:
        logger.error("End-to-end ingestion failed", error=str(e), exc_info=True)
        results["error"] = str(e)

    return results

def setup_database(db_url: str = None):
    """
    Initialize database connection

    Args:
        db_url: Database connection string (optional, uses config if not provided)
    """
    # Use the provided URL or fall back to the one from settings
    db_url = db_url or settings.database.url
    try:
        engine, session = init_db(db_url)
        logger.info("Database connection successful")
        logger.info(settings.database.database_name)
        return engine, session
    except Exception as e:
        logger.error("Database initialization failed", error=str(e), exc_info=True)
        raise

def main():
    parser = argparse.ArgumentParser(
        description='EDGAR data ingestion script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --ticker AAPL                          # Single ticker, last 5 years
  %(prog)s --ticker "AAPL,MSFT,GOOGL"            # Multiple tickers
  %(prog)s --ticker AAPL --year 2023             # Specific year
  %(prog)s --ticker AAPL --year 2020-2023        # Year range
  %(prog)s --ticker AAPL --last-n-years 3        # Last 3 years
  %(prog)s --ticker AAPL --dry-run               # See what would be processed
  %(prog)s --ticker AAPL --end-to-end --quiet    # Full pipeline, minimal output
        """
    )

    parser.add_argument('--ticker', type=str, default='AAPL',
                        help='Stock ticker symbol(s). Can be comma-separated (e.g., "AAPL,MSFT") (default: AAPL)')
    parser.add_argument('--year', type=str, default=None,
                        help='Filing year, year range (e.g., "2020-2023"), or omit for last 5 years')
    parser.add_argument('--last-n-years', type=int, default=None,
                        help='Process the last N years (overrides --year)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be processed without actually doing it')
    parser.add_argument('--quiet', action='store_true',
                        help='Reduce output verbosity')

    parser.add_argument('--email', type=str, default=settings.edgar_api.edgar_contact,
                        help=f'Email for EDGAR API access (default: {settings.edgar_api.edgar_contact})')
    parser.add_argument('--db-url', type=str, default=settings.database.url,
                        help='Database connection URL (uses config.py settings by default)')
    parser.add_argument('--end-to-end', action='store_true',
                        help='Run the end-to-end ingestion pipeline')
    parser.add_argument('--json-logs', action='store_true', default=settings.logging.json_format,
                        help='Enable JSON-formatted logging (default: uses config setting)')
    parser.add_argument('--log-level', type=str, default=settings.logging.level,
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help=f'Set logging level (default: {settings.logging.level})')

    args = parser.parse_args()

    # Parse tickers into a list
    tickers = parse_tickers(args.ticker)
    if not tickers:
        logger.error("No valid tickers provided")
        return 1

    # Determine years to process
    try:
        if args.year and args.last_n_years:
            logger.error("Cannot specify both --year and --last-n-years")
            return 1

        years = get_years_to_process(args.year, args.last_n_years)
    except ValueError as e:
        logger.error("Invalid year specification", error=str(e))
        return 1

    # Configure logging with command line options that override config settings
    log_level = 'WARNING' if args.quiet else args.log_level
    if log_level != settings.logging.level or args.json_logs != settings.logging.json_format:
        configure_logging(log_level=log_level, json_format=args.json_logs)
        logger.info("Logging reconfigured with command line options",
                   log_level=log_level, json_format=args.json_logs)

    # Show what will be processed
    logger.info("Processing plan",
                tickers=tickers,
                years=years,
                total_operations=len(tickers) * len(years),
                dry_run=args.dry_run)

    if args.dry_run:
        print("\nDry run - would process:")
        print(f"  Tickers: {', '.join(tickers)}")
        print(f"  Years: {', '.join(map(str, years))}")
        print(f"  Total operations: {len(tickers) * len(years)}")
        return 0

    try:
        # Initialize database
        setup_database(args.db_url)

        # Set up EDGAR login
        logger.info("Setting up EDGAR login", email=args.email)
        edgar_login(args.email)

        # Process all ticker/year combinations
        total_operations = len(tickers) * len(years)
        current_operation = 0
        failed_operations = []
        successful_operations = 0

        for ticker in tickers:
            for year in years:
                current_operation += 1
                if not args.quiet:
                    logger.info(f"Processing {current_operation}/{total_operations}",
                              ticker=ticker, year=year)

                try:
                    if args.end_to_end:
                        # Run the end-to-end ingestion
                        results = process_end_to_end(ticker, year)
                        if results["success"]:
                            successful_operations += 1
                        else:
                            failed_operations.append((ticker, year, results.get("error", "Unknown error")))
                    else:
                        # Run individual ingestion processes
                        company_id, edgar_company = process_company(ticker)

                        # Process filing ingestion
                        filing, filing_id = process_filing(company_id, edgar_company, year)

                        # Process document ingestion if filing was found
                        if filing and filing_id:
                            process_documents(company_id, filing_id, filing, edgar_company.name)
                            successful_operations += 1
                        else:
                            logger.warning("No filing found", ticker=ticker, year=year)
                            failed_operations.append((ticker, year, "No filing found"))

                except Exception as e:
                    logger.error("Operation failed", ticker=ticker, year=year, error=str(e))
                    failed_operations.append((ticker, year, str(e)))

        # Print final summary
        logger.info("Ingestion batch completed",
                   total_operations=total_operations,
                   successful=successful_operations,
                   failed=len(failed_operations))

        if failed_operations and not args.quiet:
            logger.warning("Failed operations summary")
            for ticker, year, error in failed_operations:
                logger.warning(f"  {ticker} {year}: {error}")

        return 1 if failed_operations else 0

    except Exception as e:
        logger.error("Batch ingestion failed", error=str(e), exc_info=True)
        return 1

    finally:
        # Close database session
        close_session()
        logger.info("Database session closed")

if main() == "__main__":
    sys.exit(main())