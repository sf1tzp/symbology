"""Background job worker — poll loop with graceful shutdown."""

import os
import signal
import socket
import threading
import time
import uuid

from symbology.database.base import init_db, close_session
from symbology.database.jobs import (
    backoff_job,
    claim_next_job,
    complete_job,
    fail_job,
    heartbeat_job,
    requeue_job_for_shutdown,
)
from symbology.utils.config import settings
from symbology.utils.logging import configure_logging, get_logger
from symbology.worker.config import worker_settings
from symbology.llm.client import (
    ShutdownRequested,
    set_shutdown_flag,
    reset_shutdown_flag,
)
from symbology.worker.handlers import DependencyNotReady, get_handler, list_handlers

# Import handlers module so decorators run and register themselves

logger = get_logger(__name__)


def _worker_id() -> str:
    """A unique, human-readable id for this worker process."""
    explicit = os.environ.get("WORKER_NAME")
    if explicit:
        return explicit
    return f"{socket.gethostname()}-{uuid.uuid4().hex[:6]}"


def _execute_job(job, db_session) -> None:
    """Run a job's handler and record its outcome.

    Runs in a daemon thread so the main loop keeps observing shutdown signals
    while a handler blocks on a long-running, uninterruptible LLM request. All
    DB work happens here using this thread's own (thread-local) scoped session,
    which is removed in ``finally``.
    """
    handler = get_handler(job.job_type)
    if handler is None:
        fail_job(job.id, error=f"No handler registered for {job.job_type.value}")
        return
    try:
        result = handler(job.params or {})
        complete_job(job.id, result=result)
        logger.info("job_completed", job_id=str(job.id))
    except DependencyNotReady as exc:
        # Not a failure: a dependency isn't ready yet. Defer (BACKOFF) without
        # burning a retry; the job polls until the dependency lands.
        db_session.rollback()
        logger.info("job_backoff", job_id=str(job.id), reason=str(exc))
        backoff_job(job.id, reason=str(exc))
    except ShutdownRequested:
        # retry_backoff broke out of a backoff sleep cleanly. Requeue without
        # burning a retry; idempotent with the main loop's stuck-job path.
        db_session.rollback()
        logger.info("job_interrupted_by_shutdown", job_id=str(job.id))
        requeue_job_for_shutdown(job.id)
    except Exception as exc:
        db_session.rollback()
        logger.exception("job_execution_failed", job_id=str(job.id))
        fail_job(job.id, error=str(exc))
    finally:
        close_session()


def run_worker() -> None:
    """Main entry point for the worker process."""
    configure_logging(
        log_level=settings.logging.level, json_format=settings.logging.json_format
    )

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

    # Initialize the database ONCE for the worker's lifetime. Calling init_db()
    # inside the poll loop builds a fresh engine + connection pool every
    # iteration and never disposes the old one, leaking idle connections until
    # the server hits "too many clients already". One engine per process keeps
    # the pool bounded (and makes running several workers in parallel safe).
    engine, db_session = init_db(settings.database.url)

    while not shutdown_requested:

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

        # Execute the handler in a daemon thread. A handler can block for
        # minutes inside an LLM request that ignores the shutdown flag (the flag
        # is only checked between retry_backoff attempts, never mid-request), so
        # running it inline would make the worker deaf to SIGTERM until the call
        # returned — long enough for the container to SIGKILL us, stranding the
        # job IN_PROGRESS. A daemon thread lets the main loop poll for shutdown
        # and requeue the job itself; the thread then dies with the process.
        logger.info("executing_job", job_id=str(job.id), job_type=job.job_type.value)
        done = threading.Event()

        def _runner(job=job):
            try:
                _execute_job(job, db_session)
            finally:
                done.set()

        worker_thread = threading.Thread(target=_runner, name="job-exec", daemon=True)
        worker_thread.start()

        # Wait for the handler, waking every second to check for shutdown and to
        # heartbeat. The heartbeat (running in this thread, not the blocked
        # handler thread) keeps the job's updated_at fresh so the stale sweep
        # doesn't reclaim a job that's still legitimately running.
        last_heartbeat = time.monotonic()
        while not done.wait(timeout=1.0):
            if shutdown_requested:
                break
            now = time.monotonic()
            if now - last_heartbeat >= worker_settings.heartbeat_interval:
                try:
                    heartbeat_job(job.id, wid)
                except Exception:
                    logger.exception("heartbeat_error", job_id=str(job.id))
                last_heartbeat = now

        if not done.is_set():
            # Shutdown requested while the handler is still blocked. The thread
            # can't be interrupted, so requeue the job here and exit; the daemon
            # thread is abandoned and dies with the process. Idempotent with the
            # thread's own ShutdownRequested path if it unblocks in the meantime.
            requeue_job_for_shutdown(job.id)
            close_session()
            break

    # Release the pool's connections promptly on graceful shutdown.
    engine.dispose()
    logger.info("worker_shutdown", worker_id=wid)


if __name__ == "__main__":
    run_worker()
