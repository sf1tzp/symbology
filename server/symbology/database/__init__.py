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
)

# Workers (first-class, self-heartbeating registry)
from symbology.database.workers import (
    heartbeat_worker,
    list_live_workers,
    mark_worker_stopped,
    reap_dead_workers,
    register_worker,
    Worker,
    WorkerStatus,
)

from symbology.database.generated_content import (
    ContentSourceType,
    create_generated_content,
    delete_generated_content,
    GeneratedContent,
    get_company_group_analysis,
    get_generated_content,
    get_generated_content_by_company_and_ticker,
    get_generated_content_by_hash,
    get_generated_content_by_source_content,
    get_generated_content_by_source_document,
    get_recent_generated_content_by_ticker,
    update_generated_content,
)

# Page content (publishing layer)
from symbology.database.page_content import (
    CompanyPageContent,
    CompanyPageContentChangeReport,
    DocumentPageContent,
    FilingPageContent,
    get_current_company_page_content,
    get_current_document_page_content,
    get_current_filing_page_content,
    get_current_group_page_content,
    GroupPageContent,
)

# Chunk models (vector embeddings)
from symbology.database.document_chunks import (
    delete_chunks_for_document,
    DocumentChunk,
    get_chunks_by_document,
    get_chunks_by_topic,
    get_chunks_for_company_doctype,
    replace_document_chunks,
    replace_document_section_chunks,
    search_document_chunks,
)
from symbology.database.generated_content_chunks import (
    delete_chunks_for_content,
    GeneratedContentChunk,
    get_chunks_by_content,
    replace_content_chunks,
    search_content_chunks,
)

# Chunk topics (stable cross-filing identity)
from symbology.database.chunk_topics import (
    add_member_to_topic,
    ChunkTopic,
    create_chunk_topic,
    delete_topics_for_scope,
    get_topics_for_scope,
    nearest_topic,
)

# Section diffs (precomputed year-over-year diffs)
from symbology.database.section_diffs import (
    ChangeKind,
    delete_diff_sets_for_pair,
    DiffSet,
    get_current_diff_set,
    SectionDiff,
)

# Company Groups
from symbology.database.company_groups import (
    add_company_to_group,
    CompanyGroup,
    company_group_membership,
    create_company_group,
    get_company_group_by_slug,
    list_company_groups,
    populate_group_from_sic_codes,
    remove_company_from_group,
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
    "Worker", "WorkerStatus",
    "DocumentChunk", "GeneratedContentChunk", "ChunkTopic",

    # Page content (publishing layer)
    "DocumentPageContent", "FilingPageContent", "CompanyPageContent",
    "CompanyPageContentChangeReport", "GroupPageContent",
    "get_current_document_page_content", "get_current_filing_page_content",
    "get_current_company_page_content", "get_current_group_page_content",

    # Chunk functions
    "get_chunks_by_document", "delete_chunks_for_document", "replace_document_chunks", "search_document_chunks",
    "get_chunks_for_company_doctype", "get_chunks_by_topic", "replace_document_section_chunks",
    "get_chunks_by_content", "delete_chunks_for_content", "replace_content_chunks", "search_content_chunks",

    # Chunk topic functions
    "get_topics_for_scope", "nearest_topic", "create_chunk_topic", "add_member_to_topic",
    "delete_topics_for_scope",

    # Section diff models + functions
    "DiffSet", "SectionDiff", "ChangeKind",
    "get_current_diff_set", "delete_diff_sets_for_pair",

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
    "claim_next_job", "complete_job", "fail_job",

    # Worker functions
    "register_worker", "heartbeat_worker", "mark_worker_stopped",
    "reap_dead_workers", "list_live_workers",
]
