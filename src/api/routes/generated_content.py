"""API routes for generated content."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from src.api.schemas import GeneratedContentResponse, GeneratedContentCreateRequest
from src.database.generated_content import (
    get_generated_content,
    get_generated_content_by_hash,
    get_generated_content_by_company_and_ticker,
    get_recent_generated_content_by_ticker,
    create_generated_content,
    update_generated_content,
    delete_generated_content,
    get_generated_content_by_source_document,
    get_generated_content_by_source_content
)
from src.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get(
    "/by-ticker/{ticker}",
    response_model=List[GeneratedContentResponse],
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Company not found or has no generated content"},
        500: {"description": "Internal server error"}
    }
)
async def get_company_generated_content_by_ticker(ticker: str):
    """Get the most recent generated content for each document type by ticker.

    Returns only the most recent content for each document type to avoid duplicates
    and ensure you get the latest AI-generated insights.

    Args:
        ticker: Company ticker symbol (e.g., 'AAPL', 'GOOGL')

    Returns:
        List of GeneratedContentResponse objects - the most recent content for each document type
    """
    logger.info("api_get_company_generated_content_by_ticker", ticker=ticker)

    try:
        content_list = get_recent_generated_content_by_ticker(ticker)

        if not content_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No generated content found for company with ticker '{ticker}'"
            )

        # Convert database models to response schemas
        response_data = []
        for content in content_list:
            content_dict = content.to_dict()
            response_data.append(GeneratedContentResponse(**content_dict))

        logger.info("api_get_company_generated_content_by_ticker_success",
                   ticker=ticker, count=len(response_data))
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error("api_get_company_generated_content_by_ticker_failed",
                    ticker=ticker, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving generated content"
        )


@router.get(
    "/by-ticker/{ticker}/{content_hash}",
    response_model=GeneratedContentResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Generated content not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_generated_content_by_ticker_and_hash(ticker: str, content_hash: str):
    """Get generated content by ticker and content hash for URL routing.

    This endpoint supports the URL format: /g/{ticker}/{hash}

    Args:
        ticker: Company ticker symbol
        content_hash: Full or partial SHA256 hash of the content

    Returns:
        GeneratedContentResponse object with the content details
    """
    logger.info("api_get_generated_content_by_ticker_and_hash",
               ticker=ticker, content_hash=content_hash)

    try:
        content = get_generated_content_by_company_and_ticker(ticker, content_hash)

        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Generated content not found for ticker '{ticker}' and hash '{content_hash}'"
            )

        content_dict = content.to_dict()
        response = GeneratedContentResponse(**content_dict)

        logger.info("api_get_generated_content_by_ticker_and_hash_success",
                   ticker=ticker, content_hash=content_hash, content_id=str(content.id))
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("api_get_generated_content_by_ticker_and_hash_failed",
                    ticker=ticker, content_hash=content_hash, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving generated content"
        )


@router.get(
    "/{content_id}",
    response_model=GeneratedContentResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Generated content not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_generated_content_by_id(content_id: UUID):
    """Get generated content by its ID.

    Args:
        content_id: UUID of the generated content

    Returns:
        GeneratedContentResponse object with the content details
    """
    logger.info("api_get_generated_content_by_id", content_id=str(content_id))

    try:
        content = get_generated_content(content_id)

        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Generated content not found with ID: {content_id}"
            )

        content_dict = content.to_dict()
        response = GeneratedContentResponse(**content_dict)

        logger.info("api_get_generated_content_by_id_success", content_id=str(content_id))
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("api_get_generated_content_by_id_failed",
                    content_id=str(content_id), error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving generated content"
        )


@router.get(
    "/by-hash/{content_hash}",
    response_model=GeneratedContentResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Generated content not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_generated_content_by_hash_only(content_hash: str):
    """Get generated content by its content hash only.

    Args:
        content_hash: Full or partial SHA256 hash of the content

    Returns:
        GeneratedContentResponse object with the content details
    """
    logger.info("api_get_generated_content_by_hash", content_hash=content_hash)

    try:
        content = get_generated_content_by_hash(content_hash)

        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Generated content not found with hash: {content_hash}"
            )

        content_dict = content.to_dict()
        response = GeneratedContentResponse(**content_dict)

        logger.info("api_get_generated_content_by_hash_success",
                   content_hash=content_hash, content_id=str(content.id))
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("api_get_generated_content_by_hash_failed",
                    content_hash=content_hash, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving generated content"
        )


@router.post(
    "/",
    response_model=GeneratedContentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Invalid request data"},
        500: {"description": "Internal server error"}
    }
)
async def create_new_generated_content(request: GeneratedContentCreateRequest):
    """Create new generated content.

    Args:
        request: GeneratedContentCreateRequest with content data

    Returns:
        GeneratedContentResponse object with the created content details
    """
    logger.info("api_create_generated_content", request_data=request.dict())

    try:
        content_data = request.dict(exclude_none=True)

        # Convert list fields for database relationships
        if 'source_document_ids' in content_data:
            # This will be handled by the ORM relationship
            del content_data['source_document_ids']
        if 'source_content_ids' in content_data:
            # This will be handled by the ORM relationship
            del content_data['source_content_ids']

        content = create_generated_content(content_data)

        # Handle source relationships if provided
        if request.source_document_ids:
            # Add logic to associate source documents
            pass
        if request.source_content_ids:
            # Add logic to associate source content
            pass

        content_dict = content.to_dict()
        response = GeneratedContentResponse(**content_dict)

        logger.info("api_create_generated_content_success", content_id=str(content.id))
        return response

    except Exception as e:
        logger.error("api_create_generated_content_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while creating generated content"
        )


@router.get(
    "/{content_id}/sources",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Generated content not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_generated_content_sources(content_id: UUID):
    """Get all sources (documents and other content) for a generated content.

    Args:
        content_id: UUID of the generated content

    Returns:
        Dictionary with source documents and source content lists
    """
    logger.info("api_get_generated_content_sources", content_id=str(content_id))

    try:
        content = get_generated_content(content_id)

        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Generated content not found with ID: {content_id}"
            )

        sources = {
            "source_documents": [
                {
                    "id": str(doc.id),
                    "name": doc.document_name,
                    "type": "document"
                } for doc in content.source_documents
            ],
            "source_content": [
                {
                    "id": str(source.id),
                    "short_hash": source.get_short_hash(),
                    "document_type": source.document_type.value if source.document_type else None,
                    "type": "generated_content"
                } for source in content.source_content
            ]
        }

        logger.info("api_get_generated_content_sources_success",
                   content_id=str(content_id),
                   source_docs=len(sources["source_documents"]),
                   source_content=len(sources["source_content"]))
        return sources

    except HTTPException:
        raise
    except Exception as e:
        logger.error("api_get_generated_content_sources_failed",
                    content_id=str(content_id), error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving content sources"
        )
