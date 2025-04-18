"""API routes for completions."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from src.api.schemas import CompletionCreateRequest, CompletionResponse
from src.database.completions import create_completion, get_completion, get_completion_ids, get_completions_by_document
from src.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/", response_model=List[UUID])
async def get_all_completion_ids(document_id: Optional[UUID] = None):
    """
    Get IDs of completions in the database.

    If document_id is provided, returns completions that use this document as a source.
    Otherwise, returns all completion IDs.
    """
    try:
        if document_id:
            # Get completions filtered by document ID
            completions = get_completions_by_document(document_id)
            completion_ids = [completion.id for completion in completions]
            logger.info("retrieved_completion_ids_by_document", document_id=str(document_id), count=len(completion_ids))
            return completion_ids
        else:
            # Get all completion IDs
            completion_ids = get_completion_ids()
            return completion_ids
    except ValueError as e:
        logger.error("invalid_uuid_format", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {str(e)}"
        ) from e
    except Exception as e:
        logger.error("error_getting_completion_ids", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get completion IDs: {str(e)}"
        ) from e


@router.get("/{completion_id}", response_model=CompletionResponse)
async def get_completion_by_id(completion_id: UUID):
    """Get a specific completion by ID."""
    try:
        completion = get_completion(completion_id)
        if not completion:
            logger.warning("completion_not_found", completion_id=str(completion_id))
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Completion with ID {completion_id} not found"
            )

        # Convert the completion to the response schema
        source_document_ids = [doc.id for doc in completion.source_documents]

        response = {
            "id": completion.id,
            "system_prompt_id": completion.system_prompt_id,
            "user_prompt_id": completion.user_prompt_id,
            "context_text": completion.context_text,
            "model": completion.model,
            "temperature": completion.temperature,
            "top_p": completion.top_p,
            "source_documents": source_document_ids
        }

        return response
    except ValueError as e:
        logger.error("invalid_uuid_format", completion_id=str(completion_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {str(e)}"
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error("error_getting_completion", completion_id=str(completion_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get completion: {str(e)}"
        ) from e


@router.post("/", response_model=CompletionResponse, status_code=status.HTTP_201_CREATED)
async def create_new_completion(request: CompletionCreateRequest):
    """Create a new completion."""
    try:
        # Transform request into the format expected by database function
        completion_data = request.model_dump()

        # Create the completion in the database
        completion = create_completion(completion_data)

        # Convert the completion to the response schema
        source_document_ids = [doc.id for doc in completion.source_documents]

        response = {
            "id": completion.id,
            "system_prompt_id": completion.system_prompt_id,
            "user_prompt_id": completion.user_prompt_id,
            "context_text": completion.context_text,
            "model": completion.model,
            "temperature": completion.temperature,
            "top_p": completion.top_p,
            "source_documents": source_document_ids
        }

        logger.info("created_completion", completion_id=str(completion.id))
        return response
    except (ValueError, ValidationError) as e:
        logger.error("invalid_completion_data", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid completion data: {str(e)}"
        ) from e
    except Exception as e:
        logger.error("error_creating_completion", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create completion: {str(e)}"
        ) from e