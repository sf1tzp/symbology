"""Scheduler configuration via environment variables."""
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SchedulerSettings(BaseSettings):
    """Configuration for the EDGAR polling scheduler."""

    poll_interval: int = Field(
        default=21600,
        description="Seconds between polling cycles (default 6 hours)",
    )
    enabled_forms: List[str] = Field(
        default=["10-K", "10-Q"],
        description="SEC form types to poll for",
    )
    filing_lookback_days: int = Field(
        default=30,
        description="How far back to check for new filings (days)",
    )

    # Bulk ingestion settings
    bulk_ingest_enabled: bool = Field(
        default=False,
        description="Enable polling for ALL new EDGAR filings (not just tracked companies)",
    )
    bulk_ingest_forms: List[str] = Field(
        default=["10-K", "10-K/A", "10-Q", "10-Q/A"],
        description="Form types to discover in bulk ingestion",
    )
    bulk_ingest_batch_size: int = Field(
        default=50,
        description="Number of filings per BULK_INGEST job",
    )

    # Alert settings
    alert_consecutive_failure_threshold: int = Field(
        default=3,
        description="Number of consecutive failures before alerting",
    )
    alert_stale_run_threshold_seconds: int = Field(
        default=7200,
        description="Seconds before a RUNNING run is considered stale",
    )
    alert_webhook_url: Optional[str] = Field(
        default=None,
        description="Webhook URL for alert notifications",
    )
    alert_webhook_timeout: int = Field(
        default=10,
        description="Webhook request timeout in seconds",
    )

    model_config = SettingsConfigDict(
        env_prefix="SCHEDULER_",
        extra="ignore",
    )


scheduler_settings = SchedulerSettings()
