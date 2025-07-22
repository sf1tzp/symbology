"""FastAPI application for Symbology API."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from src.api.routes import api_router
from src.database.base import init_db
from src.utils.config import settings
from src.utils.logging import configure_logging, get_logger
import uvicorn

# Configure structured logging
configure_logging(log_level="INFO", log_file=Path('outputs/symbology-api.log'))
logger = get_logger(__name__)

# Initialize database connection
init_db(settings.database.url)
logger.info("database_connection_initialized", host=settings.database.host, port=settings.database.port)

# Create FastAPI application
app = FastAPI(
    title="Symbology API",
    description="REST API for accessing financial data and AI-generated insights",
    version="0.2.0",
    docs_url=None,  # Disable default docs to customize
    redoc_url=None,  # Disable default redoc to customize
    openapi_tags=[
        {
            "name": "companies",
            "description": "Operations related to company information and search",
        },
        {
            "name": "documents",
            "description": "Operations related to filing documents and content",
        },
        {
            "name": "completions",
            "description": "Operations related to AI-generated completions",
        },
        {
            "name": "aggregates",
            "description": "Operations related to AI-generated aggregates",
        },
        {
            "name": "prompts",
            "description": "Operations related to prompt templates and management",
        },
    ],
    contact={
        "name": "Symbology Team",
        "url": "https://github.com/yourusername/symbology",  # Update with your repo
    },
    license_info={
        "name": "Private",
    },
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include API routes
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint for API health check."""
    logger.info("health_check_requested")
    return {"status": "online", "message": "Symbology API is running"}


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Custom Swagger UI with a better theme."""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - API Documentation",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_favicon_url="/favicon.ico",
    )


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    """ReDoc API documentation."""
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )


def start_api():
    """Start the FastAPI application using uvicorn."""
    host = settings.symbology_api.host
    port = settings.symbology_api.port

    logger.info("starting_api_server", host=host, port=port)
    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=True,
    )


if __name__ == "__main__":
    start_api()