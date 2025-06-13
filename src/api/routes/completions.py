"""API routes for completions."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from openai import OpenAIError
from pydantic import ValidationError

from src.api.schemas.completions import CompletionCreateRequest, CompletionResponse
from src.database.completions import (
    create_completion,
    get_completion,
    get_completion_ids,
    get_completions_by_document,
)
from src.database.documents import get_document
from src.database.prompts import get_prompt
from src.llm.client import create_chat_completion
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
            logger.info(
                "completion_ids_retrieved_by_document",
                document_id=str(document_id),
                count=len(completion_ids),
            )
            return completion_ids
        else:
            # Get all completion IDs
            completion_ids = get_completion_ids()
            logger.info("all_completion_ids_retrieved", count=len(completion_ids))
            return completion_ids
    except ValueError as e:
        logger.error("invalid_uuid_format", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("completion_ids_retrieval_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get completion IDs: {str(e)}",
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
                detail=f"Completion with ID {completion_id} not found",
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
            "source_documents": source_document_ids,
        }

        logger.info("completion_retrieved", completion_id=str(completion_id))
        return response
    except ValueError as e:
        logger.error(
            "invalid_uuid_format", completion_id=str(completion_id), error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {str(e)}",
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "completion_retrieval_failed", completion_id=str(completion_id), error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get completion: {str(e)}",
        ) from e


@router.post(
    "/", response_model=CompletionResponse, status_code=status.HTTP_201_CREATED
)
async def create_new_completion(request: CompletionCreateRequest):
    """Create a new completion."""
    try:
        # Transform request into the format expected by database function
        completion_data = request.model_dump()

        # Log incoming request parameters for debugging
        logger.info(
            "completion_request_received",
            model=request.model,
            temperature=request.temperature,
            document_id=len(request.document_id) if request.document_id else None,
            system_prompt_id=str(request.system_prompt_id) if request.system_prompt_id else None,
            user_prompt_id=str(request.user_prompt_id) if request.user_prompt_id else None
        )

        # Get document content if document_ids are provided
        company_name = None
        document_text = None
        document_type = None
        period_of_report = None
        if request.document_id:
            document = get_document(request.document_id)
            if document:
                document_text = document.content
                company_name = document.company.name
                period_of_report = document.filing.period_of_report
                logger.debug("document_content_retrieved", document_id=str(request.document_id))
            else:
                logger.warning("document_not_found", prompt_id=str(request.user_prompt_id))


        # Get the system and user prompts
        system_prompt_template = None
        user_prompt_template = None

        if request.system_prompt_id:
            system_prompt = get_prompt(request.system_prompt_id)
            if system_prompt:
                system_prompt_template = system_prompt.template
                logger.debug("system_prompt_retrieved", prompt_id=str(request.system_prompt_id))
            else:
                logger.warning("system_prompt_not_found", prompt_id=str(request.system_prompt_id))

        if request.user_prompt_id:
            user_prompt = get_prompt(request.user_prompt_id)
            if user_prompt:
                user_prompt_template = user_prompt.template
                logger.debug("user_prompt_retrieved", prompt_id=str(request.user_prompt_id))
            else:
                logger.warning("user_prompt_not_found", prompt_id=str(request.user_prompt_id))





        # Call the OpenAI API to generate a completion
        try:
            # Log detailed request parameters
            logger.info(
                "openai_api_request_initiated",
                model=request.model,
                system_prompt_length=len(system_prompt_template) if system_prompt_template else 0,
                user_prompt_length=len(user_prompt_template) if user_prompt_template else 0,
                context_count=len(context_content),
                temperature=request.temperature
            )

            completion_text = create_chat_completion(
                system_prompt=system_prompt_template,
                user_prompt=user_prompt_template,
                temperature=request.temperature if request.temperature is not None else 0.7,
                model=request.model
            )

            # Create a structured conversation in context_text based on the actual exchange
            completion_data['context_text'] = [
                {'role': 'system', 'content': system_prompt_template}
            ]

            # Add context messages if they exist - without acknowledgments
            if context_content:
                for i, context in enumerate(context_content):
                    if context.strip():
                        completion_data['context_text'].append({'role': 'user', 'content': context})
                        # No assistant acknowledgment message anymore

            # Add the user prompt and assistant response
            completion_data['context_text'].append({'role': 'user', 'content': user_prompt_template})
            completion_data['context_text'].append({'role': 'assistant', 'content': completion_text})

            logger.info("openai_api_response_received")

            # Only create the completion in the database if the API call was successful
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
                "source_documents": source_document_ids,
            }

            logger.info("completion_created", completion_id=str(completion.id), model=str(completion.model))
            return response

        except OpenAIError as e:
            logger.error(
                "openai_api_request_failed",
                error=str(e),
                model=str(request.model),
                exc_info=True
            )
            # Return error response to client instead of creating a database entry
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error calling OpenAI API: {str(e)}"
            )
        except Exception as e:
            logger.error(
                "completion_generation_failed",
                error=str(e),
                model=str(request.model),
                exc_info=True
            )
            # Return error response for any other exceptions
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate completion: {str(e)}"
            )
    except (ValueError, ValidationError) as e:
        logger.error("completion_data_validation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid completion data: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("completion_creation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create completion: {str(e)}",
        ) from e
