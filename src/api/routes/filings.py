"""Filings API routes."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.api.schemas.documents import DocumentResponse
from src.api.schemas.filings import FilingResponse
from src.database.documents import get_documents_by_filing
from src.database.filings import get_filing, get_filings_by_company
from src.utils.logging import get_logger

# Create logger for this module
logger = get_logger(__name__)

# Create router
router = APIRouter()


@router.get(
    "/{filing_id}",
    response_model=FilingResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Filing not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_filing_by_id(filing_id: UUID):
    """Get a filing by its ID."""
    logger.info("api_get_filing_by_id", filing_id=str(filing_id))
    filing = get_filing(filing_id)
    if not filing:
        raise HTTPException(status_code=404, detail="Filing not found")
    return filing


@router.get(
    "/by-company/{company_id}",
    response_model=List[FilingResponse],
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Company not found or has no filings"},
        500: {"description": "Internal server error"},
    },
)
async def get_company_filings(company_id: UUID):
    """Get all filings for a specific company."""
    logger.info("api_get_company_filings", company_id=str(company_id))
    filings = get_filings_by_company(company_id)
    return filings


@router.get(
    "/{filing_id}/documents",
    response_model=List[DocumentResponse],
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Filing not found"},
        500: {"description": "Internal server error"},
    },
)
# FIXME: This function should not return the document contents
async def get_filing_documents(filing_id: UUID):
    """Get all documents associated with a filing."""
    logger.info("api_get_filing_documents", filing_id=str(filing_id))
    filing = get_filing(filing_id)
    if not filing:
        raise HTTPException(status_code=404, detail="Filing not found")

    documents = get_documents_by_filing(filing_id)
    document_ids = [document.id for document in documents]

    return document_ids
