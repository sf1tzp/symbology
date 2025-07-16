"""Documents API routes."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import PlainTextResponse
from src.api.schemas import DocumentResponse
from src.database.documents import get_document, get_documents_by_filing
from src.database.documents import get_documents_by_ids as db_get_documents_by_ids
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

        # Convert document to response format
        response_data = {
            "id": document.id,
            "filing_id": document.filing_id,
            "company_id": document.company_id,
            "document_name": document.document_name,
            "content": document.content,
            "filing": None
        }

        # Include filing information if available
        if document.filing_id and hasattr(document, 'filing') and document.filing:
            filing = document.filing
            response_data["filing"] = {
                "id": filing.id,
                "company_id": filing.company_id,
                "accession_number": filing.accession_number,
                "filing_type": filing.filing_type,
                "filing_date": filing.filing_date,
                "filing_url": filing.filing_url,
                "period_of_report": filing.period_of_report
            }

        return response_data
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

@router.get(
    "/by-filing/{filing_id}",
    response_model=List[DocumentResponse],
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Filing not found or has no documents"},
        500: {"description": "Internal server error"}
    }
)
async def get_documents_by_filing_id(filing_id: UUID):
    """Get all documents for a specific filing."""
    try:
        logger.info("api_get_documents_by_filing", filing_id=str(filing_id))
        documents = get_documents_by_filing(filing_id)

        if not documents:
            raise HTTPException(status_code=404, detail="No documents found for this filing")

        # Convert to response format
        response_data = []
        for document in documents:
            doc_data = {
                "id": document.id,
                "filing_id": document.filing_id,
                "company_id": document.company_id,
                "document_name": document.document_name,
                "content": document.content,
                "filing": None
            }

            # Include filing information if available
            if hasattr(document, 'filing') and document.filing:
                filing = document.filing
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

        logger.info("api_get_documents_by_filing_success",
                   filing_id=str(filing_id),
                   document_count=len(response_data))
        return response_data

    except ValueError as e:
        logger.error("invalid_uuid_format", filing_id=str(filing_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {str(e)}"
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error("error_getting_documents_by_filing", filing_id=str(filing_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get documents for filing: {str(e)}"
        ) from e

@router.post(
    "/by-ids",
    response_model=List[DocumentResponse],
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Invalid input or UUIDs"},
        500: {"description": "Internal server error"}
    }
)
async def get_documents_by_ids(document_ids: List[UUID]):
    """Get documents by their IDs."""
    try:
        logger.info("api_get_documents_by_ids", document_ids=[str(doc_id) for doc_id in document_ids])

        if not document_ids:
            return []

        documents = db_get_documents_by_ids(document_ids)

        if not documents:
            return []

        # Convert to response format
        response_data = []
        for document in documents:
            doc_data = {
                "id": document.id,
                "filing_id": document.filing_id,
                "company_id": document.company_id,
                "document_name": document.document_name,
                "content": document.content,
                "filing": None
            }

            # Include filing information if available
            if hasattr(document, 'filing') and document.filing:
                filing = document.filing
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

        logger.info("api_get_documents_by_ids_success",
                   document_count=len(response_data),
                   requested_count=len(document_ids))
        return response_data

    except ValueError as e:
        logger.error("invalid_uuid_format", document_ids=[str(doc_id) for doc_id in document_ids], error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {str(e)}"
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error("error_getting_documents_by_ids", document_ids=[str(doc_id) for doc_id in document_ids], error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get documents: {str(e)}"
        ) from e