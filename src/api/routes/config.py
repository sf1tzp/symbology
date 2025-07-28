"""Configuration endpoints for the frontend application."""
import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from src.utils.config import settings

router = APIRouter()


@router.get("/config")
async def get_frontend_config(request: Request):
    """
    Get frontend configuration based on current environment.

    This endpoint provides environment-specific configuration
    to the frontend application at runtime.
    """
    # Determine the correct API base URL for the frontend
    # Use the actual hostname that the client is connecting to
    client_host = request.client.host if request.client else "localhost"

    # In staging/production, use the actual server's IP/hostname
    # Check if we have a public host override (for staging environments)
    api_host = os.getenv("SYMBOLOGY_API_PUBLIC_HOST") or request.url.hostname or client_host
    api_port = settings.symbology_api.port #noqa: F841

    scheme = 'https' if os.getenv("ENVIRONMENT", "production") != "development" else 'http'
    port_number = '' if os.getenv("ENVIRONMENT", "production") != "development" else f':{os.getenv("SYMBOLOGY_API_PORT", "8000")}'
    base_url = f'{scheme}://{api_host}{port_number}/api'

    config = {
        "environment": os.getenv("ENVIRONMENT", "production"),
        "logging": {
            "level": os.getenv("LOG_LEVEL", "INFO"),
            "jsonFormat": os.getenv("LOG_JSON_FORMAT", "false").lower() == "true",
            "enableBackendLogging": os.getenv("ENVIRONMENT", "production") in ["development", "staging"]
        },
        "api": {
            "baseUrl": base_url,
            "timeout": 30000
        },
        "features": {
            "enableAnalytics": os.getenv("ENABLE_ANALYTICS", "false").lower() == "true",
            "enableDebugMode": os.getenv("ENVIRONMENT", "production") == "development"
        }
    }

    return JSONResponse(
        content=config,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )
