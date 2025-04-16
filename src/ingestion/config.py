import os

# Load environment variables
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings

load_dotenv()

# Define environment type
ENV = os.environ.get("ENV", "development")


class DatabaseSettings(BaseModel):
    """Database connection configuration."""

    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")
    postgres_db: str = Field(default="symbology")
    host: str = Field(default="10.0.0.3")
    port: int = Field(default=5432)

    model_config = ConfigDict(
        env_prefix="",
        extra="ignore",
        json_schema_extra={
            "env": {
                "postgres_user": "POSTGRES_USER",
                "postgres_password": "POSTGRES_PASSWORD",
                "postgres_db": "POSTGRES_DB",
                "host": "POSTGRES_HOST",
                "port": "POSTGRES_PORT"
            }
        }
    )

    @property
    def url(self) -> str:
        """Construct database URL."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.host}:{self.port}/{self.postgres_db}"


class PGAdminSettings(BaseSettings):
    """PGAdmin settings."""

    email: str = Field(default="dude@stev.lol")
    password: str = Field(default="postgres")

    model_config = ConfigDict(
        env_prefix="",
        extra="ignore",
        json_schema_extra={
            "env": {
                "email": "PGADMIN_EMAIL",
                "password": "PGADMIN_PASSWORD"
            }
        }
    )


class ApiSettings(BaseModel):
    """API connector settings."""

    edgar_contact: str = "dude@stev.lol"


class OpenAISettings(BaseModel):
    """OpenAI API settings."""

    open_ai_host: str = Field(default="10.0.0.4")
    open_ai_port: str = Field(default="11434")
    default_model: str = Field(default="hf.co/lmstudio-community/gemma-3-12b-it-GGUF:Q6_K")

    model_config = ConfigDict(
        env_prefix="",
        extra="ignore",
        json_schema_extra={
            "env": {
                "open_ai_host": "OPENAI_HOST",
                "open_ai_port": "OPENAI_PORT",
                "default_model": "OPENAI_DEFAULT_MODEL"
            }
        }
    )


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

    model_config = ConfigDict(
        env_prefix="",
        extra="ignore",
        json_schema_extra={
            "env": {
                "level": "LOG_LEVEL",
                "json_format": "LOG_JSON_FORMAT"
            }
        }
    )


class Settings(BaseSettings):
    """Main application settings."""

    env: str = Field(default="development")
    database: DatabaseSettings = DatabaseSettings()
    pgadmin: PGAdminSettings = PGAdminSettings()
    api: ApiSettings = ApiSettings()
    openai: OpenAISettings = OpenAISettings()
    logging: LoggingSettings = LoggingSettings()

    model_config = ConfigDict(
        env_prefix="",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        json_schema_extra={
            "env": {
                "env": "ENV"
            }
        }
    )


# Create and export a settings instance
settings = Settings()
