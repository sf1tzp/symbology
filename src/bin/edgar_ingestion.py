#!/usr/bin/env python3
"""
EDGAR data ingestion script.

This script provides functionality for retrieving data from EDGAR and storing
it in the database using ingestion helper functions.

Usage:
    python -m src.bin.edgar_ingestion

Note: This script requires a valid EDGAR database connection.
"""

import sys
import os
from datetime import date
import argparse
from uuid import UUID

from src.ingestion.edgar_db.accessors import edgar_login
from src.ingestion.ingestion_helpers import (
    ingest_company,
    ingest_filing,
    ingest_filing_documents
)
from src.ingestion.database.base import init_db, close_session
from src.ingestion.utils.logging import get_logger, configure_logging
from src.ingestion.config import settings

# Configure logging using application settings
configure_logging(
    log_level=settings.logging.level,
    json_format=settings.logging.json_format
)

logger = get_logger(__name__)

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

    logger.info("Initializing database connection", db_url=db_url.replace(settings.database.postgres_password, "****"))
    try:
        engine, session = init_db(db_url)
        logger.info("Database connection successful")
        return engine, session
    except Exception as e:
        logger.error("Database initialization failed", error=str(e), exc_info=True)
        raise

def main():
    parser = argparse.ArgumentParser(description='EDGAR data ingestion script')
    parser.add_argument('--ticker', type=str, default='AAPL',
                        help='Stock ticker symbol (default: AAPL)')
    parser.add_argument('--year', type=int, default=2022,
                        help='Filing year (default: 2022)')
    parser.add_argument('--email', type=str, default=settings.api.edgar_contact,
                        help=f'Email for EDGAR API access (default: {settings.api.edgar_contact})')
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

    # Configure logging with command line options that override config settings
    if args.log_level != settings.logging.level or args.json_logs != settings.logging.json_format:
        configure_logging(log_level=args.log_level, json_format=args.json_logs)
        logger.info("Logging reconfigured with command line options",
                   log_level=args.log_level, json_format=args.json_logs)

    try:
        # Initialize database
        setup_database(args.db_url)

        # Set up EDGAR login
        logger.info("Setting up EDGAR login", email=args.email)
        edgar_login(args.email)

        try:
            if args.end_to_end:
                # Run the end-to-end ingestion
                results = process_end_to_end(args.ticker, args.year)

                if not results["success"]:
                    logger.error("End-to-end ingestion failed")
                    return 1
            else:
                # Run individual ingestion processes
                company_id, edgar_company = process_company(args.ticker)

                # Process filing ingestion
                filing, filing_id = process_filing(company_id, edgar_company, args.year)

                # Process document ingestion if filing was found
                if filing and filing_id:
                    document_uuids = process_documents(company_id, filing_id, filing, edgar_company.name)

                    # Print summary of results
                    logger.info("Ingestion completed successfully",
                               company_id=str(company_id),
                               filing_id=str(filing_id) if filing_id else None,
                               document_count=len(document_uuids) if 'document_uuids' in locals() else 0)
                else:
                    logger.warning("Ingestion completed with no filing found",
                                  company_id=str(company_id),
                                  year=args.year)

        except Exception as e:
            logger.error("Ingestion failed", error=str(e), exc_info=True)
            return 1

    finally:
        # Close database session
        close_session()
        logger.info("Database session closed")

    return 0

if __name__ == "__main__":
    sys.exit(main())