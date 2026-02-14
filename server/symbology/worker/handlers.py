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
        create_generated_content,
        get_generated_content_by_hash,
    )
    from symbology.database.prompts import Prompt
    from symbology.llm.client import get_generate_response
    from symbology.llm.prompts import format_user_prompt_content

    system_prompt_hash = params["system_prompt_hash"]
    model_config_hash = params["model_config_hash"]
    source_doc_hashes = params.get("source_document_hashes", [])
    source_content_hashes = params.get("source_content_hashes", [])
    company_ticker = params.get("company_ticker")
    description = params.get("description")
    document_type_str = params.get("document_type")
    form_type = params.get("form_type")
    content_stage_str = params.get("content_stage")

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

    # Resolve structured metadata
    from symbology.database.documents import DocumentType
    from symbology.database.generated_content import ContentStage
    resolved_document_type = DocumentType(document_type_str) if document_type_str else None
    resolved_content_stage = ContentStage(content_stage_str) if content_stage_str else None

    # Save generated content
    content_data = {
        "content": response.response,
        "summary": None,
        "company_id": company_id,
        "description": description,
        "document_type": resolved_document_type,
        "form_type": form_type,
        "content_stage": resolved_content_stage,
        "source_type": "documents" if source_documents else "generated_content",
        "model_config_id": model_config.id,
        "system_prompt_id": system_prompt.id,
        "total_duration": response.total_duration,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "warning": warning,
    }
    generated, was_created = create_generated_content(content_data)
    if source_documents:
        generated.source_documents = source_documents
    if source_content:
        generated.source_content = source_content
    session.commit()

    logger.info("handler_content_generation_done", content_id=str(generated.id))
    return {
        "content_id": str(generated.id),
        "content_hash": generated.content_hash,
        "was_created": was_created,
    }


@register_handler(JobType.BULK_INGEST)
def handle_bulk_ingest(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Ingest a batch of filings without LLM processing.

    params:
        filings (list[dict], required): List of filing dicts, each with:
            - cik (str): Company CIK number
            - company_name (str): Company name from EDGAR
            - accession_number (str): Filing accession number
            - form (str): Form type (10-K, 10-Q, 8-K, etc.)
        include_documents (bool): Whether to ingest document sections (default True).
    """
    from symbology.ingestion.bulk_discovery import get_or_create_company_from_filing
    from symbology.ingestion.edgar_db.accessors import edgar_login
    from symbology.ingestion.ingestion_helpers import ingest_single_filing
    from symbology.utils.config import settings

    edgar_login(settings.edgar_api.edgar_contact)

    filings = params["filings"]
    include_documents = params.get("include_documents", True)
    ingested = 0
    skipped = 0
    failed = 0

    for filing_info in filings:
        accession = filing_info["accession_number"]
        try:
            company = get_or_create_company_from_filing(
                cik=filing_info["cik"],
                company_name=filing_info["company_name"],
            )
            filing_id = ingest_single_filing(
                company_id=company.id,
                accession_number=accession,
                include_documents=include_documents,
            )
            if filing_id:
                ingested += 1
            else:
                skipped += 1
        except Exception:
            failed += 1
            logger.exception("bulk_ingest_filing_failed", accession_number=accession)

    logger.info(
        "handle_bulk_ingest_done",
        ingested=ingested,
        skipped=skipped,
        failed=failed,
        total=len(filings),
    )
    return {"ingested": ingested, "skipped": skipped, "failed": failed}

@register_handler(JobType.COMPANY_GROUP_PIPELINE)
def handle_company_group_pipeline(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generate cross-company sector analysis from aggregate summaries.

    params:
        tickers (list[str], required): List of company ticker symbols.
        group_slug (str, optional): Company group slug to link result to.
        max_per_ticker (int, optional): Max aggregate summaries per ticker (default 3).
    """
    from symbology.database.base import get_db_session
    from symbology.database.company_groups import get_company_group_by_slug
    from symbology.database.generated_content import (
        create_generated_content,
        get_aggregate_summaries_by_ticker,
    )
    from symbology.llm.client import get_generate_response
    from symbology.llm.prompts import format_user_prompt_content
    from symbology.database.generated_content import ContentStage
    from symbology.worker.pipeline import (
        PIPELINE_MODEL_CONFIGS,
        PIPELINE_PROMPTS,
        ensure_model_config,
        ensure_prompt,
        generate_group_frontpage_summary,
    )

    tickers = params["tickers"]
    group_slug = params.get("group_slug")
    max_per_ticker = params.get("max_per_ticker", 3)

    logger.info("handler_company_group_pipeline_start", tickers=tickers, group_slug=group_slug)

    # Set up model config and prompt
    mc = ensure_model_config(**PIPELINE_MODEL_CONFIGS["company_group_analysis"])
    system_prompt = ensure_prompt(PIPELINE_PROMPTS["company_group_analysis"])

    # Gather aggregate summaries for each ticker
    all_sources = []
    for ticker in tickers:
        summaries = get_aggregate_summaries_by_ticker(ticker.upper(), limit=max_per_ticker)
        all_sources.extend(summaries)

    if not all_sources:
        raise ValueError(f"No aggregate summaries found for tickers: {tickers}")

    # Log warning if source content is large
    total_chars = sum(len(s.content or "") for s in all_sources)
    if total_chars > 200_000:
        logger.warning(
            "company_group_pipeline_large_input",
            total_chars=total_chars,
            source_count=len(all_sources),
        )

    # Resolve group if provided
    group = None
    group_info = ""
    if group_slug:
        group = get_company_group_by_slug(group_slug)
        if group:
            group_info = f"Group: {group.name}\nDescription: {group.description or 'N/A'}\nTickers: {', '.join(tickers)}"

    # Build user prompt
    user_prompt_text = format_user_prompt_content(
        source_content=all_sources,
        additional_text=group_info if group_info else f"Tickers: {', '.join(tickers)}",
    )

    # Call LLM
    response, warning = get_generate_response(mc, system_prompt.content, user_prompt_text)

    # Store result
    content_data = {
        "content": response.response,
        "summary": None,
        "company_id": None,
        "company_group_id": group.id if group else None,
        "description": "company_group_analysis",
        "content_stage": ContentStage.COMPANY_GROUP_ANALYSIS,
        "source_type": "generated_content",
        "model_config_id": mc.id,
        "system_prompt_id": system_prompt.id,
        "total_duration": response.total_duration,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "warning": warning,
    }
    generated, was_created = create_generated_content(content_data)

    # Link source content
    session = get_db_session()
    generated.source_content = all_sources
    session.commit()

    # Generate frontpage summary from the analysis
    frontpage_hash = None
    if generated.content_hash and group:
        mc_fp = ensure_model_config(**PIPELINE_MODEL_CONFIGS["company_group_frontpage"])
        fp_prompt = ensure_prompt(PIPELINE_PROMPTS["company_group_frontpage"])
        fp_hash, fp_ok = generate_group_frontpage_summary(
            company_group_id=str(group.id),
            analysis_hash=generated.content_hash,
            prompt=fp_prompt,
            model_config=mc_fp,
        )
        if fp_ok:
            frontpage_hash = fp_hash
            logger.info("handler_company_group_frontpage_done", frontpage_hash=fp_hash)
        else:
            logger.warning("handler_company_group_frontpage_failed", group_slug=group_slug)

    logger.info(
        "handler_company_group_pipeline_done",
        content_id=str(generated.id),
        tickers=tickers,
        sources_used=len(all_sources),
    )
    return {
        "content_id": str(generated.id),
        "content_hash": generated.content_hash,
        "frontpage_hash": frontpage_hash,
        "was_created": was_created,
        "tickers": tickers,
        "sources_used": len(all_sources),
    }


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


@register_handler(JobType.FULL_PIPELINE)
def handle_full_pipeline(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """End-to-end automated pipeline: company -> filings -> content generation.

    Orchestrates ingestion and 3-stage LLM content generation pipeline.
    For each form and document type it:
      1. Ingests the company and filings from EDGAR
      2. Generates single summaries per filing document
      3. Generates an aggregate summary from all singles
      4. Generates a frontpage summary from the aggregate

    params:
        ticker (str, required): Company ticker symbol.
        forms (list[str]): Form types to process. Defaults to ["10-K", "10-Q"].
        counts (dict[str, int]): Number of filings per form.
        document_types (dict[str, list[str]]): Document types per form.
        prompts_dir (str): Path to prompts directory.
        trigger (str): "manual" or "scheduled". Defaults to "manual".
        force (bool): If True, bypass dedup and regenerate all content.
    """
    from pathlib import Path
    from uuid import UUID

    from symbology.database.base import get_db_session
    from symbology.database.filings import Filing
    from symbology.database.pipeline_runs import (
        PipelineTrigger,
        complete_pipeline_run,
        create_pipeline_run,
        fail_pipeline_run,
        start_pipeline_run,
    )
    from symbology.worker.pipeline import (
        FORM_DOCUMENT_TYPES,
        PIPELINE_MODEL_CONFIGS,
        PIPELINE_PROMPTS,
        ensure_model_config,
        ensure_prompt,
        generate_aggregate_summary,
        generate_frontpage_summary,
        generate_single_summaries,
    )

    ticker = params["ticker"]
    forms = params.get("forms", ["10-K", "10-Q"])
    default_counts = {"10-K": 5, "10-Q": 6}
    counts = params.get("counts", default_counts)
    doc_types_map = params.get("document_types", FORM_DOCUMENT_TYPES)
    prompts_dir = Path(params["prompts_dir"]) if "prompts_dir" in params else None
    trigger_str = params.get("trigger", "manual")
    trigger = PipelineTrigger(trigger_str)
    force = params.get("force", False)

    logger.info("handler_full_pipeline_start", ticker=ticker, forms=forms, force=force)

    # Step 1: Company ingestion
    company_result = handle_company_ingestion({"ticker": ticker})
    company_id = company_result["company_id"]

    # Create pipeline run record
    pipeline_run = create_pipeline_run(
        company_id=company_id,
        forms=forms,
        trigger=trigger,
        run_metadata={"ticker": ticker, "counts": counts},
    )
    start_pipeline_run(pipeline_run.id)

    jobs_created = 0
    jobs_completed = 0
    jobs_failed = 0

    try:
        # Step 2: Set up model configs
        mc_single = ensure_model_config(**PIPELINE_MODEL_CONFIGS["single_summary"])
        mc_aggregate = ensure_model_config(**PIPELINE_MODEL_CONFIGS["aggregate_summary"])
        mc_frontpage = ensure_model_config(**PIPELINE_MODEL_CONFIGS["frontpage_summary"])

        # Step 3: Set up shared prompts
        aggregate_prompt = ensure_prompt(PIPELINE_PROMPTS["aggregate_summary"], prompts_dir)
        frontpage_prompt = ensure_prompt(PIPELINE_PROMPTS["frontpage_summary"], prompts_dir)

        total_content_generated = 0

        # Step 4: Process each form
        for form in forms:
            count = counts.get(form, default_counts.get(form, 5))
            doc_types = doc_types_map.get(form, [])

            if not doc_types:
                logger.info("full_pipeline_skip_form", form=form, reason="no document types")
                continue

            # Ingest filings for this form
            filing_result = handle_filing_ingestion({
                "company_id": company_id,
                "ticker": ticker,
                "form": form,
                "count": count,
                "include_documents": True,
            })
            logger.info(
                "full_pipeline_filings_ingested",
                form=form,
                filings_count=len(filing_result["filing_ids"]),
            )

            # Query filings from DB to get their documents
            session = get_db_session()
            filings = (
                session.query(Filing)
                .filter(Filing.company_id == UUID(company_id), Filing.form == form)
                .all()
            )

            # Step 5: For each document type, run the 3-stage content pipeline
            for doc_type_str in doc_types:
                single_prompt = ensure_prompt(doc_type_str, prompts_dir)

                # Stage 1: Single summaries
                hashes, new, reused, failed = generate_single_summaries(
                    company_id, ticker, form, doc_type_str,
                    filings, single_prompt, mc_single, force=force,
                )
                jobs_created += new + failed
                jobs_completed += new + reused
                jobs_failed += failed
                total_content_generated += new + reused

                if not hashes:
                    logger.info("full_pipeline_skip_aggregate", form=form,
                                doc_type=doc_type_str, reason="no single summaries")
                    continue

                if new == 0 and not force:
                    logger.info("full_pipeline_skip_aggregate", form=form,
                                doc_type=doc_type_str, reason="all single summaries already existed",
                                existing_count=len(hashes))
                    continue

                # Stage 2: Aggregate summary
                jobs_created += 1
                agg_hash, agg_ok = generate_aggregate_summary(
                    company_id, ticker, form, doc_type_str,
                    hashes, aggregate_prompt, mc_aggregate, force=force,
                )
                if agg_ok:
                    jobs_completed += 1
                    total_content_generated += 1

                    # Stage 3: Frontpage summary
                    jobs_created += 1
                    fp_hash, fp_ok = generate_frontpage_summary(
                        company_id, ticker, form, doc_type_str,
                        agg_hash, frontpage_prompt, mc_frontpage, force=force,
                    )
                    if fp_ok:
                        jobs_completed += 1
                        total_content_generated += 1
                    else:
                        jobs_failed += 1
                else:
                    jobs_failed += 1

        # Mark pipeline run as completed
        complete_pipeline_run(
            pipeline_run.id,
            jobs_created=jobs_created,
            jobs_completed=jobs_completed,
            jobs_failed=jobs_failed,
        )

        logger.info(
            "handler_full_pipeline_done",
            ticker=ticker, forms=forms,
            content_generated=total_content_generated,
            run_id=str(pipeline_run.id),
        )
        return {
            "ticker": ticker,
            "company_id": company_id,
            "forms": forms,
            "content_generated": total_content_generated,
            "pipeline_run_id": str(pipeline_run.id),
            "jobs_created": jobs_created,
            "jobs_completed": jobs_completed,
            "jobs_failed": jobs_failed,
        }

    except Exception as e:
        fail_pipeline_run(
            pipeline_run.id,
            error=str(e),
            jobs_created=jobs_created,
            jobs_completed=jobs_completed,
            jobs_failed=jobs_failed,
        )
        raise
