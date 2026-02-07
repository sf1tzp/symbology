from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Tuple
from uuid import UUID

from edgar import Company, Filing
import pandas as pd
from symbology.database.companies import create_company, get_company, get_company_by_ticker, update_company
from symbology.database.documents import DocumentType, find_or_create_document
from symbology.database.filings import upsert_filing_by_accession_number
from symbology.database.financial_concepts import find_or_create_financial_concept
from symbology.database.financial_values import upsert_financial_value
from symbology.ingestion.edgar_db.accessors import (
    get_balance_sheet_values,
    get_cash_flow_statement_values,
    get_cover_page_values,
    get_income_statement_values,
    get_sections_for_document_types,
)
from symbology.utils.logging import get_logger
from symbology.utils.text import normalize_filing_text

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
                                  ticker=edgar_company.get_ticker())
                    company_data['fiscal_year_end'] = None
            else:
                logger.warning("invalid_fiscal_year_end_format",
                              value=edgar_company.fiscal_year_end,
                              ticker=edgar_company.get_ticker())
                company_data['fiscal_year_end'] = None
        else:
            company_data['fiscal_year_end'] = None

        # Store in database
        db_company = get_company_by_ticker(ticker)
        if db_company is not None:
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

def ingest_filings(db_id: str, ticker: str, form: str, count: int, include_documents: bool = True) -> List[Tuple]:
    """Fetch filings from EDGAR and store in database.

    Args:
        db_id: UUID of the company in database
        ticker: Company ticker symbol
        form: Form type (10-K, 10-Q, etc.)
        count: Number of filings to retrieve
        include_documents: Whether to also ingest filing documents

    Returns:
        List of tuples containing (ticker, form, period_of_report, filing_id)
    """
    try:
        company = Company(ticker)
        if company is None:
            #  some error
            return (None, None)

        logger.info("filings", ticker=ticker, form=form, count=count)
        # Get filings from EDGAR
        edgar_filings = company.get_filings(form=form).latest(count)

        # Handle case where fewer filings are available than requested
        if count == 1:
            filings = [edgar_filings] if edgar_filings is not None else []
        else:
            # Check how many filings are actually available
            try:
                # Try to get the filings up to the requested count
                filings = []
                for i in range(count):
                    try:
                        filing = edgar_filings[i]
                        filings.append(filing)
                    except IndexError:
                        # No more filings available
                        break
            except Exception:
                filings = []

        actual_count = len(filings)
        if actual_count < count:
            logger.warning("fewer_filings_available",
                          ticker=ticker,
                          form=form,
                          requested=count,
                          available=actual_count)

        filing_info = []

        for i in range(actual_count):
            filing = filings[i]

            # Prepare data for database
            filing_data = {
                'company_id': db_id,
                'accession_number': filing.accession_number,
                'form': filing.form,
                'filing_date': filing.filing_date,
                'period_of_report': filing.period_of_report,
                'url': filing.url,
            }

            # Store in database
            db_filing = upsert_filing_by_accession_number(filing_data)

            # Optionally ingest filing documents
            document_uuids = {}
            if include_documents:
                logger.info("ingest_filing_documents",
                           accession_number=filing.accession_number,
                           filing_id=str(db_filing.id))

                document_uuids = ingest_filing_documents(
                    company_id=db_id,
                    filing_id=db_filing.id,
                    filing=filing
                )

                logger.info("filing_documents_ingested",
                           accession_number=filing.accession_number,
                           filing_id=str(db_filing.id),
                           document_count=len(document_uuids),
                           document_types=[doc_type.value for doc_type in document_uuids.keys()])

            # Ingest financial data (XBRL) - wrapped in try/except so failures don't block pipeline
            try:
                financial_counts = ingest_financial_data(
                    company_id=db_id,
                    filing_id=db_filing.id,
                    filing=filing
                )
                logger.info("financial_data_ingested",
                           accession_number=filing.accession_number,
                           filing_id=str(db_filing.id),
                           counts=financial_counts)
            except Exception as e:
                logger.warning("financial_data_ingestion_failed",
                              accession_number=filing.accession_number,
                              filing_id=str(db_filing.id),
                              error=str(e))

            logger.info("filing_ingested",
                       company_id=str(db_id),
                       accession_number=filing.accession_number,
                       filing_id=str(db_filing.id))

            filing_info.append((ticker, form, filing.period_of_report, db_filing.id))

        return filing_info
    except Exception as e:
        logger.error("ingest_filing_failed", company_id=str(db_id), error=str(e), exc_info=True)
        raise

def ingest_filing_documents(company_id: UUID, filing_id: UUID, filing: Filing, company_name: str = None) -> Dict[DocumentType, UUID]:
    """Extract document sections from a filing and store in database.

    Args:
        company_id: UUID of the company in database
        filing_id: UUID of the filing in database
        filing: EDGAR filing data
        company_name: Name of the company (optional)

    Returns:
        Dictionary mapping DocumentType to their UUIDs in database
    """
    try:
        company = get_company(company_id)
        formatted_base_name = f"{company.name} {filing.form} {filing.period_of_report}"

        logger.info("ingest_filing_documents_start",
                   form=filing.form,
                   accession_number=filing.accession_number)

        document_uuids = {}

        # Use the new mapping system to get all available sections for this document type
        sections_content = get_sections_for_document_types(filing)
        logger.debug("sections_content_length", length=sections_content.__len__())

        for doc_type, content in sections_content.items():
            if content and content.strip():
                content = normalize_filing_text(content)
                # Create a readable document name based on the document type
                doc_type_names = {
                    DocumentType.DESCRIPTION: "Business Description",
                    DocumentType.RISK_FACTORS: "Risk Factors",
                    DocumentType.MDA: "Management Discussion and Analysis",
                    DocumentType.CONTROLS_PROCEDURES: "Controls and Procedures",
                    DocumentType.LEGAL_PROCEEDINGS: "Legal Proceedings",
                    DocumentType.MARKET_RISK: "Market Risk Disclosures",
                    DocumentType.EXECUTIVE_COMPENSATION: "Executive Compensation",
                    DocumentType.DIRECTORS_OFFICERS: "Directors and Officers"
                }

                document_name = f"{formatted_base_name} - {doc_type_names.get(doc_type, doc_type.value)}"

                doc = find_or_create_document(
                    company_id=company_id,
                    filing_id=filing_id,
                    title=document_name,
                    document_type=doc_type,
                    content=content
                )
                document_uuids[doc_type] = doc.id

                logger.debug("document_ingested",
                           document_type=doc_type.value,
                           document_id=str(doc.id),
                           content_length=len(content))

        logger.info("ingest_filing_documents_complete",
                   document_count=len(document_uuids),
                   document_types=[doc_type.value for doc_type in document_uuids.keys()])

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