# Load environment variables
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class DatabaseSettings(BaseSettings):
    user: str = Field(default="postgres")
    password: str = Field(default="postgres")
    name: str = Field(default="symbology")
    host: str = Field(default="localhost")
    port: int = Field(default=5432)

    # model_config refers to the Pydanic Model (not an LLM model)
    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
        extra="ignore",
    )

    @property
    def url(self) -> str:
        """Construct database URL."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class EdgarApiSettings(BaseSettings):
    edgar_contact: str = Field(default="dude@stev.lol")

    # model_config refers to the Pydanic Model (not an LLM model)
    model_config = SettingsConfigDict(
        env_prefix="EDGAR_",
        extra="ignore",
    )


class AnthropicSettings(BaseSettings):
    api_key: str = Field(default="")
    default_model: str = Field(default="claude-haiku-4-5-20251001")
    model_config = SettingsConfigDict(
        env_prefix="ANTHROPIC_",
        extra="ignore",
    )


class OpenAISettings(BaseSettings):
    # Connection (matches the OPENAI_API_HOST / OPENAI_API_PORT placeholders)
    api_host: str = Field(default="localhost")
    api_port: int = Field(default=11434)
    api_key: str = Field(
        default="not-needed", description="Bearer token; many local servers ignore it"
    )

    # Embedding model configuration. nomic-embed-text-v1.5 is the standardized
    # embedding model (768-dim); it loads as an embedding-type instance in
    # LM Studio, unlike the qwen3-architecture jina model which LM Studio treats
    # as an LLM and refuses to serve from /v1/embeddings.
    embedding_model: str = Field(default="text-embedding-nomic-embed-text-v1.5")
    embedding_dimensions: int = Field(default=768)
    # nomic models expect a task-instruction prefix on each input; "clustering:"
    # suits within-company topic alignment (symmetric chunk-vs-chunk comparison).
    # Empty string disables prefixing (for models that don't use it).
    embedding_task_prefix: str = Field(default="clustering: ")
    # Cosine *distance* below which a chunk joins an existing topic. Model-
    # dependent: nomic's cosine range is compressed (unrelated risk text sits at
    # ~0.70 similarity / 0.30 distance), so same-company same-section text needs a
    # tight threshold. Measured on TSLA risk factors: same risk year-over-year is
    # <0.03 apart, distinct risks >0.08 apart — 0.05 sits in the separating gap.
    topic_distance_threshold: float = Field(default=0.05)

    # Request behaviour
    embedding_batch_size: int = Field(
        default=32, description="Max inputs per embeddings request"
    )
    request_timeout: float = Field(
        default=60.0, description="Per-request timeout in seconds (embeddings)"
    )
    chat_request_timeout: float = Field(
        default=1200.0,
        description="Per-request timeout (s) for chat completions; long because "
        "local generation can take minutes",
    )
    retry_timeout: float = Field(
        default=600.0, description="Total seconds to keep retrying on failure"
    )

    # Chunking defaults (characters). Tuned for ~512-token retrieval chunks.
    chunk_size: int = Field(default=2000, description="Target chunk size in characters")
    chunk_overlap: int = Field(
        default=200, description="Overlap between consecutive chunks in characters"
    )

    # Dynamic context sizing (LM Studio model load API). When enabled, the chat
    # client (re)loads the served model with a context window sized to each
    # request, so oversized filing sections (e.g. risk_factors) don't overflow a
    # fixed window and abort the pipeline with a non-retryable 4xx.
    manage_context: bool = Field(
        default=True,
        description="(Re)load the model with a per-request context window via the "
        "LM Studio model-load API before each OpenAI-provider call",
    )
    management_path: str = Field(
        default="/api/v1",
        description="Base path of LM Studio's management API (hosts /models/load)",
    )
    context_min: int = Field(
        default=4096, description="Smallest context window to ever load (tokens)"
    )
    context_max: int = Field(
        default=128000,
        description="Largest context window the hardware can serve (tokens); "
        "requests are clamped to this ceiling",
    )
    context_bucket: int = Field(
        default=4096,
        description="Round the required context up to this multiple so similar "
        "request sizes reuse one loaded window instead of reloading",
    )
    chars_per_token: float = Field(
        default=3.5,
        description="Heuristic chars-per-token used to estimate prompt size "
        "(conservatively low to over-estimate tokens)",
    )
    context_safety_margin: float = Field(
        default=1.15,
        description="Multiplier on estimated prompt+output tokens for headroom",
    )
    model_load_timeout: float = Field(
        default=300.0,
        description="Per-request timeout (s) for a model-load call (loading a "
        "large context can take a while)",
    )

    # Overflow offload to Anthropic. Prompts above this estimated token size are
    # both slow to serve locally and risk overflowing even a dynamically-sized
    # window, so route them to a (large-context) Anthropic model instead.
    overflow_threshold_tokens: int = Field(
        default=32000,
        description="Estimated prompt tokens above which a local request is "
        "offloaded to Anthropic; 0 disables offload",
    )
    overflow_model: str = Field(
        default="claude-sonnet-4-6",
        description="Anthropic model to offload oversized prompts to; empty "
        "falls back to ANTHROPIC_DEFAULT_MODEL",
    )

    # model_config refers to the Pydanic Model (not an LLM model)
    model_config = SettingsConfigDict(
        env_prefix="OPENAI_",
        extra="ignore",
    )

    @property
    def base_url(self) -> str:
        """Construct the OpenAI-compatible base URL (with /v1 suffix)."""
        return f"http://{self.api_host}:{self.api_port}/v1"

    @property
    def management_url(self) -> str:
        """Base URL of LM Studio's management API (e.g. the model-load endpoint)."""
        return f"http://{self.api_host}:{self.api_port}{self.management_path}"


class LoggingSettings(BaseSettings):
    """
    Logging configuration settings.

    Attributes:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to output logs in JSON format
                    (useful for production environments and log aggregation)

    Environment variables:
        LOG_LEVEL: Override the log level
        LOG_JSON_FORMAT: Set to "true" or "1" to enable JSON logging format
    """

    level: str = Field(default="INFO")
    json_format: bool = Field(default=False)

    # model_config refers to the Pydanic Model (not an LLM model)
    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        extra="ignore",
    )


class Settings(BaseSettings):
    """Main application settings."""

    env: str = Field(default="development")
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    edgar_api: EdgarApiSettings = Field(default_factory=EdgarApiSettings)
    anthropic: AnthropicSettings = Field(default_factory=AnthropicSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Create and export a settings instance
settings = Settings()
