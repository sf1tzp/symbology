"""Worker configuration via environment variables."""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    """Configuration for the background job worker."""

    poll_interval: float = Field(default=2.0, description="Seconds between queue polls")
    stale_threshold: int = Field(default=600, description="Seconds before an in-progress job is considered stale")
    stale_check_interval: float = Field(default=60.0, description="Seconds between stale-job sweeps")

    model_config = SettingsConfigDict(
        env_prefix="WORKER_",
        extra="ignore",
    )


worker_settings = WorkerSettings()
