"""LLM completions API routes."""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.ingestion.database.base import get_db
from src.ingestion.database.crud_llm_completion import (
    get_ai_completion,
    get_ai_completions,
    create_ai_completion,
    rate_completion
)
from src.api.schemas import (
    LLMCompletion,
    LLMCompletionCreate,
    GenerationRequest,
    GenerationResponse,
    RatingCreate,
    RatingResponse
)
from src.ingestion.llm.client import OpenAIClient
from src.ingestion.utils.logging import get_logger, log_exception

# Create logger for this module
logger = get_logger(__name__)

# Create LLM completions router
router = APIRouter()


@router.get("/", response_model=List[LLMCompletion])
async def read_completions(
    skip: int = 0,
    limit: int = 100,
    company_id: Optional[int] = None,
    filing_id: Optional[int] = None,
    source_document_id: Optional[int] = None,
    model: Optional[str] = None,
    tags: Optional[List[str]] = None,
    db: Session = Depends(get_db),
):
    """
    Retrieve a list of LLM completions.

    Parameters:
    - skip: Number of records to skip (pagination)
    - limit: Maximum number of records to return
    - company_id: Filter by company ID (optional)
    - filing_id: Filter by filing ID (optional)
    - source_document_id: Filter by source document ID (optional)
    - model: Filter by LLM model (optional)
    - tags: Filter by tags (optional)
    """
    logger.info("read_completions_requested",
               skip=skip,
               limit=limit,
               company_id=company_id,
               filing_id=filing_id,
               source_document_id=source_document_id,
               model=model,
               tags=tags)

    try:
        completions = get_ai_completions(
            db=db,
            company_id=company_id,
            filing_id=filing_id,
            source_document_id=source_document_id,
            model=model,
            tags=tags,
            skip=skip,
            limit=limit
        )
        logger.info("completions_retrieved", count=len(completions))
        return completions
    except Exception as e:
        error_msg = log_exception(e, logger, "Failed to retrieve completions: ")
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/", response_model=LLMCompletion, status_code=201)
async def create_new_completion(
    completion: LLMCompletionCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new LLM completion record.

    Parameters:
    - completion: LLM completion data
    """
    logger.info("create_completion_requested",
               prompt_template_id=completion.prompt_template_id,
               model=completion.model,
               company_id=completion.company_id)

    try:
        db_completion = create_ai_completion(db=db, **completion.dict())
        logger.info("completion_created",
                   id=db_completion.id,
                   model=db_completion.model)
        return db_completion
    except Exception as e:
        error_msg = log_exception(e, logger, "Failed to create completion: ")
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/{completion_id}", response_model=LLMCompletion)
async def read_completion(
    completion_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieve a specific LLM completion by ID.

    Parameters:
    - completion_id: LLM completion ID
    """
    logger.info("read_completion_requested", completion_id=completion_id)

    try:
        db_completion = get_ai_completion(db=db, completion_id=completion_id)
        if db_completion is None:
            logger.warning("completion_not_found", completion_id=completion_id)
            raise HTTPException(status_code=404, detail="LLM completion not found")

        logger.info("completion_retrieved", completion_id=completion_id)
        return db_completion
    except HTTPException:
        raise
    except Exception as e:
        error_msg = log_exception(e, logger, "Failed to retrieve completion: ")
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/generate", response_model=GenerationResponse)
async def generate_new_completion(
    generation_request: GenerationRequest,
    db: Session = Depends(get_db),
):
    """
    Generate a new LLM completion, store it in the database, and return it.

    Parameters:
    - generation_request: Generation request parameters
    """
    logger.info("generate_completion_requested",
               prompt_length=len(generation_request.prompt),
               model=generation_request.model,
               company_id=generation_request.company_id,
               filing_id=generation_request.filing_id)

    try:
        # Create OpenAI client
        client = OpenAIClient()

        # Generate the completion using LLM client
        completion_text = client.generate_text(
            system_prompt=generation_request.system_prompt,
            user_prompt=generation_request.prompt,
            temperature=generation_request.temperature,
            max_tokens=generation_request.max_tokens,
            model=generation_request.model
        )

        # Get token usage (would need to be captured from the actual response)
        # For now using a placeholder since we don't have access to the raw response
        token_usage = {"completion_tokens": len(completion_text) // 4, "prompt_tokens": len(generation_request.prompt) // 4}

        logger.info("completion_generated",
                   result_length=len(completion_text),
                   model=generation_request.model)

        # Create completion record in the database
        completion_data = {
            "prompt_template_id": generation_request.prompt_template_id or 1,  # Default to ID 1 if not provided
            "system_prompt": generation_request.system_prompt,
            "user_prompt": generation_request.prompt,
            "completion_text": completion_text,
            "model": generation_request.model,
            "temperature": generation_request.temperature,
            "max_tokens": generation_request.max_tokens,
            "company_id": generation_request.company_id,
            "filing_id": generation_request.filing_id,
            "source_document_ids": generation_request.source_document_ids,
            "token_usage": token_usage,
            "tags": generation_request.tags
        }

        db_completion = create_ai_completion(db=db, **completion_data)

        logger.info("generated_completion_stored", completion_id=db_completion.id)

        return GenerationResponse(
            completion_id=db_completion.id,
            text=db_completion.completion_text,
            model=db_completion.model,
            token_usage=db_completion.token_usage
        )
    except Exception as e:
        error_msg = log_exception(e, logger, "Failed to generate and store completion: ")
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/{completion_id}/rate", response_model=RatingResponse)
async def rate_completion_by_id(
    completion_id: int,
    rating_request: RatingCreate,
    db: Session = Depends(get_db),
):
    """
    Rate an LLM completion.

    Parameters:
    - completion_id: LLM completion ID
    - rating_request: Rating data
    """
    logger.info("rate_completion_requested",
               completion_id=completion_id,
               rating=rating_request.rating,
               accuracy_score=rating_request.accuracy_score,
               relevance_score=rating_request.relevance_score,
               helpfulness_score=rating_request.helpfulness_score,
               has_comments=rating_request.comments is not None)

    # Check if completion exists
    db_completion = get_ai_completion(db=db, completion_id=completion_id)
    if db_completion is None:
        logger.warning("completion_not_found", completion_id=completion_id)
        raise HTTPException(status_code=404, detail="LLM completion not found")

    try:
        # Create rating
        db_rating = rate_completion(
            db=db,
            completion_id=completion_id,
            rating=rating_request.rating,
            accuracy_score=rating_request.accuracy_score,
            relevance_score=rating_request.relevance_score,
            helpfulness_score=rating_request.helpfulness_score,
            comments=rating_request.comments
        )

        logger.info("completion_rated",
                   completion_id=completion_id,
                   rating=rating_request.rating,
                   rating_id=db_rating.id)

        return RatingResponse(
            completion_id=completion_id,
            rating_id=db_rating.id,
            rating=rating_request.rating,
            accuracy_score=rating_request.accuracy_score,
            relevance_score=rating_request.relevance_score,
            helpfulness_score=rating_request.helpfulness_score
        )
    except Exception as e:
        error_msg = log_exception(e, logger, "Failed to rate completion: ")
        raise HTTPException(status_code=500, detail=error_msg)