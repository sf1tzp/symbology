"""Database package for symbology ingestion.

This package contains database models and CRUD functions for all entities
used in the symbology system.
"""

# Import base database utilities
from src.database.base import Base, close_session, get_db, get_db_session, init_db

# Import models
# Import CRUD functions
# Companies
from src.database.companies import (
    Company,
    create_company,
    delete_company,
    get_company,
    get_company_ids,
    update_company,
)

# Completions
from src.database.completions import (
    Completion,
    create_completion,
    delete_completion,
    get_completion,
    get_completion_ids,
    update_completion,
)

# Documents
from src.database.documents import (
    create_document,
    delete_document,
    Document,
    get_document,
    get_document_ids,
    update_document,
)

# Filings
from src.database.filings import (
    create_filing,
    delete_filing,
    Filing,
    get_filing,
    get_filing_ids,
    update_filing,
)

# Financial Concepts
from src.database.financial_concepts import (
    create_financial_concept,
    delete_financial_concept,
    FinancialConcept,
    get_financial_concept,
    get_financial_concept_ids,
    update_financial_concept,
)

# Financial Values
from src.database.financial_values import (
    create_financial_value,
    delete_financial_value,
    FinancialValue,
    get_financial_value,
    get_financial_value_ids,
    update_financial_value,
)

# Prompts
from src.database.prompts import (
    create_prompt,
    delete_prompt,
    get_prompt,
    get_prompt_by_name,
    get_prompt_ids,
    Prompt,
    PromptRole,
    update_prompt,
)

# Ratings
from src.database.ratings import (
    create_rating,
    delete_rating,
    get_rating,
    get_rating_ids,
    Rating,
    update_rating,
)

__all__ = [
    # Base
    "Base", "init_db", "get_db_session", "get_db", "close_session",

    # Models
    "Company", "Filing", "Document", "FinancialConcept", "FinancialValue",
    "Completion", "Rating", "Prompt", "PromptRole",

    # Company functions
    "get_company_ids", "get_company", "create_company", "update_company", "delete_company",

    # Filing functions
    "get_filing_ids", "get_filing", "create_filing", "update_filing", "delete_filing",

    # Document functions
    "get_document_ids", "get_document", "create_document", "update_document", "delete_document",

    # Financial Concept functions
    "get_financial_concept_ids", "get_financial_concept", "create_financial_concept",
    "update_financial_concept", "delete_financial_concept",

    # Financial Value functions
    "get_financial_value_ids", "get_financial_value", "create_financial_value",
    "update_financial_value", "delete_financial_value",

    # Completion functions
    "get_completion_ids", "get_completion", "create_completion", "update_completion", "delete_completion",

    # Rating functions
    "get_rating_ids", "get_rating", "create_rating", "update_rating", "delete_rating",

    # Prompt functions
    "get_prompt_ids", "get_prompt", "create_prompt", "update_prompt", "delete_prompt",
]
