"""Database models and CRUD functions for pipeline run tracking."""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSON
from sqlalchemy.orm import Mapped, mapped_column
from symbology.database.base import Base, get_db_session
from symbology.utils.logging import get_logger
from uuid_extensions import uuid7

logger = get_logger(__name__)


class PipelineTrigger(str, Enum):
    """How the pipeline run was initiated."""
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class PipelineRunStatus(str, Enum):
    """Pipeline run lifecycle states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class PipelineRun(Base):
    """Tracks an end-to-end pipeline execution."""

    __tablename__ = "pipeline_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

    # Which company this run is for
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True,
    )

    # How it was triggered
    trigger: Mapped[PipelineTrigger] = mapped_column(
        SQLEnum(PipelineTrigger, name="pipeline_trigger_enum"),
        nullable=False,
        default=PipelineTrigger.MANUAL,
    )

    # Lifecycle
    status: Mapped[PipelineRunStatus] = mapped_column(
        SQLEnum(PipelineRunStatus, name="pipeline_run_status_enum"),
        nullable=False,
        default=PipelineRunStatus.PENDING,
    )

    # Which forms were requested
    forms: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Error info
    error: Mapped[Optional[str]] = mapped_column(Text)

    # Job counters
    jobs_created: Mapped[int] = mapped_column(Integer, default=0)
    jobs_completed: Mapped[int] = mapped_column(Integer, default=0)
    jobs_failed: Mapped[int] = mapped_column(Integer, default=0)

    # Arbitrary metadata
    run_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata", JSON, default=dict,
    )

    __table_args__ = (
        Index("ix_pipeline_runs_company_status", "company_id", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<PipelineRun(id={self.id}, company_id={self.company_id}, "
            f"status={self.status.value})>"
        )


# ---------------------------------------------------------------------------
# CRUD functions
# ---------------------------------------------------------------------------

def create_pipeline_run(
    company_id: Union[UUID, str],
    forms: List[str],
    trigger: PipelineTrigger = PipelineTrigger.MANUAL,
    run_metadata: Optional[Dict[str, Any]] = None,
) -> PipelineRun:
    """Create a new pipeline run record."""
    try:
        session = get_db_session()
        run = PipelineRun(
            company_id=company_id if isinstance(company_id, UUID) else UUID(company_id),
            forms=forms,
            trigger=trigger,
            status=PipelineRunStatus.PENDING,
            run_metadata=run_metadata or {},
        )
        session.add(run)
        session.commit()
        logger.info(
            "created_pipeline_run",
            run_id=str(run.id),
            company_id=str(company_id),
            forms=forms,
        )
        return run
    except Exception as e:
        session.rollback()
        logger.error("create_pipeline_run_failed", error=str(e), exc_info=True)
        raise


def get_pipeline_run(run_id: Union[UUID, str]) -> Optional[PipelineRun]:
    """Get a pipeline run by ID."""
    try:
        session = get_db_session()
        run = session.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        if run:
            logger.debug("retrieved_pipeline_run", run_id=str(run_id))
        else:
            logger.warning("pipeline_run_not_found", run_id=str(run_id))
        return run
    except Exception as e:
        logger.error("get_pipeline_run_failed", run_id=str(run_id), error=str(e), exc_info=True)
        raise


def list_pipeline_runs(
    company_id: Optional[Union[UUID, str]] = None,
    status: Optional[PipelineRunStatus] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[PipelineRun]:
    """List pipeline runs with optional filters."""
    try:
        session = get_db_session()
        query = session.query(PipelineRun)
        if company_id:
            query = query.filter(PipelineRun.company_id == company_id)
        if status:
            query = query.filter(PipelineRun.status == status)
        query = query.order_by(PipelineRun.started_at.desc().nullslast())
        runs = query.offset(offset).limit(limit).all()
        logger.debug("listed_pipeline_runs", count=len(runs))
        return runs
    except Exception as e:
        logger.error("list_pipeline_runs_failed", error=str(e), exc_info=True)
        raise


def start_pipeline_run(run_id: Union[UUID, str]) -> Optional[PipelineRun]:
    """Mark a pipeline run as running."""
    try:
        session = get_db_session()
        run = session.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        if not run:
            return None
        run.status = PipelineRunStatus.RUNNING
        run.started_at = func.now()
        session.commit()
        logger.info("started_pipeline_run", run_id=str(run_id))
        return run
    except Exception as e:
        session.rollback()
        logger.error("start_pipeline_run_failed", run_id=str(run_id), error=str(e), exc_info=True)
        raise


def complete_pipeline_run(
    run_id: Union[UUID, str],
    jobs_created: int = 0,
    jobs_completed: int = 0,
    jobs_failed: int = 0,
) -> Optional[PipelineRun]:
    """Mark a pipeline run as completed or partial (if any jobs failed)."""
    try:
        session = get_db_session()
        run = session.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        if not run:
            return None
        run.jobs_created = jobs_created
        run.jobs_completed = jobs_completed
        run.jobs_failed = jobs_failed
        run.completed_at = func.now()
        run.status = PipelineRunStatus.PARTIAL if jobs_failed > 0 else PipelineRunStatus.COMPLETED
        session.commit()
        logger.info(
            "completed_pipeline_run",
            run_id=str(run_id),
            status=run.status.value,
            jobs_created=jobs_created,
            jobs_completed=jobs_completed,
            jobs_failed=jobs_failed,
        )
        return run
    except Exception as e:
        session.rollback()
        logger.error("complete_pipeline_run_failed", run_id=str(run_id), error=str(e), exc_info=True)
        raise


def get_latest_run_per_company() -> List[PipelineRun]:
    """Get the most recent pipeline run for each company.

    Uses DISTINCT ON (company_id) ordered by started_at DESC.
    """
    try:
        session = get_db_session()
        from sqlalchemy import text
        # Use raw SQL for DISTINCT ON which is PostgreSQL-specific
        stmt = text(
            "SELECT DISTINCT ON (company_id) * FROM pipeline_runs "
            "ORDER BY company_id, started_at DESC NULLS LAST"
        )
        runs = session.query(PipelineRun).from_statement(stmt).all()
        logger.debug("get_latest_run_per_company", count=len(runs))
        return runs
    except Exception as e:
        logger.error("get_latest_run_per_company_failed", error=str(e), exc_info=True)
        raise


def count_consecutive_failures(company_id: Union[UUID, str], limit: int = 10) -> int:
    """Count leading consecutive FAILED/PARTIAL runs for a company.

    Looks at the most recent `limit` runs ordered by started_at DESC and
    counts how many leading runs are FAILED or PARTIAL.
    """
    runs = list_pipeline_runs(company_id=company_id, limit=limit)
    count = 0
    for run in runs:
        if run.status in (PipelineRunStatus.FAILED, PipelineRunStatus.PARTIAL):
            count += 1
        else:
            break
    return count


def fail_pipeline_run(
    run_id: Union[UUID, str],
    error: str,
    jobs_created: int = 0,
    jobs_completed: int = 0,
    jobs_failed: int = 0,
) -> Optional[PipelineRun]:
    """Mark a pipeline run as failed."""
    try:
        session = get_db_session()
        run = session.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        if not run:
            return None
        run.status = PipelineRunStatus.FAILED
        run.error = error
        run.completed_at = func.now()
        run.jobs_created = jobs_created
        run.jobs_completed = jobs_completed
        run.jobs_failed = jobs_failed
        session.commit()
        logger.warning("failed_pipeline_run", run_id=str(run_id), error=error)
        return run
    except Exception as e:
        session.rollback()
        logger.error("fail_pipeline_run_failed", run_id=str(run_id), error=str(e), exc_info=True)
        raise
