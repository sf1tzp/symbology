"""Job handler registry.

Handlers are registered with @register_handler(JobType.X) and looked up by
the worker loop at execution time.
"""
import time
from typing import Any, Callable, Dict, Optional

from symbology.database.jobs import JobType
from symbology.utils.logging import get_logger

logger = get_logger(__name__)

# handler signature: (params: dict) -> Optional[dict]
HandlerFn = Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]
_registry: Dict[JobType, HandlerFn] = {}


def register_handler(job_type: JobType):
    """Decorator to register a handler function for a job type."""
    def decorator(fn: HandlerFn) -> HandlerFn:
        _registry[job_type] = fn
        logger.debug("registered_handler", job_type=job_type.value, handler=fn.__name__)
        return fn
    return decorator


def get_handler(job_type: JobType) -> Optional[HandlerFn]:
    """Look up the handler for a given job type."""
    return _registry.get(job_type)


def list_handlers() -> Dict[JobType, str]:
    """Return a mapping of job type -> handler function name."""
    return {jt: fn.__name__ for jt, fn in _registry.items()}


# ---------------------------------------------------------------------------
# Built-in stub handler for testing
# ---------------------------------------------------------------------------

@register_handler(JobType.TEST)
def handle_test(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Simple test handler — sleeps for the requested duration and echoes params."""
    sleep_seconds = params.get("sleep", 0)
    if sleep_seconds:
        time.sleep(sleep_seconds)
    return {"echo": params, "status": "ok"}


# ---------------------------------------------------------------------------
# Real handlers
# ---------------------------------------------------------------------------

@register_handler(JobType.COMPANY_INGESTION)
def handle_company_ingestion(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Ingest a company from EDGAR.

    params:
        ticker (str, required): Company ticker symbol.
    """
    from symbology.ingestion.edgar_db.accessors import edgar_login
    from symbology.ingestion.ingestion_helpers import ingest_company
    from symbology.utils.config import settings

    ticker = params["ticker"]
    logger.info("handler_company_ingestion_start", ticker=ticker)
    edgar_login(settings.edgar_api.edgar_contact)
    edgar_company, db_id = ingest_company(ticker)
    logger.info("handler_company_ingestion_done", ticker=ticker, db_id=str(db_id))
    return {"ticker": ticker, "company_id": str(db_id), "name": edgar_company.name}


@register_handler(JobType.FILING_INGESTION)
def handle_filing_ingestion(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Ingest filings for a company.

    params:
        company_id (str, required): UUID of the company in the database.
        ticker (str, required): Company ticker symbol.
        form (str): Filing form type, default "10-K".
        count (int): Number of filings to retrieve, default 5.
        include_documents (bool): Whether to ingest documents, default True.
    """
    from symbology.ingestion.edgar_db.accessors import edgar_login
    from symbology.ingestion.ingestion_helpers import ingest_filings
    from symbology.utils.config import settings

    company_id = params["company_id"]
    ticker = params["ticker"]
    form = params.get("form", "10-K")
    count = params.get("count", 5)
    include_documents = params.get("include_documents", True)

    logger.info("handler_filing_ingestion_start", ticker=ticker, form=form, count=count)
    edgar_login(settings.edgar_api.edgar_contact)
    results = ingest_filings(company_id, ticker, form, count, include_documents)
    filing_ids = [str(r[3]) for r in results]
    logger.info("handler_filing_ingestion_done", ticker=ticker, filings_count=len(filing_ids))
    return {"ticker": ticker, "form": form, "filing_ids": filing_ids}


@register_handler(JobType.CONTENT_GENERATION)
def handle_content_generation(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generate content using LLM.

    params:
        system_prompt_hash (str, required): Hash of the system prompt.
        model_config_hash (str, required): Hash of the model config.
        source_document_hashes (list[str]): Hashes of source documents.
        source_content_hashes (list[str]): Hashes of source generated content.
        company_ticker (str, optional): Company ticker.
        description (str, optional): Description of the content.
    """
    from symbology.database.base import get_db_session
    from symbology.database.companies import get_company_by_ticker
    from symbology.database.documents import Document
    from symbology.database.generated_content import (
        GeneratedContent,
        create_generated_content,
        get_generated_content_by_hash,
    )
    from symbology.database.model_configs import get_model_config_by_name
    from symbology.database.prompts import Prompt, create_prompt
    from symbology.llm.client import get_generate_response
    from symbology.llm.prompts import format_user_prompt_content

    system_prompt_hash = params["system_prompt_hash"]
    model_config_hash = params["model_config_hash"]
    source_doc_hashes = params.get("source_document_hashes", [])
    source_content_hashes = params.get("source_content_hashes", [])
    company_ticker = params.get("company_ticker")
    description = params.get("description")

    session = get_db_session()

    # Resolve system prompt
    system_prompt = session.query(Prompt).filter(Prompt.content_hash == system_prompt_hash).first()
    if not system_prompt:
        raise ValueError(f"System prompt not found: {system_prompt_hash}")

    # Resolve model config
    from symbology.database.model_configs import ModelConfig
    model_config = session.query(ModelConfig).filter(ModelConfig.id == model_config_hash).first()
    if not model_config:
        raise ValueError(f"Model config not found: {model_config_hash}")

    # Resolve source documents
    source_documents = []
    for doc_hash in source_doc_hashes:
        doc = session.query(Document).filter(Document.content_hash == doc_hash).first()
        if doc:
            source_documents.append(doc)

    # Resolve source content
    source_content = []
    for content_hash in source_content_hashes:
        content = get_generated_content_by_hash(content_hash)
        if content:
            source_content.append(content)

    # Build user prompt
    user_prompt_text = format_user_prompt_content(
        source_documents=source_documents or None,
        source_content=source_content or None,
    )

    # Call LLM
    logger.info("handler_content_generation_start", description=description)
    response, warning = get_generate_response(model_config, system_prompt.content, user_prompt_text)

    # Resolve company
    company_id = None
    if company_ticker:
        company = get_company_by_ticker(company_ticker)
        if company:
            company_id = company.id

    # Save generated content
    content_data = {
        "content": response.content,
        "summary": None,
        "company_id": company_id,
        "description": description,
        "source_type": "documents" if source_documents else "generated_content",
        "model_config_id": model_config.id,
        "system_prompt_id": system_prompt.id,
        "total_duration": response.total_duration,
        "warning": warning,
    }
    generated, was_created = create_generated_content(content_data)
    if source_documents:
        generated.source_documents = source_documents
    if source_content:
        generated.source_content = source_content
    session.commit()

    logger.info("handler_content_generation_done", content_id=str(generated.id))
    return {"content_id": str(generated.id), "was_created": was_created}


@register_handler(JobType.INGEST_PIPELINE)
def handle_ingest_pipeline(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Full ingestion pipeline: company -> filings -> (optional content generation).

    params:
        ticker (str, required): Company ticker symbol.
        form (str): Filing form type, default "10-K".
        count (int): Number of filings, default 5.
        include_documents (bool): Ingest documents, default True.
    """
    ticker = params["ticker"]
    form = params.get("form", "10-K")
    count = params.get("count", 5)
    include_documents = params.get("include_documents", True)

    logger.info("handler_ingest_pipeline_start", ticker=ticker)

    # Step 1: Company
    company_result = handle_company_ingestion({"ticker": ticker})
    company_id = company_result["company_id"]

    # Step 2: Filings
    filing_result = handle_filing_ingestion({
        "company_id": company_id,
        "ticker": ticker,
        "form": form,
        "count": count,
        "include_documents": include_documents,
    })

    logger.info("handler_ingest_pipeline_done", ticker=ticker)
    return {
        "ticker": ticker,
        "company_id": company_id,
        "filings": filing_result["filing_ids"],
    }
