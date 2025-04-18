"""Companies API routes."""
import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.api.schemas import CompanyResponse
from src.database.companies import get_company, get_company_by_cik, get_company_by_ticker, search_companies_by_query
from src.ingestion.edgar_db.accessors import edgar_login
from src.ingestion.ingestion_helpers import ingest_company, ingest_filing, ingest_filing_documents, ingest_financial_data
from src.utils.config import settings
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
    cik: Optional[str] = Query(None, description="Company CIK"),
    auto_ingest: bool = Query(False, description="Automatically ingest company if not found")
):
    """Search for companies by ticker or CIK.

    If the company is not found and auto_ingest is True, this endpoint will attempt to:
    1. Ingest company data from EDGAR
    2. Ingest the 5 most recent 10-K filings
    """
    company = None

    if ticker:
        logger.info("api_search_companies_by_ticker", ticker=ticker)
        company = get_company_by_ticker(ticker)

        # If company not found and auto_ingest is enabled, try to ingest it
        if not company and auto_ingest:
            try:
                logger.info("auto_ingesting_company", ticker=ticker)

                # Setup EDGAR login
                edgar_login(settings.edgar_api.edgar_contact)

                # Step 1: Ingest company data
                edgar_company, company_id = ingest_company(ticker)

                # Get the current year to determine which years to fetch
                current_year = datetime.datetime.now().year

                # Step 2: Ingest the 5 most recent 10-K filings (or as many as available)
                filing_years = range(current_year - 1, current_year - 6, -1)
                for year in filing_years:
                    try:
                        logger.info("auto_ingesting_filing", ticker=ticker, year=year)
                        filing, filing_id = ingest_filing(company_id, edgar_company, year)

                        if filing and filing_id:
                            # Step 3: Ingest documents for this filing
                            document_uuids = ingest_filing_documents(
                                company_id, filing_id, filing, edgar_company.name
                            )

                            # Step 4: Ingest financial data for this filing
                            financial_counts = ingest_financial_data(
                                company_id, filing_id, filing
                            )

                            logger.info(
                                "auto_ingest_filing_successful",
                                ticker=ticker,
                                year=year,
                                document_count=len(document_uuids),
                                financial_values_count=sum(financial_counts.values())
                            )
                        else:
                            logger.warning(
                                "auto_ingest_no_filing_found", ticker=ticker, year=year
                            )
                    except Exception as e:
                        logger.error(
                            "auto_ingest_filing_failed",
                            ticker=ticker,
                            year=year,
                            error=str(e),
                            exc_info=True
                        )

                # Step 5: Get the newly ingested company
                company = get_company(company_id)
                logger.info(
                    "auto_ingest_company_successful",
                    ticker=ticker,
                    company_id=str(company_id)
                )
            except Exception as e:
                logger.error(
                    "auto_ingest_company_failed",
                    ticker=ticker,
                    error=str(e),
                    exc_info=True
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to automatically ingest company with ticker {ticker}: {str(e)}"
                ) from e  # Fixed: Added 'from e' to properly chain the exception

        if not company:
            raise HTTPException(status_code=404, detail=f"Company with ticker {ticker} not found")
        return company
    elif cik:
        logger.info("api_search_companies_by_cik", cik=cik)
        company = get_company_by_cik(cik)

        # If company not found and auto_ingest is enabled, try to ingest it
        if not company and auto_ingest:
            # For CIK ingestion, we can't directly use the ticker-based function
            # We'd need to adapt the ingestion process for CIK input
            # This could be an enhancement for a future version
            logger.warning("auto_ingest_by_cik_not_implemented", cik=cik)

        if not company:
            raise HTTPException(status_code=404, detail=f"Company with CIK {cik} not found")
        return company
    else:
        raise HTTPException(status_code=400, detail="Either ticker or CIK parameter is required")