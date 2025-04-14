"""
Module for cover page CRUD operations.
This module handles operations related to cover page values.
"""
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from .base import get_db_session
from .models import CoverPageValue, FinancialConcept

# Configure logging
logger = logging.getLogger(__name__)


def store_cover_page_value(
    company_id: int,
    filing_id: int,
    concept_id: int,
    value_date: datetime,
    value: float,
    session=None
) -> CoverPageValue:
    """Store a single cover page value.

    Args:
        company_id: ID of the company
        filing_id: ID of the filing
        concept_id: ID of the financial concept
        value_date: Date of the value
        value: The actual value
        session: Database session (optional)

    Returns:
        Created CoverPageValue object
    """
    session = session or get_db_session()

    # Check if this value already exists
    existing = session.query(CoverPageValue).filter(
        CoverPageValue.company_id == company_id,
        CoverPageValue.filing_id == filing_id,
        CoverPageValue.concept_id == concept_id,
        CoverPageValue.value_date == value_date
    ).first()

    if existing:
        # Update existing value if it changed
        if existing.value != value:
            existing.value = value
            session.commit()
            session.refresh(existing)
        return existing

    # Create new value
    cp_value = CoverPageValue(
        company_id=company_id,
        filing_id=filing_id,
        concept_id=concept_id,
        value_date=value_date,
        value=value
    )
    session.add(cp_value)
    session.commit()
    session.refresh(cp_value)

    return cp_value


def get_cover_page_values_by_company(
    company_id: int,
    date_start: Optional[datetime] = None,
    date_end: Optional[datetime] = None,
    session=None
) -> List[Dict[str, Any]]:
    """Get all cover page values for a company.

    Args:
        company_id: ID of the company
        date_start: Optional start date to filter values
        date_end: Optional end date to filter values
        session: Database session (optional)

    Returns:
        List of cover page values with concept information
    """
    session = session or get_db_session()

    query = session.query(
        CoverPageValue, FinancialConcept
    ).join(
        FinancialConcept, CoverPageValue.concept_id == FinancialConcept.id
    ).filter(
        CoverPageValue.company_id == company_id
    )

    if date_start:
        query = query.filter(CoverPageValue.value_date >= date_start)

    if date_end:
        query = query.filter(CoverPageValue.value_date <= date_end)

    results = []
    for cp_value, concept in query.all():
        results.append({
            "id": cp_value.id,
            "company_id": cp_value.company_id,
            "filing_id": cp_value.filing_id,
            "concept_id": concept.id,
            "concept_name": concept.concept_id,
            "labels": concept.labels,
            "value_date": cp_value.value_date,
            "value": cp_value.value
        })

    return results


def get_cover_page_by_date(
    company_id: int,
    as_of_date: datetime,
    session=None
) -> Dict[str, Any]:
    """Get cover page for a company as of a specific date.

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
            cpv.concept_id,
            fc.concept_id as concept_name,
            fc.labels,
            cpv.value_date,
            cpv.value,
            ROW_NUMBER() OVER (
                PARTITION BY cpv.concept_id
                ORDER BY ABS(EXTRACT(EPOCH FROM (cpv.value_date - :target_date)))
            ) as rank
        FROM
            cover_page_values cpv
        JOIN
            financial_concepts fc ON cpv.concept_id = fc.id
        WHERE
            cpv.company_id = :company_id
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

    cover_page = {
        "company_id": company_id,
        "as_of_date": as_of_date,
        "concepts": {}
    }

    for row in result:
        cover_page["concepts"][row.concept_name] = {
            "labels": row.labels,
            "date": row.value_date,
            "value": row.value
        }

    return cover_page