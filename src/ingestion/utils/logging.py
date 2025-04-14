"""
Logging configuration for the Symbology project.

This module provides a consistent logging setup using structlog for
structured logging throughout the application.
"""
import logging
import sys
import traceback
from typing import List, Optional

import structlog
from structlog.types import Processor


def configure_logging(log_level: str = "INFO",
                      json_format: bool = False,
                      extra_processors: Optional[List[Processor]] = None) -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: The log level to use (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to output logs in JSON format (useful for production)
        extra_processors: Additional structlog processors to add to the chain
    """
    # Set the log level for the standard library's logging
    log_level_int = getattr(logging, log_level)
    logging.basicConfig(
        format="%(message)s",
        level=log_level_int,
    )

    # Define processors for structlog
    processors: List[Processor] = [
        # Add timestamps to logs
        structlog.processors.TimeStamper(fmt="iso"),
        # Add log level as string
        structlog.processors.add_log_level,
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