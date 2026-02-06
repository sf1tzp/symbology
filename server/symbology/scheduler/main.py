"""Scheduler process — periodic poll loop with graceful shutdown."""
import signal
import time

from symbology.database.base import init_db
from symbology.database.pipeline_runs import PipelineRunStatus, list_pipeline_runs
from symbology.scheduler.config import scheduler_settings
from symbology.scheduler.polling import poll_all_companies
from symbology.utils.config import settings
from symbology.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


def _detect_stale_runs(threshold_seconds: int = 7200) -> None:
    """Log warnings for pipeline runs stuck in RUNNING state."""
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=threshold_seconds)
    running = list_pipeline_runs(status=PipelineRunStatus.RUNNING)
    for run in running:
        if run.started_at and run.started_at < cutoff:
            logger.warning(
                "stale_pipeline_run_detected",
                run_id=str(run.id),
                started_at=str(run.started_at),
                company_id=str(run.company_id),
            )


def run_scheduler() -> None:
    """Main entry point for the scheduler process."""
    configure_logging(
        log_level=settings.logging.level,
        json_format=settings.logging.json_format,
    )
    init_db(settings.database.url)

    shutdown_requested = False

    def _handle_signal(signum, frame):
        nonlocal shutdown_requested
        logger.info("scheduler_shutdown_signal", signal=signum)
        shutdown_requested = True

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    logger.info(
        "scheduler_started",
        poll_interval=scheduler_settings.poll_interval,
        enabled_forms=scheduler_settings.enabled_forms,
        lookback_days=scheduler_settings.filing_lookback_days,
    )

    while not shutdown_requested:
        try:
            poll_all_companies(
                forms=scheduler_settings.enabled_forms,
                lookback_days=scheduler_settings.filing_lookback_days,
            )
        except Exception:
            logger.exception("poll_cycle_error")

        try:
            _detect_stale_runs()
        except Exception:
            logger.exception("stale_run_detection_error")

        # Sleep in short intervals to respond to signals promptly
        elapsed = 0.0
        while elapsed < scheduler_settings.poll_interval and not shutdown_requested:
            time.sleep(min(5.0, scheduler_settings.poll_interval - elapsed))
            elapsed += 5.0

    logger.info("scheduler_shutdown")


if __name__ == "__main__":
    run_scheduler()
