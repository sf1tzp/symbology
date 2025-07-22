"""FastAPI application for Symbology API."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import JSONResponse
from src.database.base import init_db
from src.utils.config import settings
from src.utils.logging import configure_logging, get_logger, get_uvicorn_log_config
import uvicorn


def create_app() -> FastAPI:
    # Import routes after logging is configured
    from src.api.routes import api_router
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
        allow_origins=settings.symbology_api.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add exception handling middleware
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger = get_logger(__name__)
        logger.error("unhandled_exception",
                    error=str(exc),
                    error_type=type(exc).__name__,
                    path=request.url.path,
                    method=request.method)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

    # Include API routes
    app.include_router(api_router, prefix="/api")


    @app.get("/")
    async def root():
        """Root endpoint for API health check."""
        logger = get_logger(__name__)
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

    return app


def start_api():
    # Configure structured logging using settings
    configure_logging(
        log_level=settings.logging.level,
        json_format=settings.logging.json_format,
        configure_root_logger=True
    )
    logger = get_logger(__name__)

    # Initialize database connection
    init_db(settings.database.url)
    logger.debug("database_connection_initialized", host=settings.database.host, port=settings.database.port)

    app = create_app()

    if "*" in settings.symbology_api.allowed_origins:
        logger.warn("open_cors_policy")

    logger.info("allowed_origins", allowed_origins=settings.symbology_api.allowed_origins)
    logger.info("starting_api_server",
                env=settings.env,
                host=settings.symbology_api.host,
                port=settings.symbology_api.port
            )

    uvicorn.run(
        app,
        host=settings.symbology_api.host,
        port=settings.symbology_api.port,
        reload=(settings.env == "dev"),
        log_config=get_uvicorn_log_config(
            json_format=settings.logging.json_format
        )
    )
if __name__ == "__main__":
    start_api()