# Import from the new database module
from database import (
    close_session,
    Company,
    create_company,
    Filing,
    get_company_by_cik,
    init_db,
    upsert_company,
)

# Import ingestion components
from .edgar import EdgarClient
from .ingestion import ingest_companies

__all__ = [
    # Re-export database components
    "init_db",
    "close_session",
    "Company",
    "Filing",
    "create_company",
    "get_company_by_cik",
    "upsert_company",

    # Ingestion components
    "EdgarClient",
    "ingest_companies",
]
