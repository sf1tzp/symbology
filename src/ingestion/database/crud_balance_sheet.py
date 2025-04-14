"""
Module for balance sheet CRUD operations.
This module handles operations related to balance sheet values.
"""
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from .base import get_db_session
from .models import BalanceSheetValue, FinancialConcept

# Configure logging
logger = logging.getLogger(__name__)


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