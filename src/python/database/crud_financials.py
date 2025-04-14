from datetime import datetime
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from .base import get_db_session
from .models import BalanceSheetValue, CashFlowStatementValue, CoverPageValue, FinancialConcept, IncomeStatementValue

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