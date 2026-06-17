"""Worker registry: workers as a first-class, self-reporting entity.

A worker heartbeats *itself* (independent of whether it currently holds a job),
which decouples two facts the old per-job heartbeat conflated: "this job is
progressing" and "this worker is breathing". Liveness now lives on the worker
row, so the sweep can reason about *workers* — a worker whose heartbeat lapses
is declared dead and its in-progress jobs are reclaimed as an *operational*
event (no retry budget burned), exactly like a graceful-shutdown requeue. That
is the distinction the job-level stale sweep could never make: it only had a
job to point at, so it blamed the job.

A genuinely hung handler (worker alive but the work wedged) is intentionally
out of scope here — that's a per-job runtime concept, not liveness, and the old
sweep never caught it either (the heartbeat was bumped by the main loop, not the
handler).
"""
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import List, Optional
from uuid import UUID

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from symbology.database.base import Base, get_db_session
from symbology.database.jobs import Job, JobStatus
from symbology.utils.logging import get_logger

logger = get_logger(__name__)


class WorkerStatus(str, Enum):
    """Worker lifecycle states.

    ``idle`` / ``running`` are the live states (kept fresh by the heartbeat);
    ``stopped`` is a clean graceful shutdown; ``dead`` is assigned by the reap
    sweep when a live worker's heartbeat lapses past the stale threshold.
    """
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"
    DEAD = "dead"


# The live states a worker can be in while it should still be heartbeating.
_LIVE_STATUSES = (WorkerStatus.IDLE, WorkerStatus.RUNNING)


class Worker(Base):
    """A worker process, self-registered and self-heartbeating."""

    __tablename__ = "workers"

    # Stable across restarts when WORKER_NAME is set (see worker.main._worker_id),
    # so a restarted worker reuses its row rather than leaving a ghost behind.
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    hostname: Mapped[Optional[str]] = mapped_column(String(255))
    pid: Mapped[Optional[int]] = mapped_column(Integer)

    status: Mapped[WorkerStatus] = mapped_column(
        SQLEnum(WorkerStatus, name="worker_status_enum", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=WorkerStatus.IDLE,
    )
    # The job this worker is currently executing (loose reference to jobs.id; no
    # FK so clearing/deleting jobs never blocks on a worker row, mirroring how
    # jobs.worker_id loosely references a worker by id).
    current_job_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), nullable=True)

    last_heartbeat: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    started_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        # Drives the reap sweep: find live workers whose heartbeat has lapsed.
        Index("ix_workers_liveness", "status", "last_heartbeat"),
    )

    def __repr__(self) -> str:
        return f"<Worker(id={self.id}, status={self.status.value}, job={self.current_job_id})>"


def _utcnow() -> datetime:
    """Naive UTC now — matches how job timestamps are written/compared."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def register_worker(
    worker_id: str, hostname: Optional[str] = None, pid: Optional[int] = None
) -> Optional[Worker]:
    """Register (or re-register) a worker on boot, as IDLE with a fresh heartbeat.

    Idempotent across restarts: if a row already exists for ``worker_id`` (stable
    identity via WORKER_NAME) it's reset rather than duplicated, so the dashboard
    shows continuity instead of a graveyard of one-shot rows.
    """
    try:
        session = get_db_session()
        now = _utcnow()
        worker = session.query(Worker).filter(Worker.id == worker_id).first()
        if worker is None:
            worker = Worker(id=worker_id)
            session.add(worker)
        worker.hostname = hostname
        worker.pid = pid
        worker.status = WorkerStatus.IDLE
        worker.current_job_id = None
        worker.started_at = now
        worker.last_heartbeat = now
        session.commit()
        logger.info("worker_registered", worker_id=worker_id, hostname=hostname, pid=pid)
        return worker
    except Exception as e:
        session.rollback()
        logger.error("register_worker_failed", worker_id=worker_id, error=str(e), exc_info=True)
        raise


def heartbeat_worker(
    worker_id: str,
    status: WorkerStatus = WorkerStatus.RUNNING,
    current_job_id: Optional[UUID] = None,
) -> bool:
    """Bump a worker's heartbeat (and its status / current job). Returns whether a row matched.

    Called on a fixed cadence by the main loop whether the worker is idle or
    running, so liveness never depends on holding a job. A False return means the
    row vanished (e.g. the worker was reaped as dead while briefly unable to
    heartbeat); the caller should re-register.
    """
    try:
        session = get_db_session()
        updated = (
            session.query(Worker)
            .filter(Worker.id == worker_id)
            .update(
                {
                    Worker.last_heartbeat: _utcnow(),
                    Worker.status: status,
                    Worker.current_job_id: current_job_id,
                },
                synchronize_session=False,
            )
        )
        session.commit()
        return updated > 0
    except Exception as e:
        session.rollback()
        logger.error("heartbeat_worker_failed", worker_id=worker_id, error=str(e), exc_info=True)
        raise


def mark_worker_stopped(worker_id: str) -> Optional[Worker]:
    """Mark a worker STOPPED on graceful shutdown — a clean exit, not a death."""
    try:
        session = get_db_session()
        worker = session.query(Worker).filter(Worker.id == worker_id).first()
        if worker is None:
            return None
        worker.status = WorkerStatus.STOPPED
        worker.current_job_id = None
        worker.last_heartbeat = _utcnow()
        session.commit()
        logger.info("worker_stopped", worker_id=worker_id)
        return worker
    except Exception as e:
        session.rollback()
        logger.error("mark_worker_stopped_failed", worker_id=worker_id, error=str(e), exc_info=True)
        raise


def reap_dead_workers(stale_threshold_seconds: int = 90) -> List[Job]:
    """Declare lapsed workers dead and reclaim their in-progress jobs operationally.

    A live (IDLE/RUNNING) worker whose ``last_heartbeat`` is older than the
    threshold is marked DEAD. Any IN_PROGRESS job whose owning worker is not
    currently live — a reaped worker, or one that vanished without ever
    registering — is requeued to PENDING **without** touching ``retry_count``:
    a worker disappearing is an operational event, not the job's fault (mirrors
    :func:`requeue_job_for_shutdown`). Returns the reclaimed jobs.

    The retry budget is reserved for genuine handler errors, so deploys and
    crashes that orphan healthy jobs no longer inch them toward the dead-letter.
    """
    try:
        session = get_db_session()
        cutoff = _utcnow() - timedelta(seconds=stale_threshold_seconds)

        # 1. Mark lapsed live workers dead.
        dead = (
            session.query(Worker)
            .filter(Worker.status.in_(_LIVE_STATUSES))
            .filter(Worker.last_heartbeat < cutoff)
            .all()
        )
        for w in dead:
            w.status = WorkerStatus.DEAD
            w.current_job_id = None
            logger.warning("worker_reaped_dead", worker_id=w.id,
                           last_heartbeat=w.last_heartbeat.isoformat())

        # 2. Live worker ids = those still heartbeating within the threshold.
        live_ids = {
            wid
            for (wid,) in session.query(Worker.id)
            .filter(Worker.status.in_(_LIVE_STATUSES))
            .filter(Worker.last_heartbeat >= cutoff)
            .all()
        }

        # 3. Reclaim IN_PROGRESS jobs owned by no live worker (dead, or never
        #    registered). Operational requeue: retry_count is left untouched.
        orphaned = (
            session.query(Job)
            .filter(Job.status == JobStatus.IN_PROGRESS)
            .all()
        )
        reclaimed: List[Job] = []
        for job in orphaned:
            if job.worker_id in live_ids:
                continue
            job.status = JobStatus.PENDING
            job.worker_id = None
            job.started_at = None
            job.scheduled_at = None
            job.error = f"worker {job.worker_id} vanished; job reassigned (retry budget intact)"
            reclaimed.append(job)
            logger.info("reclaimed_orphaned_job", job_id=str(job.id),
                        worker_id=job.worker_id, retry_count=job.retry_count)

        if dead or reclaimed:
            session.commit()
            logger.info("reaped_workers", dead_workers=len(dead), reclaimed_jobs=len(reclaimed))
        return reclaimed
    except Exception as e:
        session.rollback()
        logger.error("reap_dead_workers_failed", error=str(e), exc_info=True)
        raise


def list_live_workers(stale_threshold_seconds: int = 90) -> List[Worker]:
    """Workers currently considered online (live status + fresh heartbeat)."""
    try:
        session = get_db_session()
        cutoff = _utcnow() - timedelta(seconds=stale_threshold_seconds)
        return (
            session.query(Worker)
            .filter(Worker.status.in_(_LIVE_STATUSES))
            .filter(Worker.last_heartbeat >= cutoff)
            .order_by(Worker.id)
            .all()
        )
    except Exception as e:
        logger.error("list_live_workers_failed", error=str(e), exc_info=True)
        raise
