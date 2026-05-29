# Load environment variables
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class DatabaseSettings(BaseSettings):
    user: str = Field(default="postgres")
    password: str = Field(default="postgres")
    database_name: str = Field(default="symbology")
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
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database_name}"


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

    # Embedding model configuration
    embedding_model: str = Field(default="jina-embeddings-v5-omni-small-retrieval")
    embedding_dimensions: int = Field(default=1024)

    # Request behaviour
    embedding_batch_size: int = Field(
        default=32, description="Max inputs per embeddings request"
    )
    request_timeout: float = Field(
        default=60.0, description="Per-request timeout in seconds"
    )
    retry_timeout: float = Field(
        default=600.0, description="Total seconds to keep retrying on failure"
    )

    # Chunking defaults (characters). Tuned for ~512-token retrieval chunks.
    chunk_size: int = Field(default=2000, description="Target chunk size in characters")
    chunk_overlap: int = Field(
        default=200, description="Overlap between consecutive chunks in characters"
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
