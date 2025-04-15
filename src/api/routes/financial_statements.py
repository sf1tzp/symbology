"""Financial statements API routes."""
from typing import List, Optional, Union, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.ingestion.database.base import get_db
from src.ingestion.database.crud_balance_sheet import (
    get_balance_sheet_values_by_company,
    get_balance_sheet_by_date
)
from src.ingestion.database.crud_income_statement import (
    get_income_statement_values_by_company,
    get_income_statement_by_date
)
from src.ingestion.database.crud_cash_flow import (
    get_cash_flow_statement_values_by_company,
    get_cash_flow_statement_by_date
)
from src.ingestion.database.crud_financial_concepts import (
    get_all_concepts
)
from src.api.schemas import (
    FinancialConcept,
    FinancialStatementItem,
    FinancialStatement
)
from src.ingestion.utils.logging import get_logger, log_exception

# Create logger for this module
logger = get_logger(__name__)

# Create financial statements router
router = APIRouter()


@router.get("/balance-sheets/", response_model=List[FinancialStatementItem])
async def read_balance_sheets(
    company_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """
    Retrieve balance sheet values for a company.

    Parameters:
    - company_id: Company ID
    - start_date: Optional start date to filter values
    - end_date: Optional end date to filter values
    """
    logger.info("read_balance_sheets_requested",
                company_id=company_id,
                start_date=start_date,
                end_date=end_date)

    try:
        balance_sheets = get_balance_sheet_values_by_company(
            company_id=company_id,
            date_start=start_date,
            date_end=end_date,
            session=db
        )
        logger.info("balance_sheets_retrieved", count=len(balance_sheets))
        return balance_sheets
    except Exception as e:
        error_msg = log_exception(e, logger, "Failed to retrieve balance sheets: ")
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/balance-sheets/as-of-date", response_model=FinancialStatement)
async def read_balance_sheet_by_date(
    company_id: int,
    as_of_date: datetime,
    db: Session = Depends(get_db),
):
    """
    Retrieve a balance sheet for a company as of a specific date.

    Parameters:
    - company_id: Company ID
    - as_of_date: The date to get values for
    """
    logger.info("read_balance_sheet_by_date_requested",
                company_id=company_id,
                as_of_date=as_of_date)

    try:
        balance_sheet = get_balance_sheet_by_date(
            company_id=company_id,
            as_of_date=as_of_date,
            session=db
        )

        concept_count = len(balance_sheet.get("concepts", {}))
        logger.info("balance_sheet_retrieved",
                   company_id=company_id,
                   as_of_date=as_of_date,
                   concept_count=concept_count)

        return balance_sheet
    except Exception as e:
        error_msg = log_exception(e, logger, "Failed to retrieve balance sheet: ")
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/income-statements/", response_model=List[FinancialStatementItem])
async def read_income_statements(
    company_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """
    Retrieve income statement values for a company.

    Parameters:
    - company_id: Company ID
    - start_date: Optional start date to filter values
    - end_date: Optional end date to filter values
    """
    logger.info("read_income_statements_requested",
                company_id=company_id,
                start_date=start_date,
                end_date=end_date)

    try:
        income_statements = get_income_statement_values_by_company(
            company_id=company_id,
            date_start=start_date,
            date_end=end_date,
            session=db
        )
        logger.info("income_statements_retrieved", count=len(income_statements))
        return income_statements
    except Exception as e:
        error_msg = log_exception(e, logger, "Failed to retrieve income statements: ")
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/income-statements/as-of-date", response_model=FinancialStatement)
async def read_income_statement_by_date(
    company_id: int,
    as_of_date: datetime,
    db: Session = Depends(get_db),
):
    """
    Retrieve an income statement for a company as of a specific date.

    Parameters:
    - company_id: Company ID
    - as_of_date: The date to get values for
    """
    logger.info("read_income_statement_by_date_requested",
                company_id=company_id,
                as_of_date=as_of_date)

    try:
        income_statement = get_income_statement_by_date(
            company_id=company_id,
            as_of_date=as_of_date,
            session=db
        )

        concept_count = len(income_statement.get("concepts", {}))
        logger.info("income_statement_retrieved",
                   company_id=company_id,
                   as_of_date=as_of_date,
                   concept_count=concept_count)

        return income_statement
    except Exception as e:
        error_msg = log_exception(e, logger, "Failed to retrieve income statement: ")
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/cash-flows/", response_model=List[FinancialStatementItem])
async def read_cash_flows(
    company_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """
    Retrieve cash flow values for a company.

    Parameters:
    - company_id: Company ID
    - start_date: Optional start date to filter values
    - end_date: Optional end date to filter values
    """
    logger.info("read_cash_flows_requested",
                company_id=company_id,
                start_date=start_date,
                end_date=end_date)

    try:
        cash_flows = get_cash_flow_statement_values_by_company(
            company_id=company_id,
            date_start=start_date,
            date_end=end_date,
            session=db
        )
        logger.info("cash_flows_retrieved", count=len(cash_flows))
        return cash_flows
    except Exception as e:
        error_msg = log_exception(e, logger, "Failed to retrieve cash flows: ")
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/cash-flows/as-of-date", response_model=FinancialStatement)
async def read_cash_flow_by_date(
    company_id: int,
    as_of_date: datetime,
    db: Session = Depends(get_db),
):
    """
    Retrieve a cash flow statement for a company as of a specific date.

    Parameters:
    - company_id: Company ID
    - as_of_date: The date to get values for
    """
    logger.info("read_cash_flow_by_date_requested",
                company_id=company_id,
                as_of_date=as_of_date)

    try:
        cash_flow = get_cash_flow_statement_by_date(
            company_id=company_id,
            as_of_date=as_of_date,
            session=db
        )

        concept_count = len(cash_flow.get("concepts", {}))
        logger.info("cash_flow_retrieved",
                   company_id=company_id,
                   as_of_date=as_of_date,
                   concept_count=concept_count)

        return cash_flow
    except Exception as e:
        error_msg = log_exception(e, logger, "Failed to retrieve cash flow: ")
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/concepts/", response_model=List[FinancialConcept])
async def read_financial_concepts(
    skip: int = 0,
    limit: int = 100,
    concept_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Retrieve a list of financial concepts.

    Parameters:
    - skip: Number of records to skip (pagination)
    - limit: Maximum number of records to return
    - concept_type: Filter by concept type (optional)
    """
    logger.info("read_financial_concepts_requested",
               skip=skip,
               limit=limit,
               concept_type=concept_type)

    try:
        # Since we don't have concept_type filtering in the backend, we'll just get all concepts
        concepts = get_all_concepts(session=db)

        # Filter in memory if concept_type is provided
        if concept_type:
            concepts = [c for c in concepts if c.get("concept_type") == concept_type]

        # Apply skip and limit manually
        concepts = concepts[skip:skip+limit]

        logger.info("financial_concepts_retrieved", count=len(concepts))
        return concepts
    except Exception as e:
        error_msg = log_exception(e, logger, "Failed to retrieve financial concepts: ")
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/concepts/{concept_id}", response_model=FinancialConcept)
async def read_financial_concept(
    concept_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieve a specific financial concept by ID.

    Parameters:
    - concept_id: Financial concept ID
    """
    logger.info("read_financial_concept_requested", concept_id=concept_id)

    try:
        # Get all concepts and filter by ID
        all_concepts = get_all_concepts(session=db)

        # Find the concept with the matching ID
        concept = next((c for c in all_concepts if c["id"] == concept_id), None)

        if concept is None:
            logger.warning("financial_concept_not_found", concept_id=concept_id)
            raise HTTPException(status_code=404, detail="Financial concept not found")

        logger.info("financial_concept_retrieved",
                   concept_id=concept_id,
                   concept_name=concept.get("concept_id"))
        return concept
    except HTTPException:
        raise
    except Exception as e:
        error_msg = log_exception(e, logger, "Failed to retrieve financial concept: ")
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/company/{company_id}/summary", response_model=Dict[str, Any])
async def get_company_financial_summary(
    company_id: int,
    as_of_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """
    Get a summary of financial statements for a company.

    Parameters:
    - company_id: Company ID
    - as_of_date: Date for financial data (defaults to current date if not provided)
    """
    logger.info("company_financial_summary_requested", company_id=company_id, as_of_date=as_of_date)

    # Use current date if none provided
    target_date = as_of_date or datetime.now()

    try:
        # Get balance sheet, income statement, and cash flow data
        balance_sheet = get_balance_sheet_by_date(company_id, target_date, session=db)
        income_statement = get_income_statement_by_date(company_id, target_date, session=db)
        cash_flow = get_cash_flow_statement_by_date(company_id, target_date, session=db)

        # Combine into a summary
        summary = {
            "company_id": company_id,
            "as_of_date": target_date,
            "balance_sheet": balance_sheet.get("concepts", {}),
            "income_statement": income_statement.get("concepts", {}),
            "cash_flow": cash_flow.get("concepts", {})
        }

        logger.info("company_financial_summary_generated", company_id=company_id, as_of_date=target_date)
        return summary
    except Exception as e:
        error_msg = log_exception(e, logger, "Failed to generate financial summary: ")
        raise HTTPException(status_code=500, detail=error_msg)