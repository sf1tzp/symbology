"""Documents API routes."""
from uuid import UUID

from fastapi import APIRouter, HTTPException

from src.database.documents import get_document
from src.utils.logging import get_logger

# Create logger for this module
logger = get_logger(__name__)

# Create router
router = APIRouter()

@router.get("/{document_id}")
async def get_document_by_id(document_id: UUID):
    """Get a document by its ID."""
    logger.info("api_get_document_by_id", document_id=str(document_id))
    document = get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document