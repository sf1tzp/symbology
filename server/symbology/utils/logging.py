"""
Logging configuration for the Symbology project.

This module provides a consistent logging setup using structlog for
structured logging throughout the application.

Usage:
    # Configure logging using application settings
    from symbology.ingestion.config import settings
    from symbology.utils.logging import configure_logging

    configure_logging(
        log_level=settings.logging.level,
        json_format=settings.logging.json_format
    )

    # Get a logger
    logger = get_logger(__name__)
    logger.info("application_started", version="1.0.0")
"""
import logging
from pathlib import Path
import sys
import traceback
from typing import Dict, List, Optional

import structlog
from structlog.types import Processor


def format_clickable_callsite(logger, method_name, event_dict):
    """
    Format callsite information into clickable file paths.

    Gets the full file path from stack inspection and formats it as
    "src/path/to/file.py:line_number" for terminal clickability.
    """
    import inspect

    # Get the repo root
    repo_root = Path(__file__).parent.parent.parent

    try:
        # Find the calling frame (skip structlog internal frames)
        frame = inspect.currentframe()
        while frame:
            frame_filename = frame.f_code.co_filename
            frame_path = Path(frame_filename)

            # Skip frames that are in structlog or our logging module
            if ('structlog' not in str(frame_path) and
                'logging.py' not in frame_path.name and
                '__pycache__' not in str(frame_path)):

                # This should be the actual calling code
                try:
                    relative_path = frame_path.relative_to(repo_root)
                    lineno = frame.f_lineno
                    clickable_location = f'"{relative_path}:{lineno}"'
                    event_dict["caller"] = clickable_location

                    # Remove any existing filename/lineno that might have been added by CallsiteParameterAdder
                    event_dict.pop("filename", None)
                    event_dict.pop("lineno", None)
                    break
                except ValueError:
                    # If the file is not under repo_root, use absolute path
                    event_dict["caller"] = f'"{frame_path}:{frame.f_lineno}"'
                    event_dict.pop("filename", None)
                    event_dict.pop("lineno", None)
                    break

            frame = frame.f_back
    except Exception:
        # Fallback: use existing filename/lineno if available
        filename = event_dict.get("filename")
        lineno = event_dict.get("lineno")
        if filename and lineno:
            # Add ./ prefix if it's not already an absolute path
            if not filename.startswith('/'):
                event_dict["caller"] = f'"{filename}:{lineno}"'
            else:
                event_dict["caller"] = f'"{filename}:{lineno}"'
            event_dict.pop("filename", None)
            event_dict.pop("lineno", None)
    finally:
        del frame

    # Also rename func_name to function
    if "func_name" in event_dict:
        event_dict["function"] = event_dict.pop("func_name")

    return event_dict

def configure_logging(log_level: str = "INFO",
                        json_format: bool = False,
                        extra_processors: Optional[List[Processor]] = None,
                        configure_root_logger: bool = True) -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: The log level to use (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to output logs in JSON format (useful for production)
        extra_processors: Additional structlog processors to add to the chain
        configure_root_logger: Whether to configure the root logger (set False when using custom uvicorn config)

    Examples:
        # Configure basic logging
        configure_logging(log_level="INFO")

        # Configure JSON logging for production environments
        configure_logging(log_level="WARNING", json_format=True)

        # Configure without root logger (for uvicorn integration)
        configure_logging(log_level="INFO", configure_root_logger=False)
    """
    # Set the log level for the standard library's logging
    log_level_int = getattr(logging, log_level)

    if configure_root_logger:
        logging.basicConfig(
            format="%(message)s",
            level=log_level_int,
            handlers=[
                logging.StreamHandler(sys.stdout),
            ],
        )
    else:
        # Configure a minimal setup for structlog without interfering with uvicorn
        # Create a logger specifically for our application
        app_logger = logging.getLogger("symbology")
        app_logger.setLevel(log_level_int)

        # Only add handlers if they don't already exist
        if not app_logger.handlers:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(logging.Formatter("%(message)s"))

            app_logger.addHandler(console_handler)
            app_logger.propagate = False  # Don't propagate to root logger

    # Define processors for structlog
    processors: List[Processor] = [
        # Add timestamps to logs
        structlog.processors.TimeStamper(fmt="iso"),
        # Add log level as string
        structlog.processors.add_log_level,
        # Add callsite parameters.
        structlog.processors.CallsiteParameterAdder(
            {
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            }
        ),
        # Format callsite into clickable location
        format_clickable_callsite,
        # Add logger name
        structlog.processors.StackInfoRenderer(),
        # Add extra context from the logging call
        structlog.contextvars.merge_contextvars,
        # Format exceptions
        structlog.processors.format_exc_info,
    ]

    # Add any extra processors
    if extra_processors:
        processors.extend(extra_processors)

    # Add formatters based on output preference
    if json_format:
        # For production: structured JSON logs
        processors.append(structlog.processors.JSONRenderer())
    else:
        # For development: colored, human-readable logs
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=sys.stdout.isatty(),  # Colors only if running in a real terminal
                exception_formatter=structlog.dev.plain_traceback,
            )
        )

    # Configure structlog with our processors
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Pass log level from standard logging to structlog
        wrapper_class=structlog.stdlib.BoundLogger,
        # Cache logger instances for performance
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger with the given name.

    Args:
        name: The name of the logger, usually __name__

    Returns:
        A structured logger instance
    """
    logger = structlog.get_logger(name)

    # If this is an application logger (starts with 'symbology.'), disable propagation
    # to prevent double logging when using uvicorn, but ensure it has handlers
    if name.startswith('symbology.'):
        stdlib_logger = logging.getLogger(name)
        stdlib_logger.propagate = False

        # Ensure it has handlers - either copy from symbology app logger or add directly
        if not stdlib_logger.handlers:
            app_logger = logging.getLogger("symbology")
            if app_logger.handlers:
                # Copy handlers from the symbology app logger
                for handler in app_logger.handlers:
                    stdlib_logger.addHandler(handler)
            else:
                # Fallback: add console handler directly
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(logging.Formatter("%(message)s"))
                stdlib_logger.addHandler(console_handler)

        # Set the log level to match the app logger or a reasonable default
        app_logger = logging.getLogger("symbology")
        if app_logger.level != logging.NOTSET:
            stdlib_logger.setLevel(app_logger.level)
        else:
            stdlib_logger.setLevel(logging.INFO)

    return logger

def log_exception(e: Exception, logger: structlog.stdlib.BoundLogger, prefix: str = "") -> str:
    """
    Log an exception with full traceback information and return formatted error message.

    Args:
        e: The exception object
        logger: The structlog logger to use for logging
        prefix: Optional prefix for the log message

    Returns:
        Formatted error message with traceback information
    """
    exc_type, exc_value, exc_traceback = sys.exc_info()

    # Get the stack trace as a list of strings
    stack_trace = traceback.format_exception(exc_type, exc_value, exc_traceback)

    # Extract the line where the error occurred
    error_lines = [line for line in stack_trace if 'File "' in line]
    error_location = error_lines[-1].strip() if error_lines else "Unknown location"

    # Format the error message
    error_msg = f"{prefix}{str(e)} at {error_location}"

    # Log with structlog (includes traceback automatically)
    logger.error("exception_occurred",
                 error=str(e),
                 error_location=error_location,
                 exc_info=True)

    return error_msg


class StructuredUvicornFormatter(logging.Formatter):
    """Custom formatter for uvicorn logs to match our structured logging format."""

    def __init__(self, json_format: bool = False, use_colors: bool = False):
        super().__init__()
        self.json_format = json_format
        self.use_colors = use_colors

        # Color codes for console output
        self.colors = {
            'debug': '\033[36m',     # cyan
            'info': '\033[32m',      # green
            'warning': '\033[33m',   # yellow
            'error': '\033[31m',     # red
            'critical': '\033[35m',  # magenta
            'reset': '\033[0m'       # reset
        } if use_colors else {}

    def format(self, record):
        # Convert log level to lowercase
        level = record.levelname.lower()

        if self.json_format:
            # JSON format for production
            import datetime
            import json
            dt = datetime.datetime.fromtimestamp(record.created, tz=datetime.timezone.utc)
            timestamp = dt.isoformat().replace('+00:00', 'Z')

            log_data = {
                "timestamp": timestamp,
                "level": level,
                "logger": record.name,
                "message": record.getMessage()
            }
            return json.dumps(log_data)
        else:
            # Console format (matches structlog dev format)
            import datetime
            dt = datetime.datetime.fromtimestamp(record.created, tz=datetime.timezone.utc)
            timestamp = dt.isoformat().replace('+00:00', 'Z')

            # Apply colors if enabled
            if self.use_colors and level in self.colors:
                level_colored = f"{self.colors[level]}{level:<9s}{self.colors['reset']}"
            else:
                level_colored = f"{level:<9s}"

            formatted = f"{timestamp} [{level_colored}] {record.name}: {record.getMessage()}"
            return formatted


def get_uvicorn_log_config(json_format: bool = False) -> Dict:
    """
    Get a log configuration dict for uvicorn that uses our structured logging.

    Args:
        json_format: Whether to output logs in JSON format (matches main logging config)
        log_file: Optional log file path for file logging

    Returns:
        Dict: Log configuration for uvicorn that integrates with our structured logging
    """
    import sys

    # Detect if we're in a TTY for color support
    use_colors = sys.stdout.isatty() and not json_format

    handlers = {
        "console": {
            "formatter": "structured",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    }

    handler_list = ["console"]

    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "()": StructuredUvicornFormatter,
                "json_format": json_format,
                "use_colors": use_colors,
            },
        },
        "handlers": handlers,
        "root": {
            "level": "INFO",
            "handlers": handler_list,
        },
        "loggers": {
            "uvicorn": {
                "level": "INFO",
                "handlers": handler_list,
                "propagate": False,
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": handler_list,
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": handler_list,
                "propagate": False,
            },
        },
    }

    return log_config