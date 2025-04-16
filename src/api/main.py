"""FastAPI application for Symbology API."""
import logging
import os
import uvicorn

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from src.api.config import get_api_host, get_api_port
from src.api.routes import router as api_router
from src.database.base import get_db, init_db
from src.utils.logging import configure_logging, get_logger
from src.ingestion.config import settings

# Configure structured logging
configure_logging(log_level="INFO")
logger = get_logger(__name__)

# Initialize database connection
database_url = settings.database.url
init_db(database_url)
logger.info("database_connection_initialized", database_url=database_url)

# Create FastAPI application
app = FastAPI(
    title="Symbology API",
    description="REST API for accessing financial data and AI-generated insights",
    version="0.2.0",
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


def start_api():
    """Start the FastAPI application using uvicorn."""
    host = get_api_host()
    port = get_api_port()

    logger.info("starting_api_server", host=host, port=port)
    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=True,
    )


if __name__ == "__main__":
    start_api()