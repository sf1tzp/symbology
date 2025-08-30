from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Dict, Optional, Tuple
from uuid import UUID

from edgar import EntityData, Company, Filing
import pandas as pd
from src.database.companies import get_company_by_ticker, create_company, update_company
from src.database.documents import DocumentType, find_or_create_document
from src.database.filings import upsert_filing_by_accession_number
from src.database.financial_concepts import find_or_create_financial_concept
from src.database.financial_values import upsert_financial_value
# from src.ingestion.edgar_db.accessors import (
#     _year_from_period_of_report,
#     get_10k_filing,
#     get_balance_sheet_values,
#     get_business_description,
#     get_cash_flow_statement_values,
#     get_company,
#     get_cover_page_values,
#     get_income_statement_values,
#     get_management_discussion,
#     get_risk_factors,
# )
from src.utils.logging import get_logger

logger = get_logger(__name__)

def _is_numeric_value(value_str: str) -> bool:
    """Check if a string value can be converted to a numeric Decimal.

    Args:
        value_str: String value to check

    Returns:
        True if the value can be converted to Decimal, False otherwise
    """
    if not value_str or pd.isna(value_str):
        return False

    # Remove common formatting characters
    cleaned = str(value_str).strip().replace(',', '').replace('$', '').replace('(', '-').replace(')', '')

    # Check if it's a number (including negative numbers, decimals, scientific notation)
    try:
        Decimal(cleaned)
        return True
    except (ValueError, TypeError, InvalidOperation):
        return False

def ingest_company(ticker: str) -> Tuple[Company, UUID]:
    """Fetch company data from EDGAR and store in database.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Tuple of (EDGAR company data, company UUID in database)
    """
    try:
        # Get company data from EDGAR
        edgar_company = Company(ticker)
        entity_data = edgar_company.data

        # Prepare data for database
        company_data = {
            'name': entity_data.name,
            'display_name': entity_data.display_name,
            'ticker': edgar_company.get_ticker(),
            'exchanges': edgar_company.get_exchanges(),
            'sic': entity_data.sic,
            'sic_description': entity_data.sic_description,
            'former_names': entity_data.former_names if hasattr(entity_data, 'former_names') else [],
        }

        # Handle fiscal_year_end conversion from MMDD string to date
        if hasattr(entity_data, 'fiscal_year_end') and edgar_company.fiscal_year_end:
            # If it's in MMDD format, convert to a proper date
            if isinstance(edgar_company.fiscal_year_end, str) and len(edgar_company.fiscal_year_end) == 4:
                try:
                    # Create a date with current year and MM-DD from fiscal_year_end
                    month = int(edgar_company.fiscal_year_end[:2])
                    day = int(edgar_company.fiscal_year_end[2:])
                    fiscal_date = date(date.today().year, month, day)
                    company_data['fiscal_year_end'] = fiscal_date
                except (ValueError, TypeError):
                    logger.warning("invalid_fiscal_year_end_format",
                                  value=edgar_company.fiscal_year_end,
                                  cik=edgar_company.cik)
                    company_data['fiscal_year_end'] = None
            else:
                logger.warning("invalid_fiscal_year_end_format",
                              value=edgar_company.fiscal_year_end,
                              cik=edgar_company.cik)
                company_data['fiscal_year_end'] = None
        else:
            company_data['fiscal_year_end'] = None

        # Store in database
        db_company = get_company_by_ticker(ticker)
        if db_company != None:
            db_company = update_company(db_company.id, company_data)
        else:
            db_company = create_company(company_data)


        logger.info("company_ingested",
                   ticker=ticker,
                   company_id=str(db_company.id))

        return edgar_company, db_company.id
    except Exception as e:
        logger.error("ingest_company_failed", ticker=ticker, error=str(e), exc_info=True)
        raise

def ingest_filing(company_id: UUID, edgar_company: EntityData, year: int) -> Tuple[Optional[Filing], Optional[UUID]]:
    """Fetch 10-K filing from EDGAR and store in database.

    Args:
        company_id: UUID of the company in database
        edgar_company: EDGAR company data
        year: Year of the filing

    Returns:
        Tuple of (EDGAR filing data, filing UUID in database) or (None, None) if not found
    """
    try:
        # Get filing from EDGAR
        filing = get_10k_filing(edgar_company, year)
        if not filing:
            logger.warning("no_filing_found", company_id=str(company_id), year=year)
            return None, None

        # Prepare data for database
        filing_data = {
            'company_id': company_id,
            'accession_number': filing.accession_number,
            'filing_type': filing.form,
            'filing_date': filing.filing_date,
            'filing_url': filing.filing_url if hasattr(filing, 'filing_url') else None,
            'period_of_report': filing.period_of_report
        }

        # Store in database
        db_filing = upsert_filing_by_accession_number(filing_data)

        logger.info("filing_ingested",
                   company_id=str(company_id),
                   accession_number=filing.accession_number,
                   filing_id=str(db_filing.id),
                   year=_year_from_period_of_report(filing))

        return filing, db_filing.id
    except Exception as e:
        logger.error("ingest_filing_failed", company_id=str(company_id), year=year, error=str(e), exc_info=True)
        raise

def ingest_filing_documents(company_id: UUID, filing_id: UUID, filing: Filing, company_name: str = None) -> Dict[DocumentType, UUID]:
    """Extract document sections from a filing and store in database.

    Args:
        company_id: UUID of the company in database
        filing_id: UUID of the filing in database
        filing: EDGAR filing data
        company_name: Name of the company (optional)

    Returns:
        Dictionary mapping document names to their UUIDs in database
    """
    try:
        company = get_company(company_id)

        formatted_base_name = f"{company.name} {filing.period_of_report.year} {filing.form}"

        logger.info("ingest_business_description")
        document_uuids = {}
        # Business description
        business_description = get_business_description(filing)
        if business_description:
            doc = find_or_create_document(
                company_id=company_id,
                filing_id=filing_id,
                document_name=f"{formatted_base_name} - Business Description",
                document_type=DocumentType.DESCRIPTION,
                content=business_description
            )
            document_uuids[DocumentType.DESCRIPTION] = doc.id

        # Risk factors
        risk_factors = get_risk_factors(filing)
        if risk_factors:
            doc = find_or_create_document(
                company_id=company_id,
                filing_id=filing_id,
                document_name=f"{formatted_base_name} - Risk Factors",
                document_type=DocumentType.RISK_FACTORS,
                content=risk_factors
            )
            document_uuids[DocumentType.RISK_FACTORS] = doc.id

        # MD&A
        mda = get_management_discussion(filing)
        if mda:
            doc = find_or_create_document(
                company_id=company_id,
                filing_id=filing_id,
                document_name=f"{formatted_base_name} - Management Discussion",
                document_type=DocumentType.MDA,
                content=mda
            )
            document_uuids[DocumentType.MDA] = doc.id

        return document_uuids
    except Exception as e:
        logger.error("ingest_filing_documents_failed",
                    company_id=str(company_id),
                    filing_id=str(filing_id),
                    error=str(e),
                    exc_info=True)
        raise


def ingest_financial_data(company_id: UUID, filing_id: UUID, filing: Filing) -> Dict[str, int]:
    """Extract financial data from filing and store concepts and values in database.

    Args:
        company_id: UUID of the company in database
        filing_id: UUID of the filing in database
        filing: EDGAR filing data

    Returns:
        Dictionary with counts of financial values stored by statement type
    """
    try:
        counts = {'balance_sheet': 0, 'income_statement': 0, 'cash_flow': 0, 'cover_page': 0}

        # Balance sheet
        balance_sheet_df = get_balance_sheet_values(filing)
        for _index, row in balance_sheet_df.iterrows():
            concept_name = row['concept']
            concept_label = row['label'] if 'label' in row else None

            concept = find_or_create_financial_concept(
                name=concept_name,
                description=concept_label,
                labels=['balance_sheet']
            )

            # Get the value for the filing period date
            report_date = filing.period_of_report
            if isinstance(report_date, str):
                report_date = date.fromisoformat(report_date)

            if report_date.isoformat() in row:
                value_str = row[report_date.isoformat()]
            else:
                # Skip if there's no value for this period
                continue

            if pd.notna(value_str) and value_str != '':
                if _is_numeric_value(value_str):
                    try:
                        # Clean and convert the value
                        cleaned_value = str(value_str).strip().replace(',', '').replace('$', '').replace('(', '-').replace(')', '')
                        value = Decimal(cleaned_value)
                        upsert_financial_value(
                            company_id=company_id,
                            concept_id=concept.id,
                            value_date=report_date,
                            value=value,
                            filing_id=filing_id
                        )
                        counts['balance_sheet'] += 1
                    except (ValueError, TypeError, InvalidOperation):
                        logger.warning("invalid_balance_sheet_value",
                                      concept=concept_name,
                                      value=str(value_str))
                else:
                    # Log warning for non-numeric values
                    logger.warning("invalid_balance_sheet_value",
                                  concept=concept_name,
                                  value=str(value_str))

        # Income statement
        income_df = get_income_statement_values(filing)
        for _index, row in income_df.iterrows():
            concept_name = row['concept']
            concept_label = row['label'] if 'label' in row else None

            concept = find_or_create_financial_concept(
                name=concept_name,
                description=concept_label,
                labels=['income_statement']
            )

            # Get the value for the filing period date
            report_date = filing.period_of_report
            if isinstance(report_date, str):
                report_date = date.fromisoformat(report_date)

            if report_date.isoformat() in row:
                value_str = row[report_date.isoformat()]
            else:
                # Skip if there's no value for this period
                continue

            if pd.notna(value_str) and value_str != '':
                if _is_numeric_value(value_str):
                    try:
                        # Clean and convert the value
                        cleaned_value = str(value_str).strip().replace(',', '').replace('$', '').replace('(', '-').replace(')', '')
                        value = Decimal(cleaned_value)
                        upsert_financial_value(
                            company_id=company_id,
                            concept_id=concept.id,
                            value_date=report_date,
                            value=value,
                            filing_id=filing_id
                        )
                        counts['income_statement'] += 1
                    except (ValueError, TypeError, InvalidOperation):
                        logger.warning("invalid_income_statement_value",
                                      concept=concept_name,
                                      value=str(value_str))
                else:
                    # Log warning for non-numeric values
                    logger.warning("invalid_income_statement_value",
                                  concept=concept_name,
                                  value=str(value_str))

        # Cash flow statement
        cashflow_df = get_cash_flow_statement_values(filing)
        for _index, row in cashflow_df.iterrows():
            concept_name = row['concept']
            concept_label = row['label'] if 'label' in row else None

            concept = find_or_create_financial_concept(
                name=concept_name,
                description=concept_label,
                labels=['cash_flow']
            )

            # Get the value for the filing period date
            report_date = filing.period_of_report
            if isinstance(report_date, str):
                report_date = date.fromisoformat(report_date)

            if report_date.isoformat() in row:
                value_str = row[report_date.isoformat()]
            else:
                # Skip if there's no value for this period
                continue

            if pd.notna(value_str) and value_str != '':
                if _is_numeric_value(value_str):
                    try:
                        # Clean and convert the value
                        cleaned_value = str(value_str).strip().replace(',', '').replace('$', '').replace('(', '-').replace(')', '')
                        value = Decimal(cleaned_value)
                        upsert_financial_value(
                            company_id=company_id,
                            concept_id=concept.id,
                            value_date=report_date,
                            value=value,
                            filing_id=filing_id
                        )
                        counts['cash_flow'] += 1
                    except (ValueError, TypeError, InvalidOperation):
                        logger.warning("invalid_cash_flow_value",
                                      concept=concept_name,
                                      value=str(value_str))
                else:
                    # Log warning for non-numeric values
                    logger.warning("invalid_cash_flow_value",
                                  concept=concept_name,
                                  value=str(value_str))

        # Cover page data - only process numeric values
        cover_df = get_cover_page_values(filing)
        for _index, row in cover_df.iterrows():
            concept_name = row['concept']
            concept_label = row['label'] if 'label' in row else None

            concept = find_or_create_financial_concept(
                name=concept_name,
                description=concept_label,
                labels=['cover_page']
            )

            # Get the value for the filing period date
            report_date = filing.period_of_report
            if isinstance(report_date, str):
                report_date = date.fromisoformat(report_date)

            if report_date.isoformat() in row:
                value_str = row[report_date.isoformat()]
            else:
                # Skip if there's no value for this period
                continue

            # Only process numeric values for cover page data
            if pd.notna(value_str) and value_str != '':
                if _is_numeric_value(value_str):
                    try:
                        # Clean and convert the value
                        cleaned_value = str(value_str).strip().replace(',', '').replace('$', '').replace('(', '-').replace(')', '')
                        value = Decimal(cleaned_value)
                        upsert_financial_value(
                            company_id=company_id,
                            concept_id=concept.id,
                            value_date=report_date,
                            value=value,
                            filing_id=filing_id
                        )
                        counts['cover_page'] += 1
                    except (ValueError, TypeError, InvalidOperation):
                        logger.warning("invalid_cover_page_value",
                                      concept=concept_name,
                                      value=str(value_str))
                else:
                    # Log non-numeric values for debugging but don't try to store them
                    logger.debug("skipping_non_numeric_cover_page_value",
                               concept=concept_name,
                               value=str(value_str),
                               value_type=type(value_str).__name__)

        return counts
    except Exception as e:
        logger.error("ingest_financial_data_failed",
                    company_id=str(company_id),
                    filing_id=str(filing_id),
                    error=str(e),
                    exc_info=True)
        raise