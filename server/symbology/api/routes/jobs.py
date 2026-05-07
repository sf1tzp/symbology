"""Jobs API routes."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from symbology.api.schemas import JobCreateRequest, JobResponse
from symbology.database.jobs import (
    Job,
    JobStatus,
    JobType,
    cancel_job,
    create_job,
    get_job,
    list_jobs,
)
from symbology.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


def _job_to_response(job: Job) -> JobResponse:
    """Convert a Job model to JobResponse."""
    return JobResponse(
        id=job.id,
        job_type=job.job_type.value,
        params=job.params,
        priority=job.priority,
        status=job.status.value,
        worker_id=job.worker_id,
        created_at=job.created_at,
        updated_at=job.updated_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        retry_count=job.retry_count,
        max_retries=job.max_retries,
        result=job.result,
        error=job.error,
        duration=job.duration,
    )


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Invalid job type or parameters"},
    },
)
async def enqueue_job(request: JobCreateRequest):
    """Submit a new job to the queue."""
    try:
        jt = JobType(request.job_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid job_type: {request.job_type}")

    logger.info("api_enqueue_job", job_type=request.job_type, priority=request.priority)
    job = create_job(
        job_type=jt,
        params=request.params,
        priority=request.priority,
        max_retries=request.max_retries,
    )
    return _job_to_response(job)


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Job not found"}},
)
async def get_job_by_id(job_id: UUID):
    """Get a job by its ID."""
    logger.info("api_get_job", job_id=str(job_id))
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)


@router.get(
    "",
    response_model=List[JobResponse],
    status_code=status.HTTP_200_OK,
)
async def list_jobs_route(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List jobs with optional filters."""
    js = None
    jt = None
    if status_filter:
        try:
            js = JobStatus(status_filter)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")
    if job_type:
        try:
            jt = JobType(job_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid job_type: {job_type}")

    logger.info("api_list_jobs", status=status_filter, job_type=job_type, limit=limit, offset=offset)
    jobs = list_jobs(status=js, job_type=jt, limit=limit, offset=offset)
    return [_job_to_response(j) for j in jobs]


@router.delete(
    "/{job_id}",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Job not found or not cancellable"},
    },
)
async def cancel_job_route(job_id: UUID):
    """Cancel a pending job."""
    logger.info("api_cancel_job", job_id=str(job_id))
    job = cancel_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not in PENDING status")
    return _job_to_response(job)
