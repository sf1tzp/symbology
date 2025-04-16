"""Documents API routes."""
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.api.schemas import DocumentContentResponse, DocumentResponse
from src.database.documents import get_document
from src.utils.logging import get_logger

# Create logger for this module
logger = get_logger(__name__)

# Create router
router = APIRouter()

@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Document not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_document_by_id(document_id: UUID):
    """Get a document by its ID."""
    logger.info("api_get_document_by_id", document_id=str(document_id))
    document = get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

@router.get(
    "/{document_id}/content",
    response_model=DocumentContentResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Document not found or has no content"},
        500: {"description": "Internal server error"}
    }
)
async def get_document_content(document_id: UUID):
    """Get a document's content by its ID."""
    logger.info("api_get_document_content", document_id=str(document_id))
    document = get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.content:
        raise HTTPException(status_code=404, detail="Document has no content")

    return {"id": document.id, "content": document.content}