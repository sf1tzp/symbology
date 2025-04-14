from datetime import datetime
from typing import Dict, List, Union

from ingestion.edgar.accessors import (
    edgar_login,
    get_10k_filing,
    get_balance_sheet_values,
    get_business_description,
    get_cash_flow_statement_values,
    get_company,
    get_cover_page_values,
    get_income_statement_values,
    get_management_discussion,
    get_risk_factors,
)
from src.ingestion.database.base import get_db_session
from src.ingestion.database.crud_company import upsert_company
from src.ingestion.database.crud_filing import create_filing, get_filing_by_accession_number
from src.ingestion.database.crud_source_document import create_source_document
from src.ingestion.financial_processing import store_balance_sheet_data, store_cash_flow_statement_data, store_cover_page_data, store_income_statement_data
from src.ingestion.utils.logging import get_logger, log_exception

# Initialize structlog
logger = get_logger(__name__)


def process_10k_filing(ticker: str, year: int, edgar_contact: str = "your-email@example.com") -> Dict[str, Union[bool, str, int]]:
    """
    Process 10-K filing for a given ticker and year.

    This function:
    1. Retrieves the 10-K filing from EDGAR
    2. Stores company information in the database
    3. Stores filing information in the database
    4. Processes and stores financial data (balance sheet, income statement, cash flow)
    5. Processes and stores textual sections (business description, risk factors, MD&A)

    Args:
        ticker: The stock ticker symbol (e.g., "AAPL")
        year: The year of the filing as an integer (e.g., 2023)
        edgar_contact: Email address to use for EDGAR API

    Returns:
        Dictionary with status information about the processing
    """
    result = {
        "success": False,
        "ticker": ticker,
        "year": year,
        "message": "",
        "company_id": None,
        "filing_id": None,
        "errors": []  # Track individual errors
    }

    session = get_db_session()
    all_steps_succeeded = True  # Track if all steps succeeded

    try:
        # Login to EDGAR
        edgar_login(edgar_contact)

        # Get company information from EDGAR
        edgar_company = get_company(ticker)
        if not edgar_company:
            result["message"] = f"Could not find company with ticker {ticker}"
            return result

        # Get 10-K filing for the year
        filing = get_10k_filing(edgar_company, year)
        if not filing:
            result["message"] = f"Could not find 10-K filing for {ticker} in {year}"
            return result

        # Check if filing already exists in the database
        existing_filing = get_filing_by_accession_number(filing.accession_number, session=session)
        if existing_filing:
            result["message"] = f"Filing already exists in the database with ID {existing_filing.id}"
            result["filing_id"] = existing_filing.id
            result["company_id"] = existing_filing.company_id
            result["success"] = True
            return result

        # Prepare company data for the database
        company_data = {
            "cik": edgar_company.cik,
            "name": edgar_company.name,
            "tickers": edgar_company.tickers,
            "exchanges": edgar_company.exchanges if hasattr(edgar_company, "exchanges") else [],
            "sic": edgar_company.sic if hasattr(edgar_company, "sic") else None,
            "sic_description": edgar_company.sic_description if hasattr(edgar_company, "sic_description") else None,
            "category": edgar_company.category if hasattr(edgar_company, "category") else None,
            "fiscal_year_end": edgar_company.fiscal_year_end if hasattr(edgar_company, "fiscal_year_end") else None,
            "entity_type": edgar_company.entity_type if hasattr(edgar_company, "entity_type") else None
        }

        # Store or update company information
        db_company = upsert_company(edgar_company.cik, company_data, session=session)
        result["company_id"] = db_company.id

        # Prepare filing data for the database
        filing_date = filing.filing_date if filing.filing_date else None
        report_date = datetime.strptime(filing.period_of_report, "%Y-%m-%d") if filing.period_of_report else None

        filing_data = {
            "company_id": db_company.id,
            "filing_type": "10-K",
            "accession_number": filing.accession_number,
            "filing_date": filing_date,
            "report_date": report_date,
            "form_name": filing.form,
            "file_number": filing.file_number if hasattr(filing, "file_number") else None,
            "film_number": filing.film_number if hasattr(filing, "film_number") else None,
            "url": filing.link if hasattr(filing, "link") else None,
        }

        # Store filing information
        db_filing = create_filing(filing_data, session=session)
        result["filing_id"] = db_filing.id

        # Process and store financial data

        # 1. Balance sheet
        try:
            balance_sheet_df = get_balance_sheet_values(filing)
            if balance_sheet_df is not None and not balance_sheet_df.empty:
                store_balance_sheet_data(
                    filing,
                    db_company,
                    db_filing,
                    session=session
                )
                logger.info(f"Stored balance sheet data for {ticker} {year}")
        except Exception as e:
            error_msg = f"Error processing balance sheet for {ticker} {year}: {str(e)}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            all_steps_succeeded = False

        # 2. Income statement
        try:
            income_statement_df = get_income_statement_values(filing)
            if income_statement_df is not None and not income_statement_df.empty:
                store_income_statement_data(
                    filing,
                    db_company,
                    db_filing,
                    session=session
                )
                logger.info(f"Stored income statement data for {ticker} {year}")
        except Exception as e:
            error_msg = f"Error processing income statement for {ticker} {year}: {str(e)}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            all_steps_succeeded = False

        # 3. Cash flow statement
        try:
            cash_flow_df = get_cash_flow_statement_values(filing)
            if cash_flow_df is not None and not cash_flow_df.empty:
                store_cash_flow_statement_data(
                    filing,
                    db_company,
                    db_filing,
                    session=session
                )
                logger.info(f"Stored cash flow data for {ticker} {year}")
        except Exception as e:
            error_msg = f"Error processing cash flow statement for {ticker} {year}: {str(e)}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            all_steps_succeeded = False

        # 4. Cover page
        try:
            cover_page_df = get_cover_page_values(filing)
            if cover_page_df is not None and not cover_page_df.empty:
                store_cover_page_data(
                    filing,
                    db_company,
                    db_filing,
                    session=session
                )
                logger.info(f"Stored cover page data for {ticker} {year}")
        except Exception as e:
            error_msg = f"Error processing cover page for {ticker} {year}: {str(e)}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            all_steps_succeeded = False

        # Process and store textual sections

        # 1. Business description
        try:
            business_desc = get_business_description(filing)
            if business_desc:
                create_source_document(
                    db=session,
                    filing_id=db_filing.id,
                    company_id=db_company.id,
                    report_date=report_date,
                    document_type="business_description",
                    document_name="Business Description",
                    content=business_desc
                )
                logger.info(f"Stored business description for {ticker} {year}")
        except Exception as e:
            error_msg = f"Error processing business description for {ticker} {year}: {str(e)}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            all_steps_succeeded = False

        # 2. Risk factors
        try:
            risk_factors = get_risk_factors(filing)
            if risk_factors:
                create_source_document(
                    db=session,
                    filing_id=db_filing.id,
                    company_id=db_company.id,
                    report_date=report_date,
                    document_type="risk_factors",
                    document_name="Risk Factors",
                    content=risk_factors
                )
                logger.info(f"Stored risk factors for {ticker} {year}")
        except Exception as e:
            error_msg = f"Error processing risk factors for {ticker} {year}: {str(e)}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            all_steps_succeeded = False

        # 3. Management discussion and analysis
        try:
            md_and_a = get_management_discussion(filing)
            if md_and_a:
                create_source_document(
                    db=session,
                    filing_id=db_filing.id,
                    company_id=db_company.id,
                    report_date=report_date,
                    document_type="management_discussion",
                    document_name="Management's Discussion and Analysis",
                    content=md_and_a
                )
                logger.info(f"Stored management discussion for {ticker} {year}")
        except Exception as e:
            error_msg = f"Error processing management discussion for {ticker} {year}: {str(e)}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            all_steps_succeeded = False

        # Set success based on whether all steps succeeded
        result["success"] = all_steps_succeeded

        if all_steps_succeeded:
            result["message"] = f"Successfully processed 10-K filing for {ticker} ({year})"
        else:
            result["message"] = f"Processed 10-K filing for {ticker} ({year}) with {len(result['errors'])} errors"

    except Exception as e:
        error_msg = log_exception(e, f"Error processing 10-K for {ticker} {year}: ")
        result["message"] = f"Error: {str(e)}"
        result["success"] = False

        # Make sure to roll back the transaction on error
        try:
            session.rollback()
        except Exception:
            pass

    finally:
        # Close the session
        try:
            session.close()
        except Exception:
            pass

    return result


def batch_process_10k_filings(tickers: List[str], years: List[int], edgar_contact: str = "your-email@example.com") -> List[Dict]:
    """
    Process multiple 10-K filings for a list of tickers and years.

    Args:
        tickers: List of ticker symbols
        years: List of years to retrieve
        edgar_contact: Email address to use for EDGAR API

    Returns:
        List of result dictionaries for each ticker-year combination
    """
    results = []

    for ticker in tickers:
        for year in years:
            logger.info(f"Processing 10-K for {ticker} ({year})")
            result = process_10k_filing(ticker, year, edgar_contact)
            results.append(result)

    return results