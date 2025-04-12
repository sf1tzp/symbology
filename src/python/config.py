import logging
import os

# Load environment variables
from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings

load_dotenv()

# Define environment type
ENV = os.environ.get("ENV", "development")


class DatabaseSettings(BaseModel):
    """Database connection configuration."""

    postgres_user: str = Field(default="postgres", env="POSTGRES_USER")
    postgres_password: str = Field(default="postgres", env="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="symbology", env="POSTGRES_DB")
    host: str = Field(default="10.0.0.3", env="POSTGRES_HOST")
    port: int = Field(default=5432, env="POSTGRES_PORT")

    @property
    def url(self) -> str:
        """Construct database URL."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.host}:{self.port}/{self.postgres_db}"


class PGAdminSettings(BaseSettings):
    """PGAdmin settings."""

    email: str = Field(default="dude@stev.lol", env="PGADMIN_EMAIL")
    password: str = Field(default="postgres", env="PGADMIN_PASSWORD")


class ApiSettings(BaseModel):
    """API connector settings."""

    edgar_contact: str = "dude@stev.lol"


class OpenAISettings(BaseModel):
    """OpenAI API settings."""

    open_ai_host: str = "10.0.0.4"
    open_ai_port: str = "24098"


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    level: str = Field(default="INFO", env="LOG_LEVEL")

    @validator("level")
    def validate_log_level(cls, v: str) -> int:
        """Convert log level string to logging constant."""
        levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        return levels.get(v.upper(), logging.INFO)


class Settings(BaseSettings):
    """Main application settings."""

    env: str = Field(default="development", env="ENV")
    database: DatabaseSettings = DatabaseSettings()
    pgadmin: PGAdminSettings = PGAdminSettings()
    api: ApiSettings = ApiSettings()
    openai: OpenAISettings = OpenAISettings()
    logging: LoggingSettings = LoggingSettings()

    class Config:
        env_prefix = ""
        env_nested_delimiter = "__"
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Allow extra fields if needed


# Create and export a settings instance
settings = Settings()

# Configure logging
logging.basicConfig(
    level=settings.logging.level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
