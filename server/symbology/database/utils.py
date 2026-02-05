"""
Database utility functions for data exploration and quality analysis.

This module contains functions for exploring the symbology database,
analyzing data quality, and performing common database operations.
"""

from typing import List, Optional, Tuple

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sqlalchemy import create_engine

from utils.config import settings

# Global engine for database queries
pd_engine = None

def get_engine():
    """Get or create the pandas database engine"""
    global pd_engine
    if pd_engine is None:
        pd_engine = create_engine(settings.database.url)
    return pd_engine

def explore_table_schema(table_name: str) -> pd.DataFrame:
    """Get detailed schema information for a specific table"""
    schema_query = f"""
    SELECT
        column_name,
        data_type,
        is_nullable,
        column_default,
        character_maximum_length
    FROM information_schema.columns
    WHERE table_name = '{table_name}'
    AND table_schema = 'public'
    ORDER BY ordinal_position;
    """
    return pd.read_sql(schema_query, get_engine())

def analyze_missing_data(table_name: str) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Analyze missing data patterns in a table"""
    # Get all data from table
    df = pd.read_sql(f"SELECT * FROM {table_name}", get_engine())

    if df.empty:
        print(f"Table {table_name} is empty")
        return None, None

    print(f"\nMissing Data Analysis for {table_name}:")
    print(f"{'='*50}")

    # Calculate missing percentages
    missing_stats = pd.DataFrame({
        'Column': df.columns,
        'Missing_Count': df.isnull().sum(),
        'Missing_Percentage': (df.isnull().sum() / len(df)) * 100
    })

    missing_stats = missing_stats.sort_values('Missing_Percentage', ascending=False)
    missing_stats = missing_stats[missing_stats['Missing_Count'] > 0]

    if missing_stats.empty:
        print("No missing data found!")
    else:
        print(missing_stats.to_string(index=False))

    return df, missing_stats

def find_duplicates(table_name: str, key_columns: Optional[List[str]] = None) -> Optional[pd.DataFrame]:
    """Find duplicate records in a table, handling array/list columns properly"""
    df = pd.read_sql(f"SELECT * FROM {table_name}", get_engine())

    if df.empty:
        print(f"\nTable {table_name} is empty")
        return None

    print(f"\nDuplicate Analysis for {table_name}:")
    print(f"Total records: {len(df)}")

    try:
        # Get column data types to handle problematic columns
        schema_info = explore_table_schema(table_name)
        array_columns = schema_info[schema_info['data_type'] == 'ARRAY']['column_name'].tolist()

        # Create a copy of the dataframe for duplicate analysis
        df_for_duplicates = df.copy()

        # Convert array/list columns to strings for duplicate detection
        for col in array_columns:
            if col in df_for_duplicates.columns:
                df_for_duplicates[col] = df_for_duplicates[col].astype(str)

        # If no key columns specified, use all columns except problematic ones
        if key_columns is None:
            duplicates = df_for_duplicates[df_for_duplicates.duplicated(keep=False)]
        else:
            # Filter key_columns to exclude array columns if they cause issues
            safe_key_columns = [col for col in key_columns if col not in array_columns]
            if safe_key_columns:
                duplicates = df_for_duplicates[df_for_duplicates.duplicated(subset=safe_key_columns, keep=False)]
            else:
                print("Warning: All key columns are array types, skipping duplicate analysis")
                return pd.DataFrame()

        print(f"Duplicate records: {len(duplicates)}")
        print(f"Duplicate percentage: {(len(duplicates)/len(df)*100):.2f}%")

        # Return original dataframe rows that are duplicates
        if not duplicates.empty:
            duplicate_indices = duplicates.index
            return df.iloc[duplicate_indices]
        else:
            return pd.DataFrame()

    except Exception as e:
        print(f"Error in duplicate analysis: {str(e)}")
        print("Skipping duplicate analysis for this table")
        return pd.DataFrame()

def get_companies_with_missing_fields(field_name: str, table_name: str = 'companies') -> pd.DataFrame:
    """Find companies missing specific fields"""
    query = f"""
    SELECT * FROM {table_name}
    WHERE {field_name} IS NULL
    OR {field_name} = ''
    OR LENGTH(TRIM({field_name})) = 0;
    """

    try:
        result = pd.read_sql(query, get_engine())
        return result
    except Exception as e:
        print(f"Error querying {field_name} in {table_name}: {str(e)}")
        return pd.DataFrame()

def analyze_companies_data_quality() -> Optional[pd.DataFrame]:
    """Comprehensive analysis of companies table data quality"""
    print("Companies Data Quality Analysis")
    print("="*50)

    # Get companies data
    companies_df = pd.read_sql("SELECT * FROM companies", get_engine())

    if companies_df.empty:
        print("No companies data found")
        return None

    print(f"Total companies: {len(companies_df)}")
    print(f"\nCompanies with missing summary: {companies_df['summary'].isnull().sum()}")
    print(f"Companies with empty summary: {(companies_df['summary'] == '').sum()}")

    # Show sample of companies missing summary
    missing_summary = companies_df[companies_df['summary'].isnull() | (companies_df['summary'] == '')]
    if not missing_summary.empty:
        print("\nSample companies missing summary:")
        print(missing_summary[['display_name']].head(10).to_string(index=False))

    return companies_df

def analyze_filing_patterns() -> pd.DataFrame:
    """Analyze filing patterns to identify anomalies"""
    print("\nFiling Patterns Analysis")
    print("="*30)

    query = """
    SELECT
        c.display_name,
        COUNT(f.id) as filing_count,
        MIN(f.filing_date) as first_filing,
        MAX(f.filing_date) as last_filing,
        COUNT(DISTINCT f.filing_type) as filing_types_count
    FROM companies c
    LEFT JOIN filings f ON c.id = f.company_id
    GROUP BY c.id, c.tickers, c.display_name
    ORDER BY filing_count DESC;
    """

    try:
        result = pd.read_sql(query, get_engine())
        print(f"Total companies: {len(result)}")
        print(f"Companies with filings: {len(result[result['filing_count'] > 0])}")
        print(f"Companies without filings: {len(result[result['filing_count'] == 0])}")
        print("\nTop 10 companies by filing count:")
        print(result.head(10).to_string(index=False))
        return result
    except Exception as e:
        print(f"Error analyzing filing patterns: {str(e)}")
        return pd.DataFrame()

def get_data_quality_summary() -> pd.DataFrame:
    """Generate a comprehensive data quality summary"""
    # Get list of tables first
    tables_query = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name;
    """
    tables_df = pd.read_sql(tables_query, get_engine())

    summary = {}

    for table_name in tables_df['table_name']:
        try:
            # Get basic stats
            count_query = f"SELECT COUNT(*) as total_rows FROM {table_name}"
            total_rows = pd.read_sql(count_query, get_engine())['total_rows'].iloc[0]

            # Get column info
            schema_info = explore_table_schema(table_name)

            summary[table_name] = {
                'total_rows': total_rows,
                'column_count': len(schema_info),
                'nullable_columns': len(schema_info[schema_info['is_nullable'] == 'YES'])
            }
        except Exception:
            continue

    return pd.DataFrame(summary).T

def quick_query(sql_query: str) -> pd.DataFrame:
    """Execute a quick SQL query and return results as DataFrame"""
    try:
        return pd.read_sql(sql_query, get_engine())
    except Exception as e:
        print(f"Query error: {str(e)}")
        return pd.DataFrame()

def search_companies(search_term: str) -> pd.DataFrame:
    """Search for companies by name or symbol"""
    query = f"""
    SELECT tickers, company_name, summary
    FROM companies
    WHERE UPPER(company_name) LIKE UPPER('%{search_term}%')
    OR UPPER(tickers) LIKE UPPER('%{search_term}%')
    ORDER BY tickers;
    """

    return quick_query(query)

def get_company_details(tickers: str) -> pd.DataFrame:
    """Get comprehensive details for a specific company"""
    query = f"""
    SELECT
        c.*,
        COUNT(f.id) as filing_count,
        COUNT(d.id) as document_count
    FROM companies c
    LEFT JOIN filings f ON c.id = f.company_id
    LEFT JOIN documents d ON c.id = d.company_id
    WHERE UPPER(c.tickers) LIKE ('%{tickers}%')
    GROUP BY c.id;
    """

    return quick_query(query)

def plot_missing_data_heatmap(table_name: str) -> None:
    """Create a heatmap of missing data patterns"""
    df = pd.read_sql(f"SELECT * FROM {table_name} LIMIT 1000", get_engine())

    if df.empty:
        print(f"No data in table {table_name}")
        return

    plt.figure(figsize=(12, 8))
    sns.heatmap(df.isnull(), cbar=True, yticklabels=False, cmap='viridis')
    plt.title(f'Missing Data Pattern for {table_name} (first 1000 rows)')
    plt.xlabel('Columns')
    plt.ylabel('Rows')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

def get_counts_for_companies(company_ids: List[str]) -> pd.DataFrame:
    """Get filing, document, aggregate counts, and summary status for a list of company IDs"""
    if not company_ids:
        return pd.DataFrame()

    ids_str = "', '".join(company_ids)
    query = f"""
    SELECT
        c.display_name,
        c.tickers,
        c.sic_description,
        CASE
            WHEN c.summary IS NOT NULL AND LENGTH(TRIM(c.summary)) > 0
            THEN 'Yes'
            ELSE 'No'
        END as has_summary,
        COUNT(DISTINCT f.id) as filing_count,
        COUNT(DISTINCT d.id) as document_count,
        COUNT(DISTINCT a.id) as aggregate_count,
        COUNT(DISTINCT comp.id) as completion_count,
        MAX(f.filing_date) as latest_filing_date,
        STRING_AGG(DISTINCT f.filing_type, ', ') as filing_types
    FROM companies c
    LEFT JOIN filings f ON c.id = f.company_id
    LEFT JOIN documents d ON c.id = d.company_id
    LEFT JOIN aggregates a ON c.id = a.company_id
    LEFT JOIN completion_document_association cda ON d.id = cda.document_id
    LEFT JOIN completions comp ON cda.completion_id = comp.id
    WHERE c.id IN ('{ids_str}')
    GROUP BY c.id, c.display_name, c.tickers, c.sic_description, c.summary
    ORDER BY filing_count DESC, document_count DESC, aggregate_count DESC, completion_count DESC;
    """

    return quick_query(query)

