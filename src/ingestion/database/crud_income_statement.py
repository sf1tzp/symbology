"""
Module for income statement CRUD operations.
This module handles operations related to income statement values.
"""
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from .base import get_db_session
from .models import FinancialConcept, IncomeStatementValue

# Configure logging
logger = logging.getLogger(__name__)


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