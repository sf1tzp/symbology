import json
from datetime import datetime

from edgar import Company, set_identity, get_filings
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

def get_balance_sheet_values(filing):
    xbrl = XBRL.from_filing(filing)
    df = xbrl.statements.balance_sheet().to_dataframe()
    # Filter to keep only the columns for the specified year
    # Remove rows where column `has_values` == False
    if 'has_values' in df.columns:
        df = df[df['has_values'] == True]
    if 'is_abstract' in df.columns:
        df = df[df['is_abstract'] == False]

    # Drop specified columns if they exist
    columns_to_drop = ['level', 'has_values', 'is_abstract', 'original_label', 'abstract', 'dimension']
    df = df.drop(columns=[col for col in columns_to_drop if col in df.columns])

    filtered_columns = []
    for col in df.columns:
        try:
            year = year_from_period_of_report(filing)
            col_date = datetime.strptime(col, '%Y-%m-%d')
            if col_date.year == year:
                filtered_columns.append(col)
        except ValueError:
            # If it's not a date, keep it (metadata columns)
            filtered_columns.append(col)

    df = df[filtered_columns]

    return df

def get_income_statement_values(filing):
    xbrl = XBRL.from_filing(filing)
    df = xbrl.statements.income_statement().to_dataframe()
    # Filter to keep only the columns for the specified year
    # Remove rows where column `has_values` == False
    if 'has_values' in df.columns:
        df = df[df['has_values'] == True]

    if 'is_abstract' in df.columns:
        df = df[df['is_abstract'] == False]

    # # Drop specified columns if they exist
    columns_to_drop = ['level', 'abstract', 'dimension']
    df = df.drop(columns=[col for col in columns_to_drop if col in df.columns])

    filtered_columns = []
    for col in df.columns:
        try:
            year = year_from_period_of_report(filing)
            col_date = datetime.strptime(col, '%Y-%m-%d')
            if col_date.year == year:
                filtered_columns.append(col)
        except ValueError:
            # If it's not a date, keep it (metadata columns)
            filtered_columns.append(col)
        # # Keep non-date columns (like 'label')
        # if '_' not in col:
        #     filtered_columns.append(col)
        #     continue
        #
        # # For date range columns (like "2019-07-01_2020-06-30")
        # try:
        #     # Split on underscore to get start and end dates
        #     start_date_str, end_date_str = col.split('_')
        #     # Parse the end date and check if it matches the requested year
        #     start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        #     end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        #     # If end date is one year + one day later than start date
        #     date_diff = (end_date - start_date).days
        #     if end_date.year == year and (date_diff == 365 or date_diff == 364 or date_diff == 365):
        #         # todo: rename the column to just
        #         filtered_columns.append(col)

        # except (ValueError, IndexError):
        #     # If parsing fails, keep the column anyway
        #     filtered_columns.append(col)

    df = df[filtered_columns]

    return df

def debug_company(company):
    filtered = { k: v for k, v in company.__dict__.items() if k != "filings" }
    print(json.dumps(filtered, indent=2, default=str))

def debug_filing(filing):
    filtered = { k: v for k, v in filing.__dict__.items() if k != "filings" }
    print(json.dumps(filtered, indent=2, default=str))

def year_from_period_of_report(filing):
    date = datetime.strptime(filing.period_of_report, '%Y-%m-%d')
    return date.year