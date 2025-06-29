"""Documents API routes."""
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import PlainTextResponse

from src.api.schemas import DocumentResponse
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
    try:
        logger.info("api_get_document_by_id", document_id=str(document_id))
        document = get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return document
    except ValueError as e:
        logger.error("invalid_uuid_format", document_id=str(document_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {str(e)}"
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error("error_getting_document", document_id=str(document_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document: {str(e)}"
        ) from e

@router.get(
    "/{document_id}/content",
    response_class=PlainTextResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Document not found or has no content"},
        500: {"description": "Internal server error"}
    }
)
async def get_document_content(document_id: UUID):
    """Get a document's content by its ID."""
    try:
        logger.info("api_get_document_content", document_id=str(document_id))
        document = get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Handle both dictionary and object responses from database
        content = document.get("content") if isinstance(document, dict) else getattr(document, "content", None)
        
        if content is None:
            raise HTTPException(status_code=404, detail="Document content not available")
        
        # Return plain text response with proper content-type
        return PlainTextResponse(content=content, media_type="text/plain; charset=utf-8")
    except ValueError as e:
        logger.error("invalid_uuid_format", document_id=str(document_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {str(e)}"
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error("error_getting_document_content", document_id=str(document_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document content: {str(e)}"
        ) from e