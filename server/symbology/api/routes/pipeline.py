"""Pipeline monitoring API routes."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from symbology.api.schemas import (
    CompanyPipelineStatus,
    PipelineRunResponse,
    PipelineStatusResponse,
    PipelineTriggerRequest,
)
from symbology.database.companies import Company, get_company, get_company_by_ticker
from symbology.database.jobs import JobType, create_job
from symbology.database.pipeline_runs import (
    PipelineRun,
    PipelineRunStatus,
    PipelineTrigger,
    count_consecutive_failures,
    get_latest_run_per_company,
    get_pipeline_run,
    list_pipeline_runs,
)
from symbology.scheduler.config import scheduler_settings
from symbology.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


def _run_to_response(run: PipelineRun) -> PipelineRunResponse:
    """Convert a PipelineRun model to PipelineRunResponse."""
    return PipelineRunResponse(
        id=run.id,
        company_id=run.company_id,
        trigger=run.trigger.value,
        status=run.status.value,
        forms=run.forms,
        started_at=run.started_at,
        completed_at=run.completed_at,
        error=run.error,
        jobs_created=run.jobs_created,
        jobs_completed=run.jobs_completed,
        jobs_failed=run.jobs_failed,
        run_metadata=run.run_metadata,
    )


@router.get(
    "/runs",
    response_model=List[PipelineRunResponse],
    status_code=status.HTTP_200_OK,
)
async def list_runs(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List pipeline runs with optional filters."""
    ps = None
    if status_filter:
        try:
            ps = PipelineRunStatus(status_filter)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")

    runs = list_pipeline_runs(company_id=company_id, status=ps, limit=limit, offset=offset)
    logger.info("api_list_pipeline_runs", count=len(runs), status=status_filter)
    return [_run_to_response(r) for r in runs]


@router.get(
    "/runs/{run_id}",
    response_model=PipelineRunResponse,
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Pipeline run not found"}},
)
async def get_run(run_id: UUID):
    """Get a single pipeline run by ID."""
    logger.info("api_get_pipeline_run", run_id=str(run_id))
    run = get_pipeline_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return _run_to_response(run)


@router.get(
    "/status",
    response_model=PipelineStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def pipeline_status_dashboard():
    """Dashboard showing latest pipeline run per company with failure counts."""
    from datetime import datetime, timedelta, timezone

    latest_runs = get_latest_run_per_company()

    # Build per-company status
    companies: list[CompanyPipelineStatus] = []
    companies_with_failures = 0
    stale_count = 0
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=7200)

    for run in latest_runs:
        failures = count_consecutive_failures(run.company_id)
        company = get_company(run.company_id)
        ticker = company.ticker if company else None
        company_name = company.name if company else None

        if failures > 0:
            companies_with_failures += 1

        if run.status == PipelineRunStatus.RUNNING and run.started_at and run.started_at < cutoff:
            stale_count += 1

        companies.append(CompanyPipelineStatus(
            company_id=run.company_id,
            ticker=ticker,
            company_name=company_name,
            last_run_id=run.id,
            last_run_status=run.status.value,
            last_run_at=run.started_at,
            consecutive_failures=failures,
        ))

    logger.info(
        "api_pipeline_status",
        total_companies=len(companies),
        companies_with_failures=companies_with_failures,
        stale_runs=stale_count,
    )

    return PipelineStatusResponse(
        total_companies=len(companies),
        companies_with_failures=companies_with_failures,
        stale_runs=stale_count,
        next_poll_seconds=scheduler_settings.poll_interval,
        companies=companies,
    )


@router.post(
    "/trigger/{ticker}",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"description": "Company not found"}},
)
async def trigger_pipeline(ticker: str, request: Optional[PipelineTriggerRequest] = None):
    """Manually trigger a pipeline run for a company."""
    company = get_company_by_ticker(ticker.upper())
    if not company:
        raise HTTPException(status_code=404, detail=f"Company not found: {ticker}")

    forms = (request.forms if request and request.forms else scheduler_settings.enabled_forms)

    job = create_job(
        job_type=JobType.FULL_PIPELINE,
        params={"ticker": company.ticker, "forms": forms},
        priority=1,
    )

    logger.info(
        "api_trigger_pipeline",
        ticker=company.ticker,
        forms=forms,
        job_id=str(job.id),
    )

    return {"job_id": str(job.id), "ticker": company.ticker, "forms": forms}
