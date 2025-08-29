"""API route imports and configuration."""
from fastapi import APIRouter
from src.api.routes.companies import router as companies_router
from src.api.routes.documents import router as documents_router
from src.api.routes.filings import router as filings_router
from src.api.routes.generated_content import router as generated_content_router
from src.api.routes.model_configs import router as model_configs_router
from src.api.routes.prompts import router as prompts_router
from src.utils.logging import get_logger

# Create logger for this module
logger = get_logger(__name__)

# Main API router
api_router = APIRouter()

# Include routers
api_router.include_router(companies_router, prefix="/companies", tags=["companies"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(filings_router, prefix="/filings", tags=["filings"])
api_router.include_router(prompts_router, prefix="/prompts", tags=["prompts"])
api_router.include_router(generated_content_router, prefix="/generated-content", tags=["generated-content"])
api_router.include_router(model_configs_router, prefix="/model-configs", tags=["model-configs"])

logger.info("api_routes_configured",
           endpoints=[
               "/companies",
               "/documents",
               "/filings",
               "/prompts",
               "/generated-content",
               "/model-configs",
           ])