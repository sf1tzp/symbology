"""
Module for cash flow statement CRUD operations.
This module handles operations related to cash flow statement values.
"""
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from .base import get_db_session
from .models import CashFlowStatementValue, FinancialConcept

# Configure logging
logger = logging.getLogger(__name__)


def store_cash_flow_statement_value(
    company_id: int,
    filing_id: int,
    concept_id: int,
    value_date: datetime,
    value: float,
    session=None
) -> CashFlowStatementValue:
    """Store a single cash flow statement value.

    Args:
        company_id: ID of the company
        filing_id: ID of the filing
        concept_id: ID of the financial concept
        value_date: Date of the value
        value: The actual value
        session: Database session (optional)

    Returns:
        Created CashFlowStatementValue object
    """
    session = session or get_db_session()

    # Check if this value already exists
    existing = session.query(CashFlowStatementValue).filter(
        CashFlowStatementValue.company_id == company_id,
        CashFlowStatementValue.filing_id == filing_id,
        CashFlowStatementValue.concept_id == concept_id,
        CashFlowStatementValue.value_date == value_date
    ).first()

    if existing:
        # Update existing value if it changed
        if existing.value != value:
            existing.value = value
            session.commit()
            session.refresh(existing)
        return existing

    # Create new value
    cf_value = CashFlowStatementValue(
        company_id=company_id,
        filing_id=filing_id,
        concept_id=concept_id,
        value_date=value_date,
        value=value
    )
    session.add(cf_value)
    session.commit()
    session.refresh(cf_value)

    return cf_value


def get_cash_flow_statement_values_by_company(
    company_id: int,
    date_start: Optional[datetime] = None,
    date_end: Optional[datetime] = None,
    session=None
) -> List[Dict[str, Any]]:
    """Get all cash flow statement values for a company.

    Args:
        company_id: ID of the company
        date_start: Optional start date to filter values
        date_end: Optional end date to filter values
        session: Database session (optional)

    Returns:
        List of cash flow statement values with concept information
    """
    session = session or get_db_session()

    query = session.query(
        CashFlowStatementValue, FinancialConcept
    ).join(
        FinancialConcept, CashFlowStatementValue.concept_id == FinancialConcept.id
    ).filter(
        CashFlowStatementValue.company_id == company_id
    )

    if date_start:
        query = query.filter(CashFlowStatementValue.value_date >= date_start)

    if date_end:
        query = query.filter(CashFlowStatementValue.value_date <= date_end)

    results = []
    for cf_value, concept in query.all():
        results.append({
            "id": cf_value.id,
            "company_id": cf_value.company_id,
            "filing_id": cf_value.filing_id,
            "concept_id": concept.id,
            "concept_name": concept.concept_id,
            "labels": concept.labels,
            "value_date": cf_value.value_date,
            "value": cf_value.value
        })

    return results


def get_cash_flow_statement_by_date(
    company_id: int,
    as_of_date: datetime,
    session=None
) -> Dict[str, Any]:
    """Get cash flow statement for a company as of a specific date.

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
            cfv.concept_id,
            fc.concept_id as concept_name,
            fc.labels,
            cfv.value_date,
            cfv.value,
            ROW_NUMBER() OVER (
                PARTITION BY cfv.concept_id
                ORDER BY ABS(EXTRACT(EPOCH FROM (cfv.value_date - :target_date)))
            ) as rank
        FROM
            cash_flow_statement_values cfv
        JOIN
            financial_concepts fc ON cfv.concept_id = fc.id
        WHERE
            cfv.company_id = :company_id
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

    cash_flow_statement = {
        "company_id": company_id,
        "as_of_date": as_of_date,
        "concepts": {}
    }

    for row in result:
        cash_flow_statement["concepts"][row.concept_name] = {
            "labels": row.labels,
            "date": row.value_date,
            "value": row.value
        }

    return cash_flow_statement