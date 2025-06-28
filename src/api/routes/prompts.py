"""API routes for prompts."""
from typing import List

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError

from src.api.schemas import PromptCreateRequest, PromptResponse, PromptRole
from src.database import prompts as prompts_db
from src.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/by-role/{role}", response_model=List[PromptResponse])
async def get_prompts_by_role(role: PromptRole):
    """Get all prompts by role.

    Args:
        role: The role to filter prompts by (system, assistant, user)

    Returns:
        List of prompts with the specified role
    """
    try:
        session = prompts_db.get_db_session()
        db_role = prompts_db.PromptRole(role.value)
        db_prompts = session.query(prompts_db.Prompt).filter(prompts_db.Prompt.role == db_role).all()

        prompts_list = []
        for prompt in db_prompts:
            prompts_list.append(
                PromptResponse(
                    id=prompt.id,
                    name=prompt.name,
                    description=prompt.description,
                    role=prompt.role.value,
                    content=prompt.content
                )
            )

        logger.info("retrieved_prompts_by_role", role=role.value, count=len(prompts_list))
        return prompts_list

    except Exception as e:
        logger.error("get_prompts_by_role_failed", role=role.value, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve prompts: {str(e)}") from e


@router.post("/", response_model=PromptResponse, status_code=201)
async def create_prompt(prompt: PromptCreateRequest):
    """Create a new prompt.

    Args:
        prompt: Prompt data to create

    Returns:
        Created prompt
    """
    try:
        # Convert Pydantic model to dict
        prompt_data = prompt.model_dump()

        # Convert the role enum to a string for database
        prompt_data["role"] = prompts_db.PromptRole(prompt.role.value)

        # Create prompt in database
        db_prompt = prompts_db.create_prompt(prompt_data)

        # Convert to response model
        response = PromptResponse(
            id=db_prompt.id,
            name=db_prompt.name,
            description=db_prompt.description,
            role=db_prompt.role.value,
            content=db_prompt.content
        )

        logger.info("created_prompt", prompt_id=str(db_prompt.id), name=db_prompt.name)
        return response

    except ValueError as e:
        logger.error("create_prompt_validation_failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e

    except IntegrityError as e:
        logger.error("create_prompt_integrity_error", error=str(e))
        raise HTTPException(status_code=409, detail=f"Prompt already exists: {str(e)}") from e

    except Exception as e:
        logger.error("create_prompt_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create prompt: {str(e)}") from e