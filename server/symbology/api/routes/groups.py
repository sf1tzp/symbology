"""Company Groups API routes."""
from typing import List

from fastapi import APIRouter, HTTPException, Query, status
from symbology.api.routes.companies import _company_to_response
from symbology.api.schemas import CompanyGroupResponse, GeneratedContentResponse
from symbology.database.company_groups import (
    CompanyGroup,
    get_company_group_by_slug,
    list_company_groups,
)
from symbology.database.generated_content import get_company_group_analysis
from symbology.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


def _group_to_response(group: CompanyGroup, include_companies: bool = False) -> CompanyGroupResponse:
    """Convert a CompanyGroup model to CompanyGroupResponse."""
    companies = None
    if include_companies:
        companies = [_company_to_response(c) for c in group.companies]

    # Get latest analysis summary
    latest_summary = None
    try:
        analyses = get_company_group_analysis(group.id, limit=1)
        if analyses and analyses[0].content:
            latest_summary = analyses[0].content[:500]
    except Exception as e:
        logger.warning("failed_to_get_latest_analysis", slug=group.slug, error=str(e))

    return CompanyGroupResponse(
        id=group.id,
        name=group.name,
        slug=group.slug,
        description=group.description,
        sic_codes=group.sic_codes or [],
        member_count=len(group.companies),
        created_at=group.created_at,
        updated_at=group.updated_at,
        companies=companies,
        latest_analysis_summary=latest_summary,
    )


@router.get(
    "",
    response_model=List[CompanyGroupResponse],
    status_code=status.HTTP_200_OK,
    responses={
        500: {"description": "Internal server error"},
    },
)
async def list_groups(
    skip: int = Query(0, ge=0, description="Number of groups to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of groups to return"),
):
    """List all company groups."""
    logger.info("api_list_groups", skip=skip, limit=limit)

    groups = list_company_groups(limit=limit, offset=skip)
    return [_group_to_response(g) for g in groups]


@router.get(
    "/{slug}",
    response_model=CompanyGroupResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Group not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_group_detail(slug: str):
    """Get group detail including member companies."""
    logger.info("api_get_group_detail", slug=slug)

    group = get_company_group_by_slug(slug)
    if not group:
        raise HTTPException(status_code=404, detail=f"Group not found: {slug}")

    return _group_to_response(group, include_companies=True)


@router.get(
    "/{slug}/analysis",
    response_model=List[GeneratedContentResponse],
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Group not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_group_analysis(
    slug: str,
    limit: int = Query(5, ge=1, le=20, description="Maximum analyses to return"),
):
    """Get analyses for a company group."""
    logger.info("api_get_group_analysis", slug=slug, limit=limit)

    group = get_company_group_by_slug(slug)
    if not group:
        raise HTTPException(status_code=404, detail=f"Group not found: {slug}")

    analyses = get_company_group_analysis(group.id, limit=limit)

    return [
        GeneratedContentResponse(
            id=a.id,
            content_hash=a.content_hash,
            short_hash=a.get_short_hash(),
            company_id=a.company_id,
            company_group_id=a.company_group_id,
            description=a.description,
            document_type=a.description,
            source_type=a.source_type.value,
            created_at=a.created_at,
            total_duration=a.total_duration,
            input_tokens=a.input_tokens,
            output_tokens=a.output_tokens,
            warning=a.warning,
            content=a.content,
            summary=a.summary,
            model_config_id=a.model_config_id,
            system_prompt_id=a.system_prompt_id,
            user_prompt_id=a.user_prompt_id,
            source_document_ids=[str(d.id) for d in a.source_documents],
            source_content_ids=[str(c.id) for c in a.source_content],
        )
        for a in analyses
    ]
