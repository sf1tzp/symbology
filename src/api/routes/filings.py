"""Filings API routes."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException

from src.api.schemas import FilingResponse
from src.database.filings import get_filings_by_company
from src.utils.logging import get_logger

# Create logger for this module
logger = get_logger(__name__)

# Create router
router = APIRouter()


@router.get("/by-company/{company_id}", response_model=List[FilingResponse])
async def get_company_filings(company_id: UUID) -> List[FilingResponse]:
    """Get all filings for a specific company.

    Args:
        company_id: UUID of the company

    Returns:
        List of filings for the company
    """
    try:
        logger.debug("fetching_company_filings", company_id=str(company_id))

        filings = get_filings_by_company(company_id)

        # Convert to response models
        filing_responses = []
        for filing in filings:
            filing_responses.append(FilingResponse(
                id=filing.id,
                company_id=filing.company_id,
                accession_number=filing.accession_number,
                filing_type=filing.filing_type,
                filing_date=filing.filing_date,
                filing_url=filing.filing_url,
                period_of_report=filing.period_of_report
            ))

        logger.info("company_filings_retrieved",
                   company_id=str(company_id),
                   count=len(filing_responses))

        return filing_responses

    except Exception as e:
        logger.error("get_company_filings_failed",
                    company_id=str(company_id),
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve filings: {str(e)}") from e


@router.get("/by-ticker/{ticker}", response_model=List[FilingResponse])
async def get_filings_by_ticker(ticker: str) -> List[FilingResponse]:
    """Get all filings for a company by ticker symbol.

    Args:
        ticker: Stock ticker symbol

    Returns:
        List of filings for the company with that ticker
    """
    try:
        logger.debug("fetching_filings_by_ticker", ticker=ticker)

        # Import here to avoid circular imports
        from src.database.companies import get_company_by_ticker

        company = get_company_by_ticker(ticker)
        if not company:
            raise HTTPException(status_code=404, detail=f"Company with ticker '{ticker}' not found")

        filings = get_filings_by_company(company.id)

        # Convert to response models
        filing_responses = []
        for filing in filings:
            filing_responses.append(FilingResponse(
                id=filing.id,
                company_id=filing.company_id,
                accession_number=filing.accession_number,
                filing_type=filing.filing_type,
                filing_date=filing.filing_date,
                filing_url=filing.filing_url,
                period_of_report=filing.period_of_report
            ))

        logger.info("ticker_filings_retrieved",
                   ticker=ticker,
                   company_id=str(company.id),
                   count=len(filing_responses))

        return filing_responses

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_filings_by_ticker_failed",
                    ticker=ticker,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve filings: {str(e)}") from e