"""
Logging configuration for the Symbology project.

This module provides a consistent logging setup using structlog for
structured logging throughout the application.

Usage:
    # Configure logging using application settings
    from src.ingestion.config import settings
    from src.utils.logging import configure_logging

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
from typing import List, Optional

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
                        log_file: Path = 'outputs/symbology.log',
                        json_format: bool = False,
                        extra_processors: Optional[List[Processor]] = None) -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: The log level to use (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to output logs in JSON format (useful for production)
        extra_processors: Additional structlog processors to add to the chain

    Examples:
        # Configure basic logging
        configure_logging(log_level="INFO")

        # Configure JSON logging for production environments
        configure_logging(log_level="WARNING", json_format=True)
    """
    # Set the log level for the standard library's logging
    log_level_int = getattr(logging, log_level)

    logging.basicConfig(
        format="%(message)s",
        level=log_level_int,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, mode="a"),
        ],
    )

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
    return structlog.get_logger(name)

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