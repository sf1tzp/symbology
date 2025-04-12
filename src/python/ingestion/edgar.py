from datetime import datetime
import json
from typing import List, Optional

from edgar import Company, EntityData, Filing, get_filings, set_identity
from edgar.xbrl2.xbrl import XBRL
import pandas as pd


def edgar_login(edgar_contact: str) -> None:
    set_identity(edgar_contact)

def get_company(ticker: str) -> EntityData:  # Returns edgar.Company
    return Company(ticker)

def get_10k_filing(company: EntityData, year: int) -> Optional[Filing]:
    """
    Retrieve a 10-K filing for the specified year.

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
    year = year_from_period_of_report(filing)

    # Build a list of columns to keep
    filtered_columns: List[str] = []
    for col in df.columns:
        try:
            # Try to parse as a date and match by year
            col_date = datetime.strptime(col, '%Y-%m-%d')
            if col_date.year == year:
                filtered_columns.append(col)
        except ValueError:
            # Keep non-date columns (metadata)
            filtered_columns.append(col)

    return df[filtered_columns]

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

def debug_company(company: Company) -> None:
    filtered = { k: v for k, v in company.__dict__.items() if k != "filings" }
    print(json.dumps(filtered, indent=2, default=str))

def debug_filing(filing: Filing) -> None:
    filtered = { k: v for k, v in filing.__dict__.items() if k != "filings" }
    print(json.dumps(filtered, indent=2, default=str))

def year_from_period_of_report(filing: Filing) -> int:
    date = datetime.strptime(filing.period_of_report, '%Y-%m-%d')
    return date.year
