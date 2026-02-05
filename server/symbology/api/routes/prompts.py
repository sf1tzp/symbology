"""API routes for prompts."""
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from symbology.api.schemas import PromptResponse
from symbology.database.prompts import get_prompt
from symbology.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt_by_id(prompt_id: UUID):
    """Get a specific prompt by ID."""
    try:
        prompt = get_prompt(prompt_id)
        if not prompt:
            logger.warning("prompt_not_found", prompt_id=str(prompt_id))
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt with ID {prompt_id} not found"
            )

        # Convert the prompt to the response schema
        response = {
            "id": prompt.id,
            "name": prompt.name,
            "description": prompt.description,
            "role": prompt.role.value,  # Convert enum to string
            "content": prompt.content
        }

        return response
    except ValueError as e:
        logger.error("invalid_uuid_format", prompt_id=str(prompt_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {str(e)}"
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_prompt_failed", prompt_id=str(prompt_id), error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving prompt"
        ) from e