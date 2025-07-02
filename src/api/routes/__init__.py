"""API route imports and configuration."""
from fastapi import APIRouter

from src.api.routes.aggregates import router as aggregates_router
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
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(completions_router, prefix="/completions", tags=["completions"])
api_router.include_router(aggregates_router, prefix="/aggregates", tags=["aggregates"])
api_router.include_router(filings_router, prefix="/filings", tags=["filings"])
api_router.include_router(prompts_router, prefix="/prompts", tags=["prompts"])

logger.info("api_routes_configured",
           endpoints=[
               "/companies",
               "/documents",
               "/completions",
               "/aggregates",
               "/filings",
               "/prompts"
           ])