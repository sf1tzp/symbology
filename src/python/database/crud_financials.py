from datetime import datetime
import logging
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy import text

from .base import get_db_session
from .models import BalanceSheetValue, FinancialConcept, IncomeStatementValue

# Configure logging
logger = logging.getLogger(__name__)


def get_or_create_financial_concept(
    concept_id: str, label: str = None, session=None
) -> FinancialConcept:
    """Get an existing financial concept or create a new one.

    Args:
        concept_id: The standard concept identifier (e.g., us-gaap_CashAndCashEquivalentsAtCarryingValue)
        label: Human-readable label for the concept
        session: Database session (optional)

    Returns:
        FinancialConcept object
    """
    session = session or get_db_session()

    # Try to find the concept
    concept = session.query(FinancialConcept).filter(
        FinancialConcept.concept_id == concept_id
    ).first()

    if concept:
        # Concept exists, check if we need to add this label
        if label and label not in concept.labels:
            # Create a completely new list to ensure SQLAlchemy detects the change
            current_labels = concept.labels if concept.labels else []
            new_labels = current_labels + [label]
            # Assign the new list to force SQLAlchemy to detect the change
            concept.labels = new_labels
            session.commit()
            session.refresh(concept)
    else:
        # Create new concept with this label
        concept = FinancialConcept(
            concept_id=concept_id,
            labels=[label] if label else []
        )
        session.add(concept)
        session.commit()
        session.refresh(concept)

    return concept


def store_balance_sheet_value(
    company_id: int,
    filing_id: int,
    concept_id: int,
    value_date: datetime,
    value: float,
    session=None
) -> BalanceSheetValue:
    """Store a single balance sheet value.

    Args:
        company_id: ID of the company
        filing_id: ID of the filing
        concept_id: ID of the financial concept
        value_date: Date of the value
        value: The actual value
        session: Database session (optional)

    Returns:
        Created BalanceSheetValue object
    """
    session = session or get_db_session()

    # Check if this value already exists
    existing = session.query(BalanceSheetValue).filter(
        BalanceSheetValue.company_id == company_id,
        BalanceSheetValue.filing_id == filing_id,
        BalanceSheetValue.concept_id == concept_id,
        BalanceSheetValue.value_date == value_date
    ).first()

    if existing:
        # Update existing value if it changed
        if existing.value != value:
            existing.value = value
            session.commit()
            session.refresh(existing)
        return existing

    # Create new value
    bs_value = BalanceSheetValue(
        company_id=company_id,
        filing_id=filing_id,
        concept_id=concept_id,
        value_date=value_date,
        value=value
    )
    session.add(bs_value)
    session.commit()
    session.refresh(bs_value)

    return bs_value


def store_income_statement_value(
    company_id: int,
    filing_id: int,
    concept_id: int,
    value_date: datetime,
    value: float,
    session=None
) -> IncomeStatementValue:
    """Store a single income statement value.

    Args:
        company_id: ID of the company
        filing_id: ID of the filing
        concept_id: ID of the financial concept
        value_date: Date of the value
        value: The actual value
        session: Database session (optional)

    Returns:
        Created IncomeStatementValue object
    """
    session = session or get_db_session()

    # Check if this value already exists
    existing = session.query(IncomeStatementValue).filter(
        IncomeStatementValue.company_id == company_id,
        IncomeStatementValue.filing_id == filing_id,
        IncomeStatementValue.concept_id == concept_id,
        IncomeStatementValue.value_date == value_date
    ).first()

    if existing:
        # Update existing value if it changed
        if existing.value != value:
            existing.value = value
            session.commit()
            session.refresh(existing)
        return existing

    # Create new value
    is_value = IncomeStatementValue(
        company_id=company_id,
        filing_id=filing_id,
        concept_id=concept_id,
        value_date=value_date,
        value=value
    )
    session.add(is_value)
    session.commit()
    session.refresh(is_value)

    return is_value


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


def get_balance_sheet_values_by_company(
    company_id: int,
    date_start: Optional[datetime] = None,
    date_end: Optional[datetime] = None,
    session=None
) -> List[Dict[str, Any]]:
    """Get all balance sheet values for a company.

    Args:
        company_id: ID of the company
        date_start: Optional start date to filter values
        date_end: Optional end date to filter values
        session: Database session (optional)

    Returns:
        List of balance sheet values with concept information
    """
    session = session or get_db_session()

    query = session.query(
        BalanceSheetValue, FinancialConcept
    ).join(
        FinancialConcept, BalanceSheetValue.concept_id == FinancialConcept.id
    ).filter(
        BalanceSheetValue.company_id == company_id
    )

    if date_start:
        query = query.filter(BalanceSheetValue.value_date >= date_start)

    if date_end:
        query = query.filter(BalanceSheetValue.value_date <= date_end)

    results = []
    for bs_value, concept in query.all():
        results.append({
            "id": bs_value.id,
            "company_id": bs_value.company_id,
            "filing_id": bs_value.filing_id,
            "concept_id": concept.id,
            "concept_name": concept.concept_id,
            "labels": concept.labels,
            "value_date": bs_value.value_date,
            "value": bs_value.value
        })

    return results


def get_income_statement_values_by_company(
    company_id: int,
    date_start: Optional[datetime] = None,
    date_end: Optional[datetime] = None,
    session=None
) -> List[Dict[str, Any]]:
    """Get all income statement values for a company.

    Args:
        company_id: ID of the company
        date_start: Optional start date to filter values
        date_end: Optional end date to filter values
        session: Database session (optional)

    Returns:
        List of income statement values with concept information
    """
    session = session or get_db_session()

    query = session.query(
        IncomeStatementValue, FinancialConcept
    ).join(
        FinancialConcept, IncomeStatementValue.concept_id == FinancialConcept.id
    ).filter(
        IncomeStatementValue.company_id == company_id
    )

    if date_start:
        query = query.filter(IncomeStatementValue.value_date >= date_start)

    if date_end:
        query = query.filter(IncomeStatementValue.value_date <= date_end)

    results = []
    for is_value, concept in query.all():
        results.append({
            "id": is_value.id,
            "company_id": is_value.company_id,
            "filing_id": is_value.filing_id,
            "concept_id": concept.id,
            "concept_name": concept.concept_id,
            "labels": concept.labels,
            "value_date": is_value.value_date,
            "value": is_value.value
        })

    return results


def get_balance_sheet_by_date(
    company_id: int,
    as_of_date: datetime,
    session=None
) -> Dict[str, Any]:
    """Get balance sheet for a company as of a specific date.

    Args:
        company_id: ID of the company
        as_of_date: The date to get values for
        session: Database session (optional)

    Returns:
        Dictionary with concept information and values
    """
    session = session or get_db_session()

    # Use raw SQL for efficiency
    sql = text("""
    WITH ranked_values AS (
        SELECT
            bsv.concept_id,
            fc.concept_id as concept_name,
            fc.labels,
            bsv.value_date,
            bsv.value,
            ROW_NUMBER() OVER (
                PARTITION BY bsv.concept_id
                ORDER BY ABS(EXTRACT(EPOCH FROM (bsv.value_date - :target_date)))
            ) as rank
        FROM
            balance_sheet_values bsv
        JOIN
            financial_concepts fc ON bsv.concept_id = fc.id
        WHERE
            bsv.company_id = :company_id
    )
    SELECT
        concept_id,
        concept_name,
        labels,
        value_date,
        value
    FROM
        ranked_values
    WHERE
        rank = 1
    ORDER BY
        concept_name
    """)

    result = session.execute(sql, {"company_id": company_id, "target_date": as_of_date})

    balance_sheet = {
        "company_id": company_id,
        "as_of_date": as_of_date,
        "concepts": {}
    }

    for row in result:
        balance_sheet["concepts"][row.concept_name] = {
            "labels": row.labels,
            "date": row.value_date,
            "value": row.value
        }

    return balance_sheet


def get_income_statement_by_date(
    company_id: int,
    as_of_date: datetime,
    session=None
) -> Dict[str, Any]:
    """Get income statement for a company as of a specific date.

    Args:
        company_id: ID of the company
        as_of_date: The date to get values for
        session: Database session (optional)

    Returns:
        Dictionary with concept information and values
    """
    session = session or get_db_session()

    # Use raw SQL for efficiency
    sql = text("""
    WITH ranked_values AS (
        SELECT
            isv.concept_id,
            fc.concept_id as concept_name,
            fc.labels,
            isv.value_date,
            isv.value,
            ROW_NUMBER() OVER (
                PARTITION BY isv.concept_id
                ORDER BY ABS(EXTRACT(EPOCH FROM (isv.value_date - :target_date)))
            ) as rank
        FROM
            income_statement_values isv
        JOIN
            financial_concepts fc ON isv.concept_id = fc.id
        WHERE
            isv.company_id = :company_id
    )
    SELECT
        concept_id,
        concept_name,
        labels,
        value_date,
        value
    FROM
        ranked_values
    WHERE
        rank = 1
    ORDER BY
        concept_name
    """)

    result = session.execute(sql, {"company_id": company_id, "target_date": as_of_date})

    income_statement = {
        "company_id": company_id,
        "as_of_date": as_of_date,
        "concepts": {}
    }

    for row in result:
        income_statement["concepts"][row.concept_name] = {
            "labels": row.labels,
            "date": row.value_date,
            "value": row.value
        }

    return income_statement


def get_all_concepts(session=None) -> List[Dict[str, Any]]:
    """Get all financial concepts.

    Args:
        session: Database session (optional)

    Returns:
        List of all financial concepts
    """
    session = session or get_db_session()

    concepts = session.query(FinancialConcept).all()

    return [
        {
            "id": concept.id,
            "concept_id": concept.concept_id,
            "description": concept.description,
            "labels": concept.labels
        }
        for concept in concepts
    ]