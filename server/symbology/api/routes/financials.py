"""Financial data API routes."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from symbology.api.schemas import FinancialComparisonResponse
from symbology.database.companies import get_company_by_ticker
from symbology.database.financial_values import get_financial_comparison_by_company
from symbology.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/{ticker}/comparison", response_model=FinancialComparisonResponse)
def get_financial_comparison(
    ticker: str,
    statement_type: Optional[str] = Query(None, description="Filter by statement type (balance_sheet, income_statement, cash_flow)"),
    periods: int = Query(5, ge=1, le=20, description="Number of periods to compare"),
):
    """Get temporal financial data comparison for a company."""
    ticker = ticker.upper()

    company = get_company_by_ticker(ticker)
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {ticker} not found")

    try:
        comparison = get_financial_comparison_by_company(
            company_id=company.id,
            statement_type=statement_type,
            limit_periods=periods,
        )
        return FinancialComparisonResponse(**comparison)
    except Exception as e:
        logger.error("financial_comparison_failed", ticker=ticker, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve financial comparison data")
