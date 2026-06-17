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
        default=120.0,
        description=(
            "Base seconds a job in BACKOFF waits before re-checking when its source "
            "filing pages / embeddings are still being generated (deferred via "
            "Job.scheduled_at). Floor of the exponential backoff in backoff_job(), "
            "so the first re-check is quick and later ones back off (keyed off "
            "Job.backoff_count)."
        ),
    )
    dependency_requeue_delay_max: float = Field(
        default=600.0,
        description="Ceiling (seconds) for the exponential dep-wait backoff.",
    )
    retry_backoff_delay: float = Field(
        default=30.0,
        description=(
            "Base seconds a failed-but-retryable job waits in BACKOFF before it's "
            "eligible for re-claim (deferred via Job.scheduled_at). Floor of the "
            "exponential retry backoff in fail_job(), keyed off Job.retry_count, so "
            "a transient failure (rate limit, flaky network) isn't retried "
            "instantly into the same error. Distinct from dependency_requeue_delay, "
            "which paces dependency-wait deferrals."
        ),
    )
    retry_backoff_delay_max: float = Field(
        default=600.0,
        description="Ceiling (seconds) for the exponential failure-retry backoff.",
    )
    priority_aging_interval: float = Field(
        default=3600.0,
        description=(
            "Seconds of queue age that earn a job one step of effective priority "
            "in claim_next_job (lower = sooner). A job's effective priority is "
            "priority - floor(age / interval), floored at 0, so a long-waiting "
            "low-priority job eventually overtakes fresh high-priority work — "
            "fast/required jobs (ingest, embed, diff) still lead, but generated "
            "content isn't starved as ingestion piles up. At the default 3600, a "
            "1h-old priority-2 job ties (and, being older, beats) a fresh "
            "priority-1 job. Set <= 0 to disable aging (strict priority order)."
        ),
    )

    model_config = SettingsConfigDict(
        env_prefix="WORKER_",
        extra="ignore",
    )


worker_settings = WorkerSettings()
