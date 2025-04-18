"""API routes for completions."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from src.api.schemas import CompletionCreateRequest, CompletionResponse
from src.database.completions import create_completion, get_completion, get_completion_ids, get_completions_by_document
from src.database.documents import get_document
from src.database.prompts import get_prompt
from src.llm.client import OpenAIClient
from src.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)
ai_client = OpenAIClient()


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
async def create_new_completion(request: CompletionCreateRequest):
    """Create a new completion."""
    try:
        # Transform request into the format expected by database function
        completion_data = request.model_dump()

        # Log incoming request parameters for debugging
        logger.info(
            "incoming_completion_request",
            model=request.model,
            temperature=request.temperature,
            document_ids=[str(doc_id) for doc_id in request.document_ids] if request.document_ids else [],
            system_prompt_id=str(request.system_prompt_id) if request.system_prompt_id else None,
            user_prompt_id=str(request.user_prompt_id) if request.user_prompt_id else None
        )

        # Get the system and user prompts
        system_prompt_text = None
        user_prompt_text = None

        if request.system_prompt_id:
            system_prompt = get_prompt(request.system_prompt_id)
            if system_prompt:
                system_prompt_text = system_prompt.template

        if request.user_prompt_id:
            user_prompt = get_prompt(request.user_prompt_id)
            if user_prompt:
                user_prompt_text = user_prompt.template

        # If no system prompt provided, use a default one
        if not system_prompt_text:
            system_prompt_text = "You are a helpful assistant specializing in financial analysis. Analyze the content provided in the user's messages. Do not ask for additional content or instructions unless clarification is truly needed. Respond directly based on the content already provided."

        # If no user prompt provided, extract from context_text
        if not user_prompt_text:
            user_messages = [
                msg.get('content') for msg in completion_data.get('context_text', [])
                if isinstance(msg, dict) and msg.get('role') == 'user'
            ]
            if user_messages:
                user_prompt_text = user_messages[0]
            else:
                user_prompt_text = "Please provide a comprehensive analysis."

        # Get document content if document_ids are provided
        context_content = []
        if request.document_ids:
            for doc_id in request.document_ids:
                document = get_document(doc_id)
                if document and document.content:
                    context_content.append(document.content)
                    logger.debug(
                        "document_content_fetched",
                        document_id=str(doc_id),
                        content_length=len(document.content) if document.content else 0
                    )
                else:
                    logger.warn("document_not_found_or_empty", document_id=str(doc_id))

        # Initialize context_text if it doesn't exist
        if 'context_text' not in completion_data or not completion_data['context_text']:
            completion_data['context_text'] = []

        # Call the OpenAI API to generate a completion
        try:
            # Log detailed request parameters
            logger.info(
                "calling_openai_api",
                model=request.model,
                system_prompt_length=len(system_prompt_text) if system_prompt_text else 0,
                user_prompt_length=len(user_prompt_text) if user_prompt_text else 0,
                context_count=len(context_content),
                temperature=request.temperature,
                model_type=type(request.model).__name__,
                model_value=str(request.model) if request.model else "None"
            )

            completion_text = ai_client.generate_text(
                system_prompt=system_prompt_text,
                user_prompt=user_prompt_text,
                context_texts=context_content if context_content else None,
                temperature=request.temperature if request.temperature is not None else 0.7,
                max_tokens=4000,  # Default max tokens
                model=request.model
            )

            # Create a structured conversation in context_text based on the actual exchange
            completion_data['context_text'] = [
                {'role': 'system', 'content': system_prompt_text}
            ]

            # Add context messages if they exist - without acknowledgments
            if context_content:
                for i, context in enumerate(context_content):
                    if context.strip():
                        completion_data['context_text'].append({'role': 'user', 'content': context})
                        # No assistant acknowledgment message anymore

            # Add the user prompt and assistant response
            completion_data['context_text'].append({'role': 'user', 'content': user_prompt_text})
            completion_data['context_text'].append({'role': 'assistant', 'content': completion_text})

            logger.info("Successfully received completion from OpenAI API")

        except Exception as e:
            logger.error(
                "openai_api_call_failed",
                error=str(e),
                model=request.model,
                exc_info=True
            )
            # Continue with creation but log the error
            # Add the error message to the context_text
            error_message = f"Error generating completion: {str(e)}"
            completion_data['context_text'].append({
                'role': 'system',
                'content': f"ERROR: {error_message}"
            })
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