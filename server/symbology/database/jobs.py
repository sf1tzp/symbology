"""Database models and CRUD functions for background job queue."""
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union
from uuid import UUID

from sqlalchemy import DateTime, Float, Index, Integer, String, Text, cast, func, or_, text
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
    # Waiting on an unmet dependency (e.g. source filing pages still generating).
    # Distinct from a failure: it consumes no retry budget, polls until the dep
    # lands (re-claimed when `scheduled_at` arrives), and has no give-up ceiling.
    BACKOFF = "backoff"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Registered job types."""
    COMPANY_INGESTION = "company_ingestion"
    FILING_INGESTION = "filing_ingestion"
    CONTENT_GENERATION = "content_generation"
    BULK_INGEST = "bulk_ingest"
    COMPANY_GROUP_PIPELINE = "company_group_pipeline"
    FILING_PAGE_CONTENT = "filing_page_content"
    COMPANY_PAGE_CONTENT = "company_page_content"
    EMBED_FILING = "embed_filing"
    BACKFILL_CHUNKS = "backfill_chunks"
    BACKFILL_EMBEDDINGS = "backfill_embeddings"
    FILING_DIFF = "filing_diff"
    DIFF_SUMMARY = "diff_summary"
    TEST = "test"


class JobPriority:
    """Queue priority bands (lower = claimed sooner).

    The guiding rule: fast/required pipeline jobs (ingestion, chunk+embed, diff)
    outrank generated-content stages, so the data feedstock is always ready before
    the prose that cites it. The bands are deliberately coarse so there's an
    unambiguous home for each job type.

    These are only the *starting* priorities. ``claim_next_job`` decays a job's
    effective priority with age (see ``WorkerSettings.priority_aging_interval``),
    so a content job that's been waiting long enough still overtakes a steady
    drip of fresh ingestion rather than starving.
    """

    # A backed-off job is actively blocked on this one — jump the whole queue so
    # the waiting chain unblocks fast (filing pages / ingestion / embeddings a
    # page or diff is parked on).
    DEP_UNBLOCK = 0
    # Fast, required feedstock that everything else builds on: filing ingestion,
    # chunk+embed, and the backfills.
    INGEST = 1
    # Structural filing diffs — required derived data, depends on embeddings.
    DIFF = 2
    # Generated page content (company/filing) and raw content generation.
    PAGE = 3
    # Multi-company group pipelines.
    GROUP = 4
    # Diff prose summaries — deepest, least urgent generated content.
    SUMMARY = 5


class Job(Base):
    """Background job queue entry."""

    __tablename__ = "jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

    # Job definition
    job_type: Mapped[JobType] = mapped_column(
        SQLEnum(JobType, name="job_type_enum", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    params: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)
    priority: Mapped[int] = mapped_column(Integer, default=2)  # lower = higher priority

    # Lifecycle
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus, name="job_status_enum", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=JobStatus.PENDING,
    )
    worker_id: Mapped[Optional[str]] = mapped_column(String(255))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Earliest time this job may be claimed (naive UTC). NULL = eligible
    # immediately. Lets a job defer itself — e.g. a company page waiting on
    # in-flight filing page content — without busy-looping through the retry
    # machinery (which retries immediately and burns max_retries).
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Retry (genuine errors only)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

    # Dependency-wait backoff. Counts how many times the job has re-deferred
    # itself waiting on an unmet dependency; drives the exponential backoff
    # delay. Separate from retry_count so a benign wait never looks like a crash.
    backoff_count: Mapped[int] = mapped_column(Integer, default=0)

    # Result / error
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    error: Mapped[Optional[str]] = mapped_column(Text)

    # Timing
    duration: Mapped[Optional[float]] = mapped_column(Float)

    __table_args__ = (
        Index("ix_jobs_queue_poll", "status", "priority", "created_at"),
        Index("ix_jobs_stale_detection", "status", "updated_at"),
        Index("ix_jobs_scheduled", "status", "scheduled_at"),
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
    scheduled_at: Optional[datetime] = None,
) -> Job:
    """Create a new job and persist it.

    ``scheduled_at`` (naive UTC) defers the job: it won't be claimed until then.
    Leave it None to make the job eligible immediately.
    """
    try:
        session = get_db_session()
        job = Job(
            job_type=job_type,
            params=params or {},
            priority=priority,
            max_retries=max_retries,
            scheduled_at=scheduled_at,
        )
        session.add(job)
        session.commit()
        logger.info("created_job", job_id=str(job.id), job_type=job_type.value,
                    priority=priority, scheduled_at=scheduled_at.isoformat() if scheduled_at else None)
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
    status: Optional[Union[JobStatus, Sequence[JobStatus]]] = None,
    job_type: Optional[JobType] = None,
    ticker: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Job]:
    """List jobs with optional filters.

    ``status`` may be a single ``JobStatus`` or a sequence of them, in which
    case jobs matching any of the given statuses are returned.

    ``ticker`` filters to jobs whose params reference a company by ticker. The
    key varies by job type (``ticker``, ``company_ticker``, or a ``tickers``
    list), so all are checked, case-insensitively.
    """
    try:
        session = get_db_session()
        query = session.query(Job)
        if status:
            statuses = [status] if isinstance(status, JobStatus) else list(status)
            query = query.filter(Job.status.in_(statuses))
        if job_type:
            query = query.filter(Job.job_type == job_type)
        if ticker:
            t = ticker.upper()
            query = query.filter(
                or_(
                    func.upper(Job.params["ticker"].astext) == t,
                    func.upper(Job.params["company_ticker"].astext) == t,
                    # tickers is a JSON array; match the quoted element in its text form.
                    func.upper(cast(Job.params["tickers"], String)).like(f'%"{t}"%'),
                )
            )
        query = query.order_by(Job.created_at.desc())
        jobs = query.offset(offset).limit(limit).all()
        logger.debug("listed_jobs", count=len(jobs), status=status, job_type=job_type)
        return jobs
    except Exception as e:
        logger.error("list_jobs_failed", error=str(e), exc_info=True)
        raise


def get_active_jobs(job_type: JobType) -> List[Job]:
    """Return jobs of a type that are still in flight (PENDING or IN_PROGRESS).

    Used to tell whether work for a dependency is already queued/running before
    enqueuing a duplicate (e.g. filing page content a company page is waiting on).
    """
    try:
        session = get_db_session()
        return (
            session.query(Job)
            .filter(Job.job_type == job_type)
            .filter(Job.status.in_([JobStatus.PENDING, JobStatus.IN_PROGRESS]))
            .all()
        )
    except Exception as e:
        logger.error("get_active_jobs_failed", job_type=job_type.value, error=str(e), exc_info=True)
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


def stop_job(job_id: Union[UUID, str]) -> Optional[Job]:
    """Manually stop a job by marking it CANCELLED.

    Unlike :func:`cancel_job` (which only touches PENDING jobs), this stops any
    *active* job — PENDING, IN_PROGRESS, or BACKOFF (a deferred job waiting on a
    dependency is still on the queue, not terminal). Note this only updates DB
    state — a worker already executing the job will keep running until its current
    task finishes; the CANCELLED status simply prevents it from being picked up /
    retried and flags intent. Returns None if the job is missing or already in a
    terminal state (COMPLETED / FAILED / CANCELLED).
    """
    try:
        session = get_db_session()
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.warning("stop_job_not_found", job_id=str(job_id))
            return None
        if job.status not in (JobStatus.PENDING, JobStatus.IN_PROGRESS, JobStatus.BACKOFF):
            logger.warning("stop_job_not_stoppable", job_id=str(job_id), status=job.status.value)
            return None
        job.status = JobStatus.CANCELLED
        job.completed_at = func.now()
        session.commit()
        logger.info("stopped_job", job_id=str(job_id))
        return job
    except Exception as e:
        session.rollback()
        logger.error("stop_job_failed", job_id=str(job_id), error=str(e), exc_info=True)
        raise


def update_job(
    job_id: Union[UUID, str],
    params: Optional[Dict[str, Any]] = None,
    priority: Optional[int] = None,
    max_retries: Optional[int] = None,
    replace_params: bool = False,
) -> Optional[Job]:
    """Edit an editable job's fields (params, priority, max_retries).

    Only PENDING or FAILED jobs can be edited — a job that is running, completed,
    or cancelled has either already consumed its params or will never run again,
    so editing it would be misleading. ``params`` is merged into the existing
    payload by default; pass ``replace_params=True`` to overwrite it wholesale.
    Returns None if the job is missing or not in an editable status.
    """
    try:
        session = get_db_session()
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.warning("update_job_not_found", job_id=str(job_id))
            return None
        if job.status not in (JobStatus.PENDING, JobStatus.FAILED):
            logger.warning("update_job_not_editable", job_id=str(job_id), status=job.status.value)
            return None
        if params is not None:
            # Reassign a fresh dict: the JSON column doesn't track in-place
            # mutation, so merging into job.params directly wouldn't be flushed.
            job.params = params if replace_params else {**(job.params or {}), **params}
        if priority is not None:
            job.priority = priority
        if max_retries is not None:
            job.max_retries = max_retries
        session.commit()
        logger.info("updated_job", job_id=str(job.id))
        return job
    except Exception as e:
        session.rollback()
        logger.error("update_job_failed", job_id=str(job_id), error=str(e), exc_info=True)
        raise


def claim_next_job(worker_id: str) -> Optional[Job]:
    """Atomically claim the highest-priority eligible pending job.

    Selection is by *effective* priority, not the stored one: a job's effective
    priority is ``priority - floor(age_seconds / priority_aging_interval)``,
    floored at 0, so a long-waiting low-priority job gradually overtakes fresh
    high-priority work. This keeps fast/required jobs (ingest, embed, diff) ahead
    of generated content under steady load, while guaranteeing content isn't
    starved as ingestion piles up — at the default 3600s interval, a 1h-old
    priority-2 job ties a fresh priority-1 job and, being older, wins the
    ``created_at`` tiebreak. ``created_at`` remains the tiebreak within a band, so
    aging is monotonic (older always weakly preferred). Set the interval <= 0 to
    fall back to strict ``priority, created_at`` order.

    Claiming is a SINGLE statement — ``UPDATE ... WHERE id = (SELECT ... FOR
    UPDATE SKIP LOCKED LIMIT 1) RETURNING`` — rather than a ``SELECT FOR UPDATE``
    followed by a separate ``UPDATE``. The two-statement form only holds the row
    lock across both statements on a *direct* connection; behind a transaction-
    or statement-pooling pooler (e.g. PgBouncer) the ``SELECT``'s lock and the
    ``UPDATE`` can land on different backends, so two workers can claim the same
    row. A single statement is atomic under every pooling mode.

    Both ``pending`` and ``backoff`` (dependency-wait) jobs are eligible: a
    ``backoff`` job is just a deferred job that's still waiting on a dependency,
    re-claimed the same way once its time arrives. Deferred jobs (``scheduled_at``
    in the future) are skipped until their time arrives; a NULL ``scheduled_at``
    is eligible immediately. The enum labels (``'pending'`` / ``'backoff'`` /
    ``'in_progress'``) are inlined as untyped literals so they coerce to
    ``job_status_enum`` without a bound-parameter cast.
    """
    from symbology.worker.config import worker_settings

    try:
        session = get_db_session()
        # Compare scheduled_at against a Python-side naive UTC "now" (matching how
        # scheduled_at is written and the stale-sweep convention) so a non-UTC DB
        # session timezone can't shift the timestamp/timestamptz comparison. The
        # same :now drives the age term in the priority decay below — created_at is
        # naive UTC too, so the subtraction is tz-independent.
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        aging = worker_settings.priority_aging_interval
        # Effective priority decays one step per `aging` seconds of age, floored at
        # 0. aging <= 0 disables decay (strict priority). created_at stays the
        # tiebreak so older jobs win within a band.
        if aging and aging > 0:
            # Inner GREATEST(0, ...) clamps a slightly-negative age (clock skew on a
            # just-created job) so FLOOR can't go to -1 and wrongly raise priority.
            order_by = (
                "GREATEST(0, priority - FLOOR("
                "GREATEST(0, EXTRACT(EPOCH FROM (:now - created_at))) / :aging"
                ")), created_at"
            )
        else:
            order_by = "priority, created_at"
        claimed_id = session.execute(
            text(
                f"""
                UPDATE jobs
                SET status = 'in_progress',
                    worker_id = :wid,
                    started_at = now()
                WHERE id = (
                    SELECT id FROM jobs
                    WHERE status IN ('pending', 'backoff')
                      AND (scheduled_at IS NULL OR scheduled_at <= :now)
                    ORDER BY {order_by}
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                RETURNING id
                """
            ),
            {"wid": worker_id, "now": now, "aging": aging},
        ).scalar()
        if claimed_id is None:
            session.commit()
            return None
        # Re-read inside the same transaction (sees our own UPDATE) for a fully
        # hydrated ORM instance, then commit to release the row.
        job = session.query(Job).filter(Job.id == claimed_id).first()
        session.commit()
        logger.info("claimed_job", job_id=str(claimed_id), worker_id=worker_id,
                    job_type=job.job_type.value if job else None)
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
    """Mark a job as failed, retrying with backoff if retries remain.

    A retryable failure goes to BACKOFF (not PENDING) with ``scheduled_at`` set
    by an exponential delay (floor ``retry_backoff_delay``, ceiling
    ``retry_backoff_delay_max``) keyed off the now-incremented ``retry_count``.
    That defers re-claim instead of letting a worker pick the job up on the very
    next poll — a transient failure (rate limit, flaky upstream) gets time to
    clear rather than being retried straight back into the same error.
    :func:`claim_next_job` re-claims a BACKOFF job once its ``scheduled_at``
    arrives, the same path used for dependency-wait deferrals. Once retries are
    exhausted the job is dead-lettered to FAILED.
    """
    from symbology.worker.config import worker_settings

    try:
        session = get_db_session()
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.warning("fail_job_not_found", job_id=str(job_id))
            return None
        job.error = error
        job.retry_count += 1
        if job.retry_count < job.max_retries:
            delay = min(
                worker_settings.retry_backoff_delay * (2 ** (job.retry_count - 1)),
                worker_settings.retry_backoff_delay_max,
            )
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            job.scheduled_at = now + timedelta(seconds=delay)
            job.status = JobStatus.BACKOFF
            job.worker_id = None
            job.started_at = None
            logger.info("requeued_job", job_id=str(job.id), retry_count=job.retry_count,
                        max_retries=job.max_retries, delay_seconds=delay,
                        scheduled_at=job.scheduled_at.isoformat())
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


def backoff_job(job_id: Union[UUID, str], reason: str) -> Optional[Job]:
    """Defer a job that's waiting on an unmet dependency.

    Unlike :func:`fail_job`, this is NOT a failure: it consumes no retry budget
    and never gives up. The job goes to BACKOFF with ``scheduled_at`` set by an
    exponential backoff (floor ``dependency_requeue_delay``, ceiling
    ``dependency_requeue_delay_max``) keyed off ``backoff_count``, so the first
    re-check is quick (deps usually land within a minute or two) and later ones
    back off to a cheap poll. It is re-claimed by :func:`claim_next_job` once its
    time arrives. ``reason`` is stored in ``error`` for visibility.
    """
    from symbology.worker.config import worker_settings

    try:
        session = get_db_session()
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.warning("backoff_job_not_found", job_id=str(job_id))
            return None
        job.backoff_count += 1
        delay = min(
            worker_settings.dependency_requeue_delay * (2 ** (job.backoff_count - 1)),
            worker_settings.dependency_requeue_delay_max,
        )
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        job.scheduled_at = now + timedelta(seconds=delay)
        job.status = JobStatus.BACKOFF
        job.worker_id = None
        job.started_at = None
        job.error = reason
        session.commit()
        logger.info("backoff_job", job_id=str(job.id), backoff_count=job.backoff_count,
                    delay_seconds=delay, scheduled_at=job.scheduled_at.isoformat(),
                    reason=reason)
        return job
    except Exception as e:
        session.rollback()
        logger.error("backoff_job_failed", job_id=str(job_id), error=str(e), exc_info=True)
        raise


def requeue_job_for_shutdown(job_id: Union[UUID, str]) -> Optional[Job]:
    """Return an IN_PROGRESS job to PENDING after a worker shutdown.

    Unlike :func:`fail_job`, this does NOT consume a retry: an operational
    restart is not the job's fault, so it should resume from where it was, not
    inch toward the retry ceiling. It is also idempotent — a no-op once the job
    is no longer IN_PROGRESS — so the executing worker thread (on a clean
    ``ShutdownRequested``) and the main loop (when the handler is stuck in an
    uninterruptible request) can both call it without double-handling.
    """
    try:
        session = get_db_session()
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.warning("requeue_for_shutdown_not_found", job_id=str(job_id))
            return None
        if job.status != JobStatus.IN_PROGRESS:
            # Already requeued (or finished) by the other party — nothing to do.
            return job
        job.status = JobStatus.PENDING
        job.worker_id = None
        job.started_at = None
        job.error = "worker shutdown during execution"
        session.commit()
        logger.info("requeued_job_for_shutdown", job_id=str(job.id))
        return job
    except Exception as e:
        session.rollback()
        logger.error("requeue_for_shutdown_failed", job_id=str(job_id), error=str(e), exc_info=True)
        raise


def count_jobs_by_status(status: JobStatus, job_type: Optional[JobType] = None) -> int:
    """Count jobs with a given status, optionally filtered by type."""
    try:
        session = get_db_session()
        query = session.query(func.count(Job.id)).filter(Job.status == status)
        if job_type:
            query = query.filter(Job.job_type == job_type)
        return query.scalar() or 0
    except Exception as e:
        logger.error("count_jobs_by_status_failed", error=str(e), exc_info=True)
        raise


def requeue_failed_jobs(job_type: Optional[JobType] = None) -> List[Job]:
    """Reset FAILED jobs to PENDING so they can be retried.

    Clears retry_count, worker_id, error, started_at, and completed_at.
    """
    try:
        session = get_db_session()
        query = session.query(Job).filter(Job.status == JobStatus.FAILED)
        if job_type:
            query = query.filter(Job.job_type == job_type)
        jobs = query.all()
        for job in jobs:
            job.status = JobStatus.PENDING
            job.retry_count = 0
            job.worker_id = None
            job.error = None
            job.started_at = None
            job.completed_at = None
        if jobs:
            session.commit()
            logger.info("requeued_failed_jobs", count=len(jobs), job_type=job_type)
        return jobs
    except Exception as e:
        session.rollback()
        logger.error("requeue_failed_jobs_failed", error=str(e), exc_info=True)
        raise


def requeue_job(
    job_id: Union[UUID, str],
    force: bool = False,
    extra_params: Optional[Dict[str, Any]] = None,
) -> Optional[Job]:
    """Requeue a single job for immediate execution.

    By default only FAILED, CANCELLED, or BACKOFF jobs are requeuable: a FAILED or
    CANCELLED job is reset to PENDING with its retry budget cleared (retry_count,
    worker_id, error, started_at, completed_at), while a BACKOFF job — still on the
    queue, just deferred — is left in BACKOFF with its ``scheduled_at`` pulled
    forward to now.

    ``force=True`` additionally allows re-running a COMPLETED job (reset to PENDING)
    — e.g. to regenerate output after a fix — and resets BACKOFF fully to PENDING
    rather than merely pulling it forward. IN_PROGRESS jobs are never requeuable
    (use ``stop`` first). ``extra_params`` is merged into the job's params before
    requeue, which is how a forced retry passes ``{"force": True}`` through to a
    handler that supports regeneration (e.g. diff_summary). Returns None if the job
    does not exist or is not in a requeuable status.
    """
    try:
        session = get_db_session()
        requeuable = [JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.BACKOFF]
        if force:
            requeuable.append(JobStatus.COMPLETED)
        job = (
            session.query(Job)
            .filter(Job.id == job_id, Job.status.in_(requeuable))
            .first()
        )
        if not job:
            return None
        if extra_params:
            # Reassign a fresh dict — the JSON column doesn't track in-place mutation.
            job.params = {**(job.params or {}), **extra_params}
        if job.status == JobStatus.BACKOFF and not force:
            # Already eligible for claiming once scheduled_at arrives; just bring
            # that forward to now. Keep backoff_count so a later self-deferral
            # resumes the exponential schedule rather than restarting it.
            job.scheduled_at = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            job.status = JobStatus.PENDING
            job.retry_count = 0
            job.worker_id = None
            job.error = None
            job.started_at = None
            job.completed_at = None
            job.scheduled_at = None
        session.commit()
        logger.info("requeued_job", job_id=str(job.id), status=job.status.value, force=force)
        return job
    except Exception as e:
        session.rollback()
        logger.error("requeue_job_failed", job_id=str(job_id), error=str(e), exc_info=True)
        raise


def cancel_jobs_by_status(
    statuses: Union[JobStatus, Iterable[JobStatus]],
    job_type: Optional[JobType] = None,
) -> int:
    """Bulk-cancel jobs in the given status(es) (→ CANCELLED). Returns count affected.

    Accepts a single status or an iterable of statuses; CANCELLED and COMPLETED
    jobs are never re-cancelled even if requested.
    """
    if isinstance(statuses, JobStatus):
        statuses = [statuses]
    statuses = [s for s in statuses if s not in (JobStatus.CANCELLED, JobStatus.COMPLETED)]
    if not statuses:
        return 0
    try:
        session = get_db_session()
        query = session.query(Job).filter(Job.status.in_(statuses))
        if job_type:
            query = query.filter(Job.job_type == job_type)
        count = query.update({Job.status: JobStatus.CANCELLED}, synchronize_session=False)
        session.commit()
        logger.info(
            "cancelled_jobs_by_status",
            count=count,
            statuses=[s.value for s in statuses],
            job_type=job_type,
        )
        return count
    except Exception as e:
        session.rollback()
        logger.error("cancel_jobs_by_status_failed", error=str(e), exc_info=True)
        raise


def cancel_failed_jobs(job_type: Optional[JobType] = None) -> int:
    """Bulk-cancel FAILED jobs (FAILED → CANCELLED). Returns count affected."""
    return cancel_jobs_by_status(JobStatus.FAILED, job_type=job_type)
