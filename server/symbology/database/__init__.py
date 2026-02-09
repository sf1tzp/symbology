"""Database package for symbology ingestion.

This package contains database models and CRUD functions for all entities
used in the symbology system.
"""

from symbology.database.base import Base, close_session, get_db, get_db_session, init_db

# Companies
from symbology.database.companies import (
    Company,
    create_company,
    delete_company,
    get_company,
    get_company_ids,
    update_company,
)

# Documents
from symbology.database.documents import (
    create_document,
    delete_document,
    Document,
    get_document,
    get_document_ids,
    update_document,
)

# Filings
from symbology.database.filings import (
    create_filing,
    delete_filing,
    Filing,
    get_filing,
    get_filing_ids,
    update_filing,
)

# Financial Concepts
from symbology.database.financial_concepts import (
    create_financial_concept,
    delete_financial_concept,
    FinancialConcept,
    get_financial_concept,
    get_financial_concept_ids,
    update_financial_concept,
)

# Financial Values
from symbology.database.financial_values import (
    create_financial_value,
    delete_financial_value,
    FinancialValue,
    get_financial_value,
    get_financial_value_ids,
    update_financial_value,
)
# Jobs
from symbology.database.jobs import (
    cancel_job,
    claim_next_job,
    complete_job,
    create_job,
    fail_job,
    get_job,
    Job,
    JobStatus,
    JobType,
    list_jobs,
    mark_stale_jobs_as_failed,
)

# Pipeline Runs
from symbology.database.pipeline_runs import (
    complete_pipeline_run,
    count_consecutive_failures,
    create_pipeline_run,
    fail_pipeline_run,
    get_latest_run_per_company,
    get_pipeline_run,
    list_pipeline_runs,
    PipelineRun,
    PipelineRunStatus,
    PipelineTrigger,
    start_pipeline_run,
)

from symbology.database.generated_content import (
    ContentSourceType,
    create_generated_content,
    delete_generated_content,
    GeneratedContent,
    get_generated_content,
    get_generated_content_by_company_and_ticker,
    get_generated_content_by_hash,
    get_generated_content_by_source_content,
    get_generated_content_by_source_document,
    get_recent_generated_content_by_ticker,
    update_generated_content,
)

# New consolidated models
from symbology.database.model_configs import (
    create_model_config,
    delete_model_config,
    get_all_model_configs,
    get_model_config,
    get_model_config_by_name,
    get_model_config_ids,
    ModelConfig,
    update_model_config,
)

# Prompts
from symbology.database.prompts import create_prompt, delete_prompt, get_prompt, get_prompt_ids, Prompt, PromptRole

# Ratings
from symbology.database.ratings import (
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
    "Completion", "Aggregate", "Rating", "Prompt", "PromptRole",
    "Job", "JobStatus", "JobType",
    "PipelineRun", "PipelineRunStatus", "PipelineTrigger",

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

    # Rating functions
    "get_rating_ids", "get_rating", "create_rating", "update_rating", "delete_rating",

    # Prompt functions
    "get_prompt_ids", "get_prompt", "create_prompt", "update_prompt", "delete_prompt",

    # Job functions
    "create_job", "get_job", "list_jobs", "cancel_job",
    "claim_next_job", "complete_job", "fail_job", "mark_stale_jobs_as_failed",

    # Pipeline Run functions
    "create_pipeline_run", "get_pipeline_run", "list_pipeline_runs",
    "start_pipeline_run", "complete_pipeline_run", "fail_pipeline_run",
    "get_latest_run_per_company", "count_consecutive_failures",
]
