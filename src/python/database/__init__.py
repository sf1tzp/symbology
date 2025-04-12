from .base import Base, close_session, db_session, engine, get_db_session, init_db

# Re-export the CRUD functions for easy import
from .crud_company import (
    create_company,
    delete_company,
    get_all_companies,
    get_companies_by_ticker,
    get_company_by_cik,
    get_company_by_id,
    update_company,
    upsert_company,
)
from .crud_filing import (
    create_filing,
    delete_filing,
    get_all_filings,
    get_filing_by_accession_number,
    get_filing_by_id,
    get_filings_by_company_id,
    get_filings_by_date_range,
    get_filings_by_type,
    update_filing,
    upsert_filing,
)
from .crud_financials import (
    get_all_concepts,
    get_balance_sheet_by_date,
    get_balance_sheet_values_by_company,
    get_income_statement_by_date,
    get_income_statement_values_by_company,
    get_or_create_financial_concept,
    store_balance_sheet_value,
    store_income_statement_value,
)
from .models import (
    BalanceSheetValue,
    Company,
    Filing,
    FinancialConcept,
    IncomeStatementValue,
)

# Initialize all models and provide a clean import API
__all__ = [
    # Database session
    "engine", "db_session", "init_db", "close_session", "Base", "get_db_session",

    # Models
    "Company", "Filing", "FinancialConcept", "BalanceSheetValue", "IncomeStatementValue",

    # Company CRUD
    "create_company", "get_company_by_id", "get_company_by_cik",
    "get_companies_by_ticker", "update_company", "delete_company",
    "get_all_companies", "upsert_company",

    # Filing CRUD
    "create_filing", "get_filing_by_id", "get_filing_by_accession_number",
    "get_filings_by_company_id", "get_filings_by_type", "get_filings_by_date_range",
    "update_filing", "delete_filing", "get_all_filings", "upsert_filing",

    # Financials CRUD
    "get_or_create_financial_concept", "get_all_concepts",
    "store_balance_sheet_value", "store_income_statement_value",
    "process_balance_sheet_dataframe", "process_income_statement_dataframe",
    "get_balance_sheet_values_by_company", "get_income_statement_values_by_company",
    "get_balance_sheet_by_date", "get_income_statement_by_date",
]