"""Companies API routes."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from src.database.companies import get_company, get_company_by_cik, get_company_by_ticker
from src.utils.logging import get_logger

# Create logger for this module
logger = get_logger(__name__)

# Create router
router = APIRouter()

@router.get("/{company_id}")
async def get_company_by_id(company_id: UUID):
    """Get a company by its ID."""
    logger.info("api_get_company_by_id", company_id=str(company_id))
    company = get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@router.get("/")
async def search_companies(
    ticker: Optional[str] = Query(None, description="Company ticker symbol"),
    cik: Optional[str] = Query(None, description="Company CIK")
):
    """Search for companies by ticker or CIK."""
    if ticker:
        logger.info("api_search_companies_by_ticker", ticker=ticker)
        company = get_company_by_ticker(ticker)
        if not company:
            raise HTTPException(status_code=404, detail=f"Company with ticker {ticker} not found")
        return company
    elif cik:
        logger.info("api_search_companies_by_cik", cik=cik)
        company = get_company_by_cik(cik)
        if not company:
            raise HTTPException(status_code=404, detail=f"Company with CIK {cik} not found")
        return company
    else:
        raise HTTPException(status_code=400, detail="Either ticker or CIK parameter is required")