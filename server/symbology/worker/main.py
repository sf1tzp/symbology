"""Background job worker — poll loop with graceful shutdown."""
import os
import signal
import socket
import time

from symbology.database.base import init_db
from symbology.database.jobs import claim_next_job, complete_job, fail_job, mark_stale_jobs_as_failed
from symbology.utils.config import settings
from symbology.utils.logging import configure_logging, get_logger
from symbology.worker.config import worker_settings
from symbology.llm.client import ShutdownRequested, set_shutdown_flag, reset_shutdown_flag
from symbology.worker.handlers import get_handler, list_handlers

# Import handlers module so decorators run and register themselves

logger = get_logger(__name__)


def _worker_id() -> str:
    return f"{socket.gethostname()}-{os.getpid()}"


def run_worker() -> None:
    """Main entry point for the worker process."""
    configure_logging(log_level=settings.logging.level, json_format=settings.logging.json_format)
    init_db(settings.database.url)

    wid = _worker_id()
    shutdown_requested = False
    reset_shutdown_flag()

    def _handle_signal(signum, frame):
        nonlocal shutdown_requested
        logger.info("shutdown_signal_received", signal=signum, worker_id=wid)
        shutdown_requested = True
        set_shutdown_flag()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    logger.info("worker_started", worker_id=wid, handlers=list(list_handlers().keys()))

    last_stale_check = time.monotonic()

    while not shutdown_requested:
        # Periodic stale-job sweep
        now = time.monotonic()
        if now - last_stale_check >= worker_settings.stale_check_interval:
            try:
                stale = mark_stale_jobs_as_failed(worker_settings.stale_threshold)
                if stale:
                    logger.info("stale_sweep_complete", recovered=len(stale))
            except Exception:
                logger.exception("stale_sweep_error")
            last_stale_check = now

        # Try to claim work
        try:
            job = claim_next_job(wid)
        except Exception:
            logger.exception("claim_error")
            time.sleep(worker_settings.poll_interval)
            continue

        if job is None:
            time.sleep(worker_settings.poll_interval)
            continue

        # Execute handler
        handler = get_handler(job.job_type)
        if handler is None:
            fail_job(job.id, error=f"No handler registered for {job.job_type.value}")
            continue

        logger.info("executing_job", job_id=str(job.id), job_type=job.job_type.value)
        try:
            result = handler(job.params or {})
            complete_job(job.id, result=result)
            logger.info("job_completed", job_id=str(job.id))
        except ShutdownRequested:
            logger.info("job_interrupted_by_shutdown", job_id=str(job.id))
            fail_job(job.id, error="worker shutdown during execution")
        except Exception as exc:
            logger.exception("job_execution_failed", job_id=str(job.id))
            fail_job(job.id, error=str(exc))

    logger.info("worker_shutdown", worker_id=wid)


if __name__ == "__main__":
    run_worker()
