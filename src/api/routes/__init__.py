"""API route imports and configuration."""
from fastapi import APIRouter

from src.api.routes.companies import router as companies_router
from src.api.routes.completions import router as completions_router
from src.api.routes.documents import router as documents_router
from src.api.routes.filings import router as filings_router
from src.api.routes.prompts import router as prompts_router
from src.utils.logging import get_logger

# Create logger for this module
logger = get_logger(__name__)

# Main API router
api_router = APIRouter()

# Include routers
api_router.include_router(companies_router, prefix="/companies", tags=["companies"])
api_router.include_router(filings_router, prefix="/filings", tags=["filings"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(prompts_router, prefix="/prompts", tags=["prompts"])
api_router.include_router(completions_router, prefix="/completions", tags=["completions"])

logger.info("api_routes_configured",
           endpoints=[
               "/companies",
               "/filings",
               "/documents",
               "/prompts",
               "/completions",
           ])