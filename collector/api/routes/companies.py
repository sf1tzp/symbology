"""Companies API routes."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from collector.api.schemas import CompanyResponse
from collector.database.companies import Company, get_company, get_company_by_ticker, list_all_companies, search_companies_by_query
from collector.database.generated_content import get_frontpage_summary_by_ticker
from collector.utils.logging import get_logger

# Create logger for this module
logger = get_logger(__name__)

# Create router
router = APIRouter()


def _company_to_response(company: Company) -> CompanyResponse:
    """Convert a Company model to CompanyResponse with frontpage summary."""
    # Get the frontpage summary from generated content
    summary = None
    if company.ticker:
        try:
            summary = get_frontpage_summary_by_ticker(company.ticker)
        except Exception as e:
            logger.warning("failed_to_get_frontpage_summary", ticker=company.ticker, error=str(e))

    return CompanyResponse(
        id=company.id,
        name=company.name,
        display_name=company.display_name,
        ticker=company.ticker,
        exchanges=company.exchanges,
        sic=company.sic,
        sic_description=company.sic_description,
        fiscal_year_end=company.fiscal_year_end,
        former_names=company.former_names,
        summary=summary
    )

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
    return [_company_to_response(company) for company in companies]

@router.get(
    "/id/{company_id}",
    response_model=CompanyResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Company not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_company_by_id_route(company_id: UUID):
    """Get a company by its ID."""
    logger.info("api_get_company_by_id", company_id=str(company_id))
    company = get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return _company_to_response(company)

@router.get(
    "/by-ticker/{ticker}",
    response_model=CompanyResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Company not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_company_by_ticker_route(ticker: str):
    """Get a company by its ticker symbol."""
    logger.info("api_get_company_by_ticker_route", ticker=ticker)
    company = get_company_by_ticker(ticker)
    if not company:
        raise HTTPException(status_code=404, detail=f"Company with ticker {ticker} not found")
    return _company_to_response(company)

@router.get(
    "",
    response_model=List[CompanyResponse],
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Bad request - invalid parameters"},
        500: {"description": "Internal server error"}
    }
)
async def get_companies_route(
    search: Optional[str] = Query(None, description="Search query for company name or ticker"),
    skip: int = Query(0, description="Number of companies to skip", ge=0),
    limit: int = Query(50, description="Maximum number of companies to return", ge=1, le=100),
    ticker: Optional[str] = Query(None, description="Company ticker symbol"),
):
    """Get companies with various filtering options.

    Can be used for:
    - Searching companies by name/ticker with 'search' parameter
    - Getting paginated list with 'skip' and 'limit' parameters
    - Finding specific company by 'ticker'
    """
    # Handle specific ticker lookup
    if ticker:
        logger.info("api_get_companies_by_ticker", ticker=ticker)
        company = get_company_by_ticker(ticker)
        if not company:
            raise HTTPException(status_code=404, detail=f"Company with ticker {ticker} not found")
        return [_company_to_response(company)]

    # Handle search functionality
    if search:
        logger.info("api_get_companies_search", search=search, limit=limit)
        companies = search_companies_by_query(search, limit)
        return [_company_to_response(company) for company in companies]

    # Handle paginated list
    logger.info("api_get_companies_list", skip=skip, limit=limit)
    companies = list_all_companies(offset=skip, limit=limit)
    return [_company_to_response(company) for company in companies]


