"""Filings API routes."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException
from src.api.schemas import CompanyResponse, DocumentResponse, FilingResponse
from src.database.documents import get_documents_by_filing
from src.database.filings import get_filing_by_accession_number, get_filings_by_company
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


@router.get("/{accession_number}", response_model=FilingResponse)
async def get_filing_by_accession(accession_number: str) -> FilingResponse:
    """Get a specific filing by its accession number.

    Args:
        accession_number: SEC accession number (e.g., 0001326380-22-000021)

    Returns:
        Filing details
    """
    try:
        logger.debug("fetching_filing_by_accession", accession_number=accession_number)

        filing = get_filing_by_accession_number(accession_number)
        if not filing:
            raise HTTPException(
                status_code=404,
                detail=f"Filing with accession number '{accession_number}' not found"
            )

        filing_response = FilingResponse(
            id=filing.id,
            company_id=filing.company_id,
            accession_number=filing.accession_number,
            filing_type=filing.filing_type,
            filing_date=filing.filing_date,
            filing_url=filing.filing_url,
            period_of_report=filing.period_of_report
        )

        logger.info("filing_retrieved_by_accession",
                   accession_number=accession_number,
                   filing_id=str(filing.id))

        return filing_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_filing_by_accession_failed",
                    accession_number=accession_number,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve filing: {str(e)}") from e


@router.get("/{accession_number}/documents", response_model=List[DocumentResponse])
async def get_filing_documents_by_accession(accession_number: str) -> List[DocumentResponse]:
    """Get all documents for a filing by its accession number.

    Args:
        accession_number: SEC accession number

    Returns:
        List of documents in the filing
    """
    try:
        logger.debug("fetching_filing_documents_by_accession", accession_number=accession_number)

        filing = get_filing_by_accession_number(accession_number)
        if not filing:
            raise HTTPException(
                status_code=404,
                detail=f"Filing with accession number '{accession_number}' not found"
            )

        documents = get_documents_by_filing(filing.id)

        # Convert to response format
        response_data = []
        for document in documents:
            doc_data = {
                "id": document.id,
                "filing_id": document.filing_id,
                "company_ticker": document.company.ticker,
                "document_name": document.document_name,
                "document_type": document.document_type,
                "content": document.content,
                "content_hash": document.content_hash,
                "short_hash": document.get_short_hash() if hasattr(document, 'get_short_hash') and document.content_hash else None,
                "filing": None
            }

            # Include filing information
            doc_data["filing"] = {
                "id": filing.id,
                "company_id": filing.company_id,
                "accession_number": filing.accession_number,
                "filing_type": filing.filing_type,
                "filing_date": filing.filing_date,
                "filing_url": filing.filing_url,
                "period_of_report": filing.period_of_report
            }

            response_data.append(doc_data)

        logger.info("filing_documents_retrieved_by_accession",
                   accession_number=accession_number,
                   document_count=len(response_data))

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_filing_documents_by_accession_failed",
                    accession_number=accession_number,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve filing documents: {str(e)}") from e


@router.get("/{accession_number}/company", response_model=CompanyResponse)
async def get_filing_company_by_accession(accession_number: str) -> CompanyResponse:
    """Get the company information for a filing by its accession number.

    Args:
        accession_number: SEC accession number

    Returns:
        Company details
    """
    try:
        logger.debug("fetching_filing_company_by_accession", accession_number=accession_number)

        filing = get_filing_by_accession_number(accession_number)
        if not filing:
            raise HTTPException(
                status_code=404,
                detail=f"Filing with accession number '{accession_number}' not found"
            )

        company = filing.company
        if not company:
            raise HTTPException(
                status_code=404,
                detail=f"Company not found for filing '{accession_number}'"
            )

        company_response = CompanyResponse(
            id=company.id,
            cik=company.cik,
            name=company.name,
            display_name=company.display_name,
            is_company=company.is_company,
            tickers=company.tickers,
            exchanges=company.exchanges,
            sic=company.sic,
            sic_description=company.sic_description,
            fiscal_year_end=company.fiscal_year_end,
            entity_type=company.entity_type,
            ein=company.ein,
            former_names=company.former_names,
            summary=company.summary
        )

        logger.info("filing_company_retrieved_by_accession",
                   accession_number=accession_number,
                   company_id=str(company.id))

        return company_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_filing_company_by_accession_failed",
                    accession_number=accession_number,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve filing company: {str(e)}") from e