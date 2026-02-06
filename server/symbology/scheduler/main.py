"""Scheduler process — periodic poll loop with graceful shutdown."""
import signal
import time

from symbology.database.base import init_db
from symbology.scheduler.config import scheduler_settings
from symbology.scheduler.polling import poll_all_companies
from symbology.utils.config import settings
from symbology.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


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
            from symbology.scheduler.alerts import check_alerts
            check_alerts()
        except Exception:
            logger.exception("alert_check_error")

        # Sleep in short intervals to respond to signals promptly
        elapsed = 0.0
        while elapsed < scheduler_settings.poll_interval and not shutdown_requested:
            time.sleep(min(5.0, scheduler_settings.poll_interval - elapsed))
            elapsed += 5.0

    logger.info("scheduler_shutdown")


if __name__ == "__main__":
    run_scheduler()
