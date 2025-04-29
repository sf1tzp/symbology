"""API routes for completions."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from src.api.schemas import CompletionResponse, SingleDocumentCompletionRequest
from src.database import create_completion, get_completion, get_completion_ids, get_completions_by_document, get_document
from src.llm import create_chat_completion, format_user_prompt, SYSTEM_PROMPTS, USER_PROMPT_TEMPLATES
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
        if (document_id):
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
async def single_document_analysis(request: SingleDocumentCompletionRequest):
    """Create a new completion."""
    completion_data = {
        "document_ids": [
            request.document_id
        ],
        "model": request.model,
        "temperature": request.temperature,


    }
    try:
        # Transform request into the format expected by database function
        completion_data = request.model_dump()

        # Log incoming request parameters for debugging
        logger.info(
            "incoming_completion_request",
            model=request.model,
            temperature=request.temperature,
            document_id=request.document_id,
            system_prompt_id=request.system_prompt_id,
            user_prompt_id=request.user_prompt_id
        )

        document = get_document(document_id=request.document_id)

        system_prompt = SYSTEM_PROMPTS[document.document_name]
        user_prompt = USER_PROMPT_TEMPLATES[document.document_name]

        format_user_prompt(user_prompt, {
            "company_name": document.company.name,
            "year": document.filing.period_of_report.year,
            "content": document.content
        })

        # Call the OpenAI API to generate a completion
        try:
            # Log detailed request parameters
            logger.info(
                "Making chat completion for {document.company.name} {document.filing.filing_type} {document.document_name}",
                model=request.model,
                system_prompt_length=len(system_prompt),
                user_prompt_length=len(user_prompt),
                temperature=request.temperature,
            )

            response = create_chat_completion(request.model, request.temperature, system_prompt, user_prompt)
            logger.info(f"Successfully received completion {len(response)} from OpenAI API")
            completion_data["content"] = response

        except Exception as e:
            logger.error(
                "OpenAI API call failed",
                error=str(e),
                exc_info=True
            )
            raise e

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

        logger.info("created_completion", completion_id=str(completion.id), model=completion.model)
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