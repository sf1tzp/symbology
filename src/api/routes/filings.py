"""Filings API routes."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query

from src.database.filings import get_filing, get_filings_by_company
from src.database.documents import get_documents_by_filing
from src.utils.logging import get_logger

# Create logger for this module
logger = get_logger(__name__)

# Create router
router = APIRouter()

@router.get("/{filing_id}")
async def get_filing_by_id(filing_id: UUID):
    """Get a filing by its ID."""
    logger.info("api_get_filing_by_id", filing_id=str(filing_id))
    filing = get_filing(filing_id)
    if not filing:
        raise HTTPException(status_code=404, detail="Filing not found")
    return filing

@router.get("/by-company/{company_id}")
async def get_company_filings(company_id: UUID):
    """Get all filings for a specific company."""
    logger.info("api_get_company_filings", company_id=str(company_id))
    filings = get_filings_by_company(company_id)
    return filings

@router.get("/{filing_id}/documents")
async def get_filing_documents(filing_id: UUID):
    """Get all documents associated with a filing."""
    logger.info("api_get_filing_documents", filing_id=str(filing_id))
    filing = get_filing(filing_id)
    if not filing:
        raise HTTPException(status_code=404, detail="Filing not found")

    documents = get_documents_by_filing(filing_id)
    return documents