import os

# Load environment variables
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

# Define environment type
ENV = os.environ.get("ENV", "development")


class DatabaseSettings(BaseSettings):
    """Database connection configuration."""

    user: str = Field(default="postgres")
    password: str = Field(default="postgres")
    database_name: str = Field(default="symbology")
    host: str = Field(default="localhost")
    port: int = Field(default=5432)

    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
        extra="ignore",
    )

    @property
    def url(self) -> str:
        """Construct database URL."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database_name}"


class SymbologyApiSettings(BaseSettings):
    host: str = Field(default="localhost")
    port: int = Field(default=8000)

    model_config = SettingsConfigDict(
        env_prefix="SYMBOLOGY_API_",
        extra="ignore",
    )


class EdgarApiSettings(BaseSettings):
    """API connector settings."""

    edgar_contact: str = Field(default="dude@stev.lol")

    model_config = SettingsConfigDict(
        env_prefix="EDGAR_",
        extra="ignore",
    )


class OpenAISettings(BaseSettings):
    """OpenAI API settings."""

    host: str = Field(default="localhost")
    port: str = Field(default="8000")
    default_model: str = Field(default="hf.co/lmstudio-community/gemma-3-12b-it-GGUF:Q6_K")

    model_config = SettingsConfigDict(
        env_prefix="OPENAI_API_",
        extra="ignore",
    )

    @property
    def url(self) -> str:
        """Construct open ai api URL."""
        return f"http://{self.host}:{self.port}"


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

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        extra="ignore",
    )


class HuggingFaceApiSettings():
    token: str = Field(default="")

    model_config = SettingsConfigDict(
        env_prefix="HF_",
        extra="ignore",
    )


class Settings(BaseSettings):
    """Main application settings."""

    env: str = Field(default="development")
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    symbology_api: SymbologyApiSettings = Field(default_factory=SymbologyApiSettings)
    edgar_api: EdgarApiSettings = Field(default_factory=EdgarApiSettings)
    huggingface_api: HuggingFaceApiSettings = Field(default_factory=HuggingFaceApiSettings)
    openai_api: OpenAISettings = Field(default_factory=OpenAISettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Create and export a settings instance
settings = Settings()
