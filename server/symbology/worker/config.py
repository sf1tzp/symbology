"""Worker configuration via environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    """Configuration for the background job worker."""

    poll_interval: float = Field(default=2.0, description="Seconds between queue polls")
    heartbeat_interval: float = Field(
        default=15.0,
        description="Seconds between liveness heartbeats for the running job",
    )
    stale_threshold: int = Field(
        default=90,
        description=(
            "Seconds without a heartbeat before an in-progress job is considered "
            "stale. Must be comfortably above heartbeat_interval so a live job is "
            "never reclaimed mid-flight."
        ),
    )
    stale_check_interval: float = Field(
        default=60.0, description="Seconds between stale-job sweeps"
    )
    dependency_requeue_delay: float = Field(
        default=600.0,
        description=(
            "Seconds a company page job waits before re-checking when its source "
            "filing pages are still being generated (deferred via Job.scheduled_at)."
        ),
    )
    dependency_requeue_max_attempts: int = Field(
        default=6,
        description=(
            "Max times a company page job reschedules itself waiting on in-flight "
            "filing page content before failing loudly. Bounds the wait separately "
            "from max_retries (which counts genuine crashes, retried immediately)."
        ),
    )

    model_config = SettingsConfigDict(
        env_prefix="WORKER_",
        extra="ignore",
    )


worker_settings = WorkerSettings()
