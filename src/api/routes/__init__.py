"""API routes configuration."""
from fastapi import APIRouter

from src.ingestion.utils.logging import get_logger

# Create logger for this module
logger = get_logger(__name__)

# Import individual route modules
from src.api.routes import (
    companies,
    filings,
    financial_statements,
    llm_completions,
)

# Create main router
router = APIRouter()

# Include all sub-routers
router.include_router(companies.router, prefix="/companies", tags=["companies"])
router.include_router(filings.router, prefix="/filings", tags=["filings"])
router.include_router(financial_statements.router, prefix="/financials", tags=["financials"])
router.include_router(llm_completions.router, prefix="/completions", tags=["completions"])

logger.info("api_routes_configured",
           endpoints=[
               "/companies",
               "/filings",
               "/financials",
               "/completions"
           ])