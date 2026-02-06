"""Scheduler configuration via environment variables."""
from typing import List

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

    model_config = SettingsConfigDict(
        env_prefix="SCHEDULER_",
        extra="ignore",
    )


scheduler_settings = SchedulerSettings()
