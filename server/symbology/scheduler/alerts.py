"""Alert detection and webhook dispatch for pipeline monitoring."""
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from urllib.parse import urlparse

import httpx
from symbology.database.companies import get_company
from symbology.database.pipeline_runs import (
    PipelineRunStatus,
    count_consecutive_failures,
    get_latest_run_per_company,
    list_pipeline_runs,
)
from symbology.scheduler.config import scheduler_settings
from symbology.utils.logging import get_logger

logger = get_logger(__name__)


def detect_consecutive_failures(threshold: int) -> List[Dict]:
    """Find companies with consecutive failure counts at or above threshold.

    Returns list of dicts: [{company_id, ticker, consecutive_failures}]
    """
    latest_runs = get_latest_run_per_company()
    alerts = []
    for run in latest_runs:
        failures = count_consecutive_failures(run.company_id)
        if failures >= threshold:
            company = get_company(run.company_id)
            ticker = company.ticker if company else "unknown"
            alerts.append({
                "company_id": str(run.company_id),
                "ticker": ticker,
                "consecutive_failures": failures,
            })
    return alerts


def detect_stale_runs(threshold_seconds: int) -> List[Dict]:
    """Find pipeline runs stuck in RUNNING state beyond the threshold.

    Returns list of dicts: [{run_id, company_id, stale_seconds}]
    """
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=threshold_seconds)
    running = list_pipeline_runs(status=PipelineRunStatus.RUNNING)
    alerts = []
    for run in running:
        if run.started_at and run.started_at < cutoff:
            stale_seconds = int((datetime.now(timezone.utc).replace(tzinfo=None) - run.started_at).total_seconds())
            alerts.append({
                "run_id": str(run.id),
                "company_id": str(run.company_id),
                "stale_seconds": stale_seconds,
            })
    return alerts


def send_webhook(url: str, payload: dict, timeout: int = 10) -> None:
    """Send an alert payload to a webhook URL.

    Logs the host only (no credential leakage).
    """
    url_host = urlparse(url).hostname or "unknown"
    try:
        response = httpx.post(url, json=payload, timeout=timeout)
        logger.info(
            "alert_webhook_sent",
            url_host=url_host,
            status_code=response.status_code,
        )
    except Exception as exc:
        logger.error(
            "alert_webhook_failed",
            url_host=url_host,
            error_type=type(exc).__name__,
        )


def check_alerts() -> None:
    """Orchestrate alert detection and dispatch.

    Called from the scheduler loop. Detects consecutive failures and stale
    runs, emits structured log events, and sends webhook if configured.
    """
    cfg = scheduler_settings

    failure_alerts = detect_consecutive_failures(cfg.alert_consecutive_failure_threshold)
    stale_alerts = detect_stale_runs(cfg.alert_stale_run_threshold_seconds)

    for alert in failure_alerts:
        logger.warning(
            "alert_consecutive_failures",
            ticker=alert["ticker"],
            company_id=alert["company_id"],
            consecutive_failures=alert["consecutive_failures"],
        )

    for alert in stale_alerts:
        logger.warning(
            "alert_stale_run",
            run_id=alert["run_id"],
            company_id=alert["company_id"],
            stale_seconds=alert["stale_seconds"],
        )

    logger.info(
        "alert_check_completed",
        failure_alerts=len(failure_alerts),
        stale_alerts=len(stale_alerts),
    )

    if cfg.alert_webhook_url and (failure_alerts or stale_alerts):
        send_webhook(
            url=cfg.alert_webhook_url,
            payload={
                "failure_alerts": failure_alerts,
                "stale_alerts": stale_alerts,
            },
            timeout=cfg.alert_webhook_timeout,
        )
