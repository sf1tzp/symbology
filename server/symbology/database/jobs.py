"""Database models and CRUD functions for background job queue."""
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy import DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column
from symbology.database.base import Base, get_db_session
from symbology.utils.logging import get_logger
from uuid_extensions import uuid7

logger = get_logger(__name__)


class JobStatus(str, Enum):
    """Job lifecycle states."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Registered job types."""
    COMPANY_INGESTION = "company_ingestion"
    FILING_INGESTION = "filing_ingestion"
    CONTENT_GENERATION = "content_generation"
    INGEST_PIPELINE = "ingest_pipeline"
    FULL_PIPELINE = "full_pipeline"
    BULK_INGEST = "bulk_ingest"
    COMPANY_GROUP_PIPELINE = "company_group_pipeline"
    TEST = "test"


class Job(Base):
    """Background job queue entry."""

    __tablename__ = "jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

    # Job definition
    job_type: Mapped[JobType] = mapped_column(
        SQLEnum(JobType, name="job_type_enum"),
        nullable=False,
    )
    params: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)
    priority: Mapped[int] = mapped_column(Integer, default=2)  # lower = higher priority

    # Lifecycle
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus, name="job_status_enum"),
        nullable=False,
        default=JobStatus.PENDING,
    )
    worker_id: Mapped[Optional[str]] = mapped_column(String(255))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Retry
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

    # Result / error
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    error: Mapped[Optional[str]] = mapped_column(Text)

    # Timing
    duration: Mapped[Optional[float]] = mapped_column(Float)

    __table_args__ = (
        Index("ix_jobs_queue_poll", "status", "priority", "created_at"),
        Index("ix_jobs_stale_detection", "status", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, type={self.job_type.value}, status={self.status.value})>"


# ---------------------------------------------------------------------------
# CRUD functions
# ---------------------------------------------------------------------------

def create_job(
    job_type: JobType,
    params: Optional[Dict[str, Any]] = None,
    priority: int = 2,
    max_retries: int = 3,
) -> Job:
    """Create a new job and persist it."""
    try:
        session = get_db_session()
        job = Job(
            job_type=job_type,
            params=params or {},
            priority=priority,
            max_retries=max_retries,
        )
        session.add(job)
        session.commit()
        logger.info("created_job", job_id=str(job.id), job_type=job_type.value, priority=priority)
        return job
    except Exception as e:
        session.rollback()
        logger.error("create_job_failed", error=str(e), exc_info=True)
        raise


def get_job(job_id: Union[UUID, str]) -> Optional[Job]:
    """Get a job by ID."""
    try:
        session = get_db_session()
        job = session.query(Job).filter(Job.id == job_id).first()
        if job:
            logger.debug("retrieved_job", job_id=str(job_id))
        else:
            logger.warning("job_not_found", job_id=str(job_id))
        return job
    except Exception as e:
        logger.error("get_job_failed", job_id=str(job_id), error=str(e), exc_info=True)
        raise


def list_jobs(
    status: Optional[JobStatus] = None,
    job_type: Optional[JobType] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Job]:
    """List jobs with optional filters."""
    try:
        session = get_db_session()
        query = session.query(Job)
        if status:
            query = query.filter(Job.status == status)
        if job_type:
            query = query.filter(Job.job_type == job_type)
        query = query.order_by(Job.created_at.desc())
        jobs = query.offset(offset).limit(limit).all()
        logger.debug("listed_jobs", count=len(jobs), status=status, job_type=job_type)
        return jobs
    except Exception as e:
        logger.error("list_jobs_failed", error=str(e), exc_info=True)
        raise


def cancel_job(job_id: Union[UUID, str]) -> Optional[Job]:
    """Cancel a pending job. Returns None if not found or not cancellable."""
    try:
        session = get_db_session()
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.warning("cancel_job_not_found", job_id=str(job_id))
            return None
        if job.status != JobStatus.PENDING:
            logger.warning("cancel_job_not_pending", job_id=str(job_id), status=job.status.value)
            return None
        job.status = JobStatus.CANCELLED
        session.commit()
        logger.info("cancelled_job", job_id=str(job_id))
        return job
    except Exception as e:
        session.rollback()
        logger.error("cancel_job_failed", job_id=str(job_id), error=str(e), exc_info=True)
        raise


def claim_next_job(worker_id: str) -> Optional[Job]:
    """Atomically claim the highest-priority pending job using SELECT FOR UPDATE SKIP LOCKED."""
    try:
        session = get_db_session()
        job = (
            session.query(Job)
            .filter(Job.status == JobStatus.PENDING)
            .order_by(Job.priority, Job.created_at)
            .with_for_update(skip_locked=True)
            .first()
        )
        if not job:
            return None
        job.status = JobStatus.IN_PROGRESS
        job.worker_id = worker_id
        job.started_at = func.now()
        session.commit()
        logger.info("claimed_job", job_id=str(job.id), worker_id=worker_id, job_type=job.job_type.value)
        return job
    except Exception as e:
        session.rollback()
        logger.error("claim_next_job_failed", worker_id=worker_id, error=str(e), exc_info=True)
        raise


def complete_job(job_id: Union[UUID, str], result: Optional[Dict[str, Any]] = None) -> Optional[Job]:
    """Mark a job as completed."""
    try:
        session = get_db_session()
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.warning("complete_job_not_found", job_id=str(job_id))
            return None
        job.status = JobStatus.COMPLETED
        job.result = result
        job.completed_at = func.now()
        if job.started_at:
            # started_at is naive UTC from the database; use naive UTC for arithmetic
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            job.duration = (now - job.started_at).total_seconds()
        session.commit()
        logger.info("completed_job", job_id=str(job.id), job_type=job.job_type.value)
        return job
    except Exception as e:
        session.rollback()
        logger.error("complete_job_failed", job_id=str(job_id), error=str(e), exc_info=True)
        raise


def fail_job(job_id: Union[UUID, str], error: str) -> Optional[Job]:
    """Mark a job as failed. Re-queues if retries remain."""
    try:
        session = get_db_session()
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.warning("fail_job_not_found", job_id=str(job_id))
            return None
        job.error = error
        job.retry_count += 1
        if job.retry_count < job.max_retries:
            job.status = JobStatus.PENDING
            job.worker_id = None
            job.started_at = None
            logger.info("requeued_job", job_id=str(job.id), retry_count=job.retry_count, max_retries=job.max_retries)
        else:
            job.status = JobStatus.FAILED
            job.completed_at = func.now()
            logger.warning("job_exhausted_retries", job_id=str(job.id), retry_count=job.retry_count)
        session.commit()
        return job
    except Exception as e:
        session.rollback()
        logger.error("fail_job_failed", job_id=str(job_id), error=str(e), exc_info=True)
        raise


def mark_stale_jobs_as_failed(stale_threshold_seconds: int = 600) -> List[Job]:
    """Find IN_PROGRESS jobs not updated within the threshold and mark them failed."""
    try:
        session = get_db_session()
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=stale_threshold_seconds)
        stale_jobs = (
            session.query(Job)
            .filter(Job.status == JobStatus.IN_PROGRESS)
            .filter(Job.updated_at < cutoff)
            .all()
        )
        for job in stale_jobs:
            job.error = f"Stale: no update for {stale_threshold_seconds}s"
            job.retry_count += 1
            if job.retry_count < job.max_retries:
                job.status = JobStatus.PENDING
                job.worker_id = None
                job.started_at = None
                logger.info("requeued_stale_job", job_id=str(job.id), retry_count=job.retry_count)
            else:
                job.status = JobStatus.FAILED
                job.completed_at = func.now()
                logger.warning("stale_job_exhausted_retries", job_id=str(job.id))
        if stale_jobs:
            session.commit()
            logger.info("marked_stale_jobs", count=len(stale_jobs))
        return stale_jobs
    except Exception as e:
        session.rollback()
        logger.error("mark_stale_jobs_failed", error=str(e), exc_info=True)
        raise
