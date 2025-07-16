"""API routes for aggregates."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from src.api.schemas import AggregateResponse, CompletionResponse
from src.database.aggregates import get_aggregate, get_recent_aggregates_by_ticker
from src.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get(
    "/by-ticker/{ticker}",
    response_model=List[AggregateResponse],
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Company not found or has no aggregates"},
        500: {"description": "Internal server error"}
    }
)
async def get_company_aggregates_by_ticker(ticker: str):
    """Get the most recent aggregates for each document type associated with a company by ticker.

    Returns only the most recent aggregate for each document type (MDA, RISK_FACTORS, DESCRIPTION)
    to avoid duplicate entries and ensure you get the latest AI-generated insights.

    Args:
        ticker: Company ticker symbol (e.g., 'AAPL', 'GOOGL')

    Returns:
        List of AggregateResponse objects - the most recent aggregate for each document type
    """
    logger.info("api_get_company_aggregates_by_ticker", ticker=ticker)

    try:
        aggregates = get_recent_aggregates_by_ticker(ticker)

        if not aggregates:
            raise HTTPException(
                status_code=404,
                detail=f"No aggregates found for company with ticker {ticker}"
            )

        # Convert database models to response schemas
        response_data = []
        for aggregate in aggregates:
            response_data.append(AggregateResponse(
                id=aggregate.id,
                company_id=aggregate.company_id,
                document_type=aggregate.document_type.value if aggregate.document_type else None,
                created_at=aggregate.created_at,
                total_duration=aggregate.total_duration,
                content=aggregate.content,
                summary=aggregate.summary,
                model=aggregate.model,
                temperature=aggregate.temperature,
                top_p=aggregate.top_p,
                num_ctx=aggregate.num_ctx,
                system_prompt_id=aggregate.system_prompt_id
            ))

        logger.info(
            "api_get_company_aggregates_by_ticker_success",
            ticker=ticker,
            count=len(response_data),
            document_types=[item.document_type for item in response_data]
        )

        return response_data

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "api_get_company_aggregates_by_ticker_failed",
            ticker=ticker,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error while retrieving aggregates for {ticker}"
        ) from e


@router.get(
    "/{aggregate_id}/completions",
    response_model=List[CompletionResponse],
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Aggregate not found or has no source completions"},
        500: {"description": "Internal server error"}
    }
)
async def get_aggregate_source_completions(aggregate_id: UUID):
    """Get all completions that were used as sources to create this aggregate.

    This endpoint allows the UI to show the "Links to Source Completions"
    from the Aggregate Overview page.

    Args:
        aggregate_id: UUID of the aggregate

    Returns:
        List of CompletionResponse objects that were used to create the aggregate
    """
    logger.info("api_get_aggregate_source_completions", aggregate_id=str(aggregate_id))

    try:
        # First get the aggregate to check if it exists
        aggregate = get_aggregate(aggregate_id)
        if not aggregate:
            raise HTTPException(
                status_code=404,
                detail=f"Aggregate with ID {aggregate_id} not found"
            )

        # Get the source completions from the aggregate relationship
        source_completions = aggregate.source_completions

        if not source_completions:
            raise HTTPException(
                status_code=404,
                detail=f"No source completions found for aggregate {aggregate_id}"
            )

        # Convert to response format
        response_data = []
        for completion in source_completions:
            source_document_ids = [doc.id for doc in completion.source_documents]

            response_data.append(CompletionResponse(
                id=completion.id,
                system_prompt_id=completion.system_prompt_id,
                model=completion.model,
                temperature=completion.temperature,
                top_p=completion.top_p,
                num_ctx=completion.num_ctx,
                source_documents=source_document_ids,
                created_at=completion.created_at,
                total_duration=completion.total_duration,
                content=completion.content
            ))

        logger.info(
            "api_get_aggregate_source_completions_success",
            aggregate_id=str(aggregate_id),
            completion_count=len(response_data)
        )

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "api_get_aggregate_source_completions_failed",
            aggregate_id=str(aggregate_id),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error while retrieving source completions for aggregate {aggregate_id}"
        ) from e