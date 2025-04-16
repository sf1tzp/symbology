"""API configuration module."""
import os
from typing import Optional

from src.utils.logging import get_logger

# Create logger for this module
logger = get_logger(__name__)

# Default values
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

# Environment variable names
ENV_HOST = "SYMBOLOGY_API_HOST"
ENV_PORT = "SYMBOLOGY_API_PORT"


def get_api_host() -> str:
    """Get the API host from environment variable or use default."""
    host = os.environ.get(ENV_HOST, DEFAULT_HOST)
    logger.debug("api_host_configured", host=host, from_env=ENV_HOST in os.environ)
    return host


def get_api_port() -> int:
    """Get the API port from environment variable or use default."""
    port_str = os.environ.get(ENV_PORT)
    if port_str:
        try:
            port = int(port_str)
            logger.debug("api_port_configured", port=port, from_env=True)
            return port
        except ValueError:
            logger.warning("invalid_port_in_env", port_str=port_str, default=DEFAULT_PORT)
            print(f"Invalid port: {port_str}, using default: {DEFAULT_PORT}")

    logger.debug("api_port_configured", port=DEFAULT_PORT, from_env=False)
    return DEFAULT_PORT