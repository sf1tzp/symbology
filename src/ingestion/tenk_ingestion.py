from typing import Dict, List, Optional, Union

from src.ingestion.edgar_db.accessors import edgar_login
from src.ingestion.ingestion_helpers import ingest_company, ingest_filing, ingest_filing_documents, ingest_financial_data
from src.utils.logging import get_logger

logger = get_logger(__name__)

def run_10k_ingestion(tickers: Union[str, List[str]],
                     years: Union[int, List[int]],
                     edgar_contact: Optional[str] = None) -> Dict:
    """
    Run the 10-K data ingestion pipeline for the specified tickers and years.

    Args:
        tickers: Single ticker or list of ticker symbols to process
        years: Single year or list of years to fetch filings for
        edgar_contact: Email address for SEC EDGAR API identity (optional)

    Returns:
        Dictionary with statistics about ingested data
    """
    # Normalize inputs
    if isinstance(tickers, str):
        tickers = [tickers]
    if isinstance(years, int):
        years = [years]

    # Set EDGAR identity if provided
    if edgar_contact:
        edgar_login(edgar_contact)

    # Track ingestion statistics
    stats = {
        'companies': 0,
        'filings': 0,
        'documents': 0,
        'financial_values': {
            'balance_sheet': 0,
            'income_statement': 0,
            'cash_flow': 0,
            'cover_page': 0
        }
    }

    # Process each ticker
    for ticker in tickers:
        logger.info("processing_ticker", ticker=ticker)
        try:
            # Ingest company data
            edgar_company, company_id = ingest_company(ticker)
            stats['companies'] += 1

            # Process each year for this company
            for year in years:
                logger.info("processing_year", ticker=ticker, year=year)

                # Ingest filing
                filing, filing_id = ingest_filing(company_id, edgar_company, year)
                if not filing or not filing_id:
                    logger.warning("no_filing_for_year", ticker=ticker, year=year)
                    continue

                stats['filings'] += 1

                # Ingest filing documents (business description, risk factors, MD&A)
                document_ids = ingest_filing_documents(company_id, filing_id, filing)
                stats['documents'] += len(document_ids)

                # Ingest financial data (balance sheet, income statement, cash flow, cover page)
                financial_counts = ingest_financial_data(company_id, filing_id, filing)

                # Update statistics
                for statement_type, count in financial_counts.items():
                    stats['financial_values'][statement_type] += count

        except Exception as e:
            logger.error("ticker_processing_failed",
                        ticker=ticker,
                        error=str(e),
                        exc_info=True)

    # Calculate total financial values
    stats['financial_values']['total'] = sum(stats['financial_values'].values())

    logger.info("ingestion_completed",
               tickers=tickers,
               years=years,
               companies=stats['companies'],
               filings=stats['filings'],
               documents=stats['documents'],
               financial_values=stats['financial_values']['total'])

    return stats