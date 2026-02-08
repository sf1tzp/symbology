"""Filings API routes."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from symbology.api.schemas import (
    CompanyResponse,
    DocumentResponse,
    DocumentWithContentResponse,
    FilingResponse,
    FilingTimelineResponse,
    GeneratedContentSummaryResponse,
)
from symbology.database.documents import get_documents_by_filing
from symbology.database.filings import Filing, get_filing_by_accession_number, get_filings_by_company
from symbology.database.generated_content import (
    get_frontpage_summary_by_ticker,
    get_generated_content_by_document_ids,
)
from symbology.utils.logging import get_logger

# Create logger for this module
logger = get_logger(__name__)

# Create router
router = APIRouter()


def _filing_to_response(filing: Filing) -> FilingResponse:
    """Convert a Filing model to FilingResponse.

    Args:
        filing: The filing object to convert

    Returns:
        FilingResponse object with filing details
    """
    return FilingResponse(
        id=filing.id,
        company_id=filing.company_id,
        accession_number=filing.accession_number,
        form=filing.form,
        filing_date=filing.filing_date,
        url=filing.url,
        period_of_report=filing.period_of_report
    )


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
        filing_responses = [_filing_to_response(filing) for filing in filings]

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
        from symbology.database.companies import get_company_by_ticker

        company = get_company_by_ticker(ticker)
        if not company:
            raise HTTPException(status_code=404, detail=f"Company with ticker '{ticker}' not found")

        filings = get_filings_by_company(company.id)

        # Convert to response models
        filing_responses = [_filing_to_response(filing) for filing in filings]

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


@router.get("/by-ticker/{ticker}/timeline", response_model=List[FilingTimelineResponse])
async def get_filings_timeline_by_ticker(
    ticker: str,
    limit: int = Query(default=20, ge=1, le=100),
) -> List[FilingTimelineResponse]:
    """Get filing timeline with nested documents and generated content for a company.

    Returns filings ordered by period_of_report ASC (oldest first) with their
    documents and associated generated content pre-loaded. Uses batch queries
    to avoid N+1 problems.

    Args:
        ticker: Stock ticker symbol
        limit: Maximum number of filings to return (default 20)

    Returns:
        List of filings with nested documents and generated content
    """
    try:
        logger.debug("fetching_filings_timeline_by_ticker", ticker=ticker)

        from symbology.database.companies import get_company_by_ticker

        # 1. Get company
        company = get_company_by_ticker(ticker)
        if not company:
            raise HTTPException(status_code=404, detail=f"Company with ticker '{ticker}' not found")

        # 2. Get filings ordered by period_of_report ASC, with documents auto-loaded via selectin
        from symbology.database.base import get_db_session
        session = get_db_session()
        filings = (
            session.query(Filing)
            .filter(Filing.company_id == company.id)
            .order_by(Filing.period_of_report.asc())
            .limit(limit)
            .all()
        )

        # 3. Collect all document IDs across all filings
        all_document_ids = []
        for filing in filings:
            for doc in filing.documents:
                all_document_ids.append(doc.id)

        # 4. Batch-fetch generated content for all documents (single query)
        gc_by_doc_id = get_generated_content_by_document_ids(all_document_ids) if all_document_ids else {}

        # 5. Assemble nested response
        timeline_responses = []
        for filing in filings:
            doc_responses = []
            for doc in filing.documents:
                gc_list = gc_by_doc_id.get(doc.id, [])
                gc_responses = [
                    GeneratedContentSummaryResponse(
                        id=gc.id,
                        content_hash=gc.content_hash,
                        short_hash=gc.get_short_hash() if gc.content_hash else None,
                        description=gc.description,
                        document_type=gc.document_type.value if gc.document_type else None,
                        summary=gc.summary,
                        created_at=gc.created_at,
                    )
                    for gc in gc_list
                ]
                doc_responses.append(DocumentWithContentResponse(
                    id=doc.id,
                    title=doc.title,
                    document_type=doc.document_type.value if doc.document_type else None,
                    content_hash=doc.content_hash,
                    short_hash=doc.get_short_hash() if doc.content_hash else None,
                    generated_content=gc_responses,
                ))

            timeline_responses.append(FilingTimelineResponse(
                id=filing.id,
                company_id=filing.company_id,
                accession_number=filing.accession_number,
                form=filing.form,
                filing_date=filing.filing_date,
                url=filing.url,
                period_of_report=filing.period_of_report,
                documents=doc_responses,
            ))

        logger.info("filings_timeline_retrieved",
                    ticker=ticker,
                    filing_count=len(timeline_responses),
                    document_count=len(all_document_ids))

        return timeline_responses

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_filings_timeline_by_ticker_failed",
                    ticker=ticker,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve filing timeline: {str(e)}") from e


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

        filing_response = _filing_to_response(filing)

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
                "title": document.title,
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
                "form": filing.form,
                "filing_date": filing.filing_date,
                "url": filing.url,
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

        # Get the frontpage summary from generated content
        summary = None
        if company.ticker:
            try:
                summary = get_frontpage_summary_by_ticker(company.ticker)
            except Exception as e:
                logger.warning("failed_to_get_frontpage_summary", ticker=company.ticker, error=str(e))

        company_response = CompanyResponse(
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