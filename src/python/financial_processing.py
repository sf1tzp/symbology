"""
Module for financial data processing and storage.
This module contains shared functionality for processing and storing financial data.
"""
from datetime import datetime
import logging
from typing import Any, Dict, Optional

import pandas as pd
from sqlalchemy.orm import Session

from .database.crud_financials import (
    get_or_create_financial_concept,
    store_balance_sheet_value,
    store_income_statement_value,
    store_cash_flow_statement_value
)
from .database.models import Company, Filing

# Configure logging
logger = logging.getLogger(__name__)

def process_balance_sheet_dataframe(
    company_id: int,
    filing_id: int,
    df: pd.DataFrame,
    session=None
) -> Dict[str, Any]:
    """Process a balance sheet dataframe and store values in the database.

    Args:
        company_id: ID of the company
        filing_id: ID of the filing
        df: Dataframe from get_balance_sheet_values()
        session: Database session (optional)

    Returns:
        Summary of processing results
    """
    from .database.base import get_db_session
    session = session or get_db_session()

    results = {
        "total_concepts": 0,
        "total_values": 0,
        "concepts": {},
        "dates": []
    }

    # Get date columns (all columns that can be parsed as dates)
    date_columns = []
    for col in df.columns:
        try:
            date_columns.append(datetime.strptime(col, '%Y-%m-%d'))
            results["dates"].append(col)
        except (ValueError, TypeError):
            continue

    if not date_columns:
        logger.error("No date columns found in dataframe")
        return results

    # Process each row in the dataframe
    for _, row in df.iterrows():
        # Skip rows without concept or label
        if 'concept' not in row or 'label' not in row:
            continue

        concept_id = row['concept']
        label = row['label']

        # Skip abstract concepts (rows with no actual values)
        if all(pd.isna(row[date_col.strftime('%Y-%m-%d')]) for date_col in date_columns):
            continue

        # Get or create concept
        concept = get_or_create_financial_concept(concept_id, label, session=session)
        results["total_concepts"] += 1
        results["concepts"][concept_id] = label

        # Store values for each date
        for date_col in date_columns:
            date_str = date_col.strftime('%Y-%m-%d')
            if date_str in row and not pd.isna(row[date_str]):
                value = float(row[date_str])
                store_balance_sheet_value(
                    company_id=company_id,
                    filing_id=filing_id,
                    concept_id=concept.id,
                    value_date=date_col,
                    value=value,
                    session=session
                )
                results["total_values"] += 1

    return results


def process_income_statement_dataframe(
    company_id: int,
    filing_id: int,
    df: pd.DataFrame,
    session=None
) -> Dict[str, Any]:
    """Process an income statement dataframe and store values in the database.

    Args:
        company_id: ID of the company
        filing_id: ID of the filing
        df: Dataframe from get_income_statement_values()
        session: Database session (optional)

    Returns:
        Summary of processing results
    """
    from .database.base import get_db_session
    session = session or get_db_session()

    results = {
        "total_concepts": 0,
        "total_values": 0,
        "concepts": {},
        "dates": []
    }

    # Get date columns (all columns that can be parsed as dates)
    date_columns = []
    for col in df.columns:
        try:
            date_columns.append(datetime.strptime(col, '%Y-%m-%d'))
            results["dates"].append(col)
        except (ValueError, TypeError):
            continue

    if not date_columns:
        logger.error("No date columns found in dataframe")
        return results

    # Process each row in the dataframe
    for _, row in df.iterrows():
        # Skip rows without concept or label
        if 'concept' not in row or 'label' not in row:
            continue

        concept_id = row['concept']
        label = row['label']

        # Skip abstract concepts (rows with no actual values)
        if all(pd.isna(row[date_col.strftime('%Y-%m-%d')]) or row[date_col.strftime('%Y-%m-%d')] == '' for date_col in date_columns):
            continue

        # Get or create concept
        concept = get_or_create_financial_concept(concept_id, label, session=session)
        results["total_concepts"] += 1
        results["concepts"][concept_id] = label

        # Store values for each date
        for date_col in date_columns:
            date_str = date_col.strftime('%Y-%m-%d')
            if date_str in row and not pd.isna(row[date_str]) and row[date_str] != '':
                value = float(row[date_str])
                store_income_statement_value(
                    company_id=company_id,
                    filing_id=filing_id,
                    concept_id=concept.id,
                    value_date=date_col,
                    value=value,
                    session=session
                )
                results["total_values"] += 1

    return results


def process_cash_flow_statement_dataframe(
    company_id: int,
    filing_id: int,
    df: pd.DataFrame,
    session=None
) -> Dict[str, Any]:
    """Process a cash flow statement dataframe and store values in the database.

    Args:
        company_id: ID of the company
        filing_id: ID of the filing
        df: Dataframe from get_cash_flow_statement_values()
        session: Database session (optional)

    Returns:
        Summary of processing results
    """
    from .database.base import get_db_session
    session = session or get_db_session()

    results = {
        "total_concepts": 0,
        "total_values": 0,
        "concepts": {},
        "dates": []
    }

    # Get date columns (all columns that can be parsed as dates)
    date_columns = []
    for col in df.columns:
        try:
            date_columns.append(datetime.strptime(col, '%Y-%m-%d'))
            results["dates"].append(col)
        except (ValueError, TypeError):
            continue

    if not date_columns:
        logger.error("No date columns found in dataframe")
        return results

    # Process each row in the dataframe
    for _, row in df.iterrows():
        # Skip rows without concept or label
        if 'concept' not in row or 'label' not in row:
            continue

        concept_id = row['concept']
        label = row['label']

        # Skip abstract concepts (rows with no actual values)
        if all(pd.isna(row[date_col.strftime('%Y-%m-%d')]) or row[date_col.strftime('%Y-%m-%d')] == '' for date_col in date_columns):
            continue

        # Get or create concept
        concept = get_or_create_financial_concept(concept_id, label, session=session)
        results["total_concepts"] += 1
        results["concepts"][concept_id] = label

        # Store values for each date
        for date_col in date_columns:
            date_str = date_col.strftime('%Y-%m-%d')
            if date_str in row and not pd.isna(row[date_str]) and row[date_str] != '':
                value = float(row[date_str])
                store_cash_flow_statement_value(
                    company_id=company_id,
                    filing_id=filing_id,
                    concept_id=concept.id,
                    value_date=date_col,
                    value=value,
                    session=session
                )
                results["total_values"] += 1

    return results


def store_balance_sheet_data(edgar_filing: Any, db_company: Company, db_filing: Filing, session: Optional[Session] = None) -> Dict[str, Any]:
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
        # Get balance sheet dataframe
        from .ingestion.edgar import get_balance_sheet_values
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


def store_income_statement_data(edgar_filing: Any, db_company: Company, db_filing: Filing, session: Optional[Session] = None) -> Dict[str, Any]:
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
        # Get income statement dataframe
        from .ingestion.edgar import get_income_statement_values
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


def store_cash_flow_statement_data(edgar_filing: Any, db_company: Company, db_filing: Filing, session: Optional[Session] = None) -> Dict[str, Any]:
    """
    Extract cash flow statement data from an EDGAR filing and store it in the database.

    Args:
        edgar_filing: Filing object from edgar package
        db_company: Company object from database
        db_filing: Filing object from database
        session: SQLAlchemy session (optional)

    Returns:
        Dictionary with summary of stored data
    """
    try:
        # Get cash flow statement dataframe
        from .ingestion.edgar import get_cash_flow_statement_values
        cash_flow_stmt_df = get_cash_flow_statement_values(edgar_filing)

        # Process and store in database
        results = process_cash_flow_statement_dataframe(
            company_id=db_company.id,
            filing_id=db_filing.id,
            df=cash_flow_stmt_df,
            session=session
        )

        return results
    except ImportError as e:
        raise ImportError("Could not import database modules. Make sure you're running from the correct directory.") from e