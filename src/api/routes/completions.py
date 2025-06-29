"""API routes for completions."""
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.api.schemas import CompletionResponse
from src.database.completions import get_completion
from src.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


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
            "model": completion.model,
            "temperature": completion.temperature,
            "top_p": completion.top_p,
            "num_ctx": completion.num_ctx,
            "source_documents": source_document_ids,
            "created_at": completion.created_at,
            "total_duration": completion.total_duration
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