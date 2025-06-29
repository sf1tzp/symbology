"""Companies API routes."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.api.schemas import CompanyResponse
from src.database.companies import get_company, get_company_by_cik, get_company_by_ticker, search_companies_by_query
from src.utils.logging import get_logger

# Create logger for this module
logger = get_logger(__name__)

# Create router
router = APIRouter()

@router.get(
    "/search",
    response_model=List[CompanyResponse],
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Bad request - missing required parameters"},
        500: {"description": "Internal server error"}
    }
)
async def search_companies_partial(
    query: str = Query(..., description="Search query for company name or ticker"),
    limit: int = Query(10, description="Maximum number of results to return", ge=1, le=50)
):
    """Search for companies by partial name or ticker.

    Returns a list of companies that match the search query.
    This is primarily used for autocomplete functionality.
    """
    if not query or len(query.strip()) < 1:
        raise HTTPException(status_code=400, detail="Search query must not be empty")

    logger.info("api_search_companies_partial", query=query, limit=limit)
    companies = search_companies_by_query(query, limit)
    return companies

@router.get(
    "/id/{company_id}",
    response_model=CompanyResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Company not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_company_by_id(company_id: UUID):
    """Get a company by its ID."""
    logger.info("api_get_company_by_id", company_id=str(company_id))
    company = get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@router.get(
    "/",
    response_model=CompanyResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Bad request - missing required parameters"},
        404: {"description": "Company not found"},
        500: {"description": "Internal server error"}
    }
)
async def search_companies(
    ticker: Optional[str] = Query(None, description="Company ticker symbol"),
    cik: Optional[str] = Query(None, description="Company CIK")
):
    """Search for companies by ticker or CIK."""
    company = None

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