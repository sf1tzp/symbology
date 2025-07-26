"""Logging routes for client-side error tracking."""
import logging
from typing import Dict

from fastapi import APIRouter
from pydantic import BaseModel
from src.utils.logging import get_logger

router = APIRouter(prefix="/logs", tags=["logging"])
logger = get_logger(__name__)


class LogRequest(BaseModel):
    """Request model for client-side logging."""
    timestamp: str
    level: str
    component: str
    event: str
    user_agent: str


@router.post("/log")
async def log_client_message(request: LogRequest) -> Dict[str, str]:
    """
    Log client-side messages for monitoring and debugging.

    This endpoint allows the frontend to send logs to the backend
    for centralized logging and monitoring.
    """
    try:
        # Map client log levels to Python logging levels
        level_mapping = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warn": logging.WARNING,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
            "fatal": logging.CRITICAL,
        }

        # Get the appropriate log level, default to ERROR for unknown levels
        log_level = level_mapping.get(request.level.lower(), logging.ERROR)

        # Log at the appropriate level with additional context
        logger.log(
            log_level,
            request.event,
            user_agent=request.user_agent,
            client_event=request.event,
            component=request.component,
        )

        return {"status": "logged"}

    except Exception as e:
        # Don't let logging errors break the endpoint
        logger.error("log_client_message_failed", error=e)
        return {"status": "error", "message": "Failed to log error"}
