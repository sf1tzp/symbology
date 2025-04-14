from datetime import datetime
from typing import List, Optional

from edgar import Company, EntityData, Filing, get_filings, set_identity
from edgar.xbrl2.xbrl import XBRL
import pandas as pd


def edgar_login(edgar_contact: str) -> None:
    """
    Set the identity for accessing EDGAR database.

    The SEC EDGAR system requires a valid email contact for API access.

    Args:
        edgar_contact: Email address to identify requests to SEC
    """
    set_identity(edgar_contact)

def get_company(ticker: str) -> EntityData:
    """
    Retrieve company information from EDGAR using its ticker symbol.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')

    Returns:
        EntityData object containing company information
    """
    return Company(ticker)

def get_10k_filing(company: EntityData, year: int) -> Optional[Filing]:
    """
    Retrieve a 10-K filing for the specified year.

    10-K filings are comprehensive annual reports that public companies must file with the SEC,
    containing detailed financial information and business disclosures.

    Args:
        company: A Company object from the edgar package
        year: The year of the filing as an integer (e.g., 2023)

    Returns:
        The 10-K filing for the specified year or None if not found
    """
    filings = get_filings(year, form="10-K")
    filings = filings.filter(cik = company.cik)
    if len(filings) > 0:
        return filings[0]
    else:
        return None

def _process_xbrl_dataframe(df: pd.DataFrame, filing: Filing, columns_to_drop: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Process XBRL dataframe by filtering rows and columns based on common criteria.

    Args:
        df: DataFrame from XBRL statement
        filing: Filing object to extract year information
        columns_to_drop: List of columns to exclude from the result

    Returns:
        Processed DataFrame
    """
    if columns_to_drop is None:
        columns_to_drop = ['level', 'has_values', 'is_abstract', 'original_label', 'abstract', 'dimension']

    # Apply filters for existing columns
    mask = True  # Start with all rows selected
    if 'is_abstract' in df.columns:
        mask = mask & (~df['is_abstract'])
    if 'has_values' in df.columns:
        mask = mask & df['has_values']

    # Apply the filter mask only if we've actually set conditions
    if not isinstance(mask, bool):
        df = df.loc[mask]

    # Drop specified columns if they exist
    df = df.drop(columns=[col for col in columns_to_drop if col in df.columns])

    # Filter columns based on year
    fiscal_date = filing.period_of_report

    # Build a list of columns to keep
    filtered_columns: List[str] = []
    for col in df.columns:
        try:
            # Try to parse as a date and match by year
            _ = datetime.strptime(col, '%Y-%m-%d')
            if col == fiscal_date:
                filtered_columns.append(col)
        except ValueError:
            # Keep non-date columns (metadata)
            filtered_columns.append(col)

    df = df[filtered_columns]

    # Remove rows where 'year' column is blank (NaN or empty string)
    if fiscal_date in df.columns:
        df = df[df[fiscal_date].notna() & (df[fiscal_date] != '')]

    return df

def get_balance_sheet_values(filing: Filing) -> pd.DataFrame:
    """
    Extract balance sheet values from a filing.

    Args:
        filing: Filing object from edgar package

    Returns:
        DataFrame containing balance sheet data for the filing's year
    """
    xbrl = XBRL.from_filing(filing)
    df = xbrl.statements.balance_sheet().to_dataframe()
    return _process_xbrl_dataframe(df, filing)

def get_income_statement_values(filing: Filing) -> pd.DataFrame:
    """
    Extract income statement values from a filing.

    Args:
        filing: Filing object from edgar package

    Returns:
        DataFrame containing income statement data for the filing's year
    """
    xbrl = XBRL.from_filing(filing)
    df = xbrl.statements.income_statement().to_dataframe()
    # Income statement uses slightly different columns to drop
    return _process_xbrl_dataframe(df, filing, columns_to_drop=['level', 'abstract', 'dimension'])

def get_cash_flow_statement_values(filing: Filing) -> pd.DataFrame:
    """
    Extract cash flow statement values from a filing.

    The cash flow statement shows how changes in balance sheet accounts and
    income affect cash and cash equivalents, categorized by operating, investing,
    and financing activities.

    Args:
        filing: Filing object from edgar package

    Returns:
        DataFrame containing cash flow data for the filing's year
    """
    xbrl = XBRL.from_filing(filing)
    df = xbrl.statements.cash_flow_statement().to_dataframe()
    # Cash flow statement uses slightly different columns to drop
    return _process_xbrl_dataframe(df, filing, columns_to_drop=['level', 'abstract', 'dimension'])

def get_cover_page_values(filing: Filing) -> pd.DataFrame:
    """
    Extract cover page information from a filing.

    The cover page contains summary information about the filing and company,
    such as the company name, fiscal year end, filing date, and other
    identifying information.

    Args:
        filing: Filing object from edgar package

    Returns:
        DataFrame containing cover page data for the filing
    """
    xbrl = XBRL.from_filing(filing)
    df = xbrl.statements["CoverPage"].to_dataframe()

    # Remove level, abstract, dimension columns
    columns_to_drop = ['level', 'abstract', 'dimension']
    df = df.drop(columns=[col for col in columns_to_drop if col in df.columns])

    # Identify the date column (typically the last column)
    date_columns = [col for col in df.columns if col not in ['concept', 'label']]

    if date_columns:
        # Rename the date column to filing.period_of_report
        df = df.rename(columns={date_columns[0]: filing.period_of_report})

        # Remove rows where the date column is empty or NA
        df = df[df[filing.period_of_report].notna() & (df[filing.period_of_report] != '')]

    return df

def get_business_description(filing: Filing) -> Optional[str]:
    """
    Extract the business description section from a 10-K filing.

    Args:
        filing: A Filing object from the edgar package

    Returns:
        The business description text as a string or None if not found
    """
    filing_obj = filing.obj()
    return filing_obj.business if hasattr(filing_obj, 'business') else None

def get_risk_factors(filing: Filing) -> Optional[str]:
    """
    Extract the risk factors section from a 10-K filing.

    Risk factors typically discuss significant risks that could adversely affect
    the company's business, financial condition, or future results.

    Args:
        filing: A Filing object from the edgar package

    Returns:
        The risk factors text as a string or None if not found
    """
    filing_obj = filing.obj()
    return filing_obj.risk_factors if hasattr(filing_obj, 'risk_factors') else None

def get_management_discussion(filing: Filing) -> Optional[str]:
    """
    Extract the management's discussion and analysis (MD&A) section from a 10-K filing.

    MD&A provides information about the company's financial condition,
    changes in financial condition, and results of operations from management's perspective.

    Args:
        filing: A Filing object from the edgar package

    Returns:
        The MD&A text as a string or None if not found
    """
    filing_obj = filing.obj()
    return filing_obj.management_discussion if hasattr(filing_obj, 'management_discussion') else None

def _year_from_period_of_report(filing: Filing) -> int:
    """
    Extract the calendar year from a filing's period of report date.

    Args:
        filing: A Filing object containing period_of_report date in 'YYYY-MM-DD' format

    Returns:
        The year as an integer
    """
    date = datetime.strptime(filing.period_of_report, '%Y-%m-%d')
    return date.year
