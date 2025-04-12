from datetime import datetime
import json

from edgar import Company, get_filings, set_identity
from edgar.xbrl2.xbrl import XBRL


def edgar_login(edgar_contact):
    set_identity(edgar_contact)

def get_company(ticker):
    return Company(ticker)

def get_10k_filing(company, year):
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

def _process_xbrl_dataframe(df, filing, columns_to_drop=None):
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
    filtered_columns = []
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

def get_balance_sheet_values(filing):
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

def get_income_statement_values(filing):
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

def store_balance_sheet_data(edgar_filing, db_company, db_filing, session=None):
    """
    Extract balance sheet data from an EDGAR filing and store it in the database.

    Args:
        edgar_filing: Filing object from edgar package
        db_company: Company object from database
        db_filing: Filing object from database
        session: SQLAlchemy session (optional)

    Returns:
        Dictionary with summary of stored data
    """
    try:
        from src.python.database.crud_financials import process_balance_sheet_dataframe

        # Get balance sheet dataframe
        balance_sheet_df = get_balance_sheet_values(edgar_filing)

        # Process and store in database
        results = process_balance_sheet_dataframe(
            company_id=db_company.id,
            filing_id=db_filing.id,
            df=balance_sheet_df,
            session=session
        )

        return results
    except ImportError as e:
        raise ImportError("Could not import database modules. Make sure you're running from the correct directory.") from e

def store_income_statement_data(edgar_filing, db_company, db_filing, session=None):
    """
    Extract income statement data from an EDGAR filing and store it in the database.

    Args:
        edgar_filing: Filing object from edgar package
        db_company: Company object from database
        db_filing: Filing object from database
        session: SQLAlchemy session (optional)

    Returns:
        Dictionary with summary of stored data
    """
    try:
        from src.python.database.crud_financials import process_income_statement_dataframe

        # Get income statement dataframe
        income_stmt_df = get_income_statement_values(edgar_filing)

        # Process and store in database using our specialized income statement function
        results = process_income_statement_dataframe(
            company_id=db_company.id,
            filing_id=db_filing.id,
            df=income_stmt_df,
            session=session
        )

        return results
    except ImportError as e:
        raise ImportError("Could not import database modules. Make sure you're running from the correct directory.") from e

def debug_company(company):
    filtered = { k: v for k, v in company.__dict__.items() if k != "filings" }
    print(json.dumps(filtered, indent=2, default=str))

def debug_filing(filing):
    filtered = { k: v for k, v in filing.__dict__.items() if k != "filings" }
    print(json.dumps(filtered, indent=2, default=str))

def year_from_period_of_report(filing):
    date = datetime.strptime(filing.period_of_report, '%Y-%m-%d')
    return date.year