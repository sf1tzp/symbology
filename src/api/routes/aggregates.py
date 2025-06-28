"""API routes for aggregates."""
from typing import List

from fastapi import APIRouter, HTTPException, status

from src.api.schemas import AggregateResponse
from src.database.aggregates import get_recent_aggregates_by_ticker
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