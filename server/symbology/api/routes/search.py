"""Search API routes."""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from symbology.api.schemas import SearchResponse, SearchResultItem
from symbology.database.search import unified_search
from symbology.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get(
    "",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Bad request"},
        500: {"description": "Internal server error"},
    },
)
async def search(
    q: str = Query(..., min_length=1, description="Search query string"),
    entity_types: Optional[List[str]] = Query(
        None, description="Entity types to search: company, filing, generated_content"
    ),
    sic: Optional[str] = Query(None, description="Filter by SIC code"),
    form_type: Optional[str] = Query(None, description="Filter by SEC form type (10-K, 10-Q)"),
    document_type: Optional[str] = Query(
        None, description="Filter by document type (MDA, RISK_FACTORS, etc.)"
    ),
    date_from: Optional[date] = Query(None, description="Filter results from this date"),
    date_to: Optional[date] = Query(None, description="Filter results up to this date"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """Unified full-text search across companies, filings, and generated content.

    Supports full-text search with relevance ranking, filtering by entity type,
    SIC code, form type, document type, and date range.
    """
    logger.info(
        "api_unified_search",
        query=q,
        entity_types=entity_types,
        limit=limit,
        offset=offset,
    )

    # Validate entity_types if provided
    valid_types = {"company", "filing", "generated_content", "company_group"}
    if entity_types:
        invalid = set(entity_types) - valid_types
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid entity types: {invalid}. Valid types: {valid_types}",
            )

    try:
        result = unified_search(
            query=q,
            entity_types=entity_types,
            sic=sic,
            form_type=form_type,
            document_type=document_type,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )

        return SearchResponse(
            results=[SearchResultItem(**item) for item in result["results"]],
            total=result["total"],
            query=q,
        )

    except Exception as e:
        logger.error("api_unified_search_failed", query=q, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while performing search",
        ) from e
