"""Job handler registry.

Handlers are registered with @register_handler(JobType.X) and looked up by
the worker loop at execution time.
"""
import time
from typing import Any, Callable, Dict, Optional

from symbology.database.jobs import JobType
from symbology.utils.logging import get_logger

logger = get_logger(__name__)


class DependencyNotReady(Exception):
    """Signal that a job can't proceed yet because a dependency isn't ready.

    A benign control-flow signal, NOT a crash. The worker catches it and defers
    the job (``backoff_job``) instead of failing it: no retry budget is consumed
    and the job polls until the dependency lands. Handlers raise this after
    ensuring the missing dependency has a job in flight.
    """


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
        ticker (str, required): Company ticker symbol.
        company_id (str, optional): UUID of the company in the database. When
            omitted, resolved from ``ticker`` (ingesting the company if missing).
        form (str): Filing form type, default "10-K".
        count (int): Number of filings to retrieve, default 5.
        include_documents (bool): Whether to ingest documents, default True.
    """
    from symbology.ingestion.edgar_db.accessors import edgar_login
    from symbology.ingestion.ingestion_helpers import ingest_filings
    from symbology.utils.config import settings

    ticker = params["ticker"]
    company_id = params.get("company_id")
    if not company_id:
        from symbology.database.companies import get_company_by_ticker

        company = get_company_by_ticker(ticker.upper())
        company_id = company.id if company else handle_company_ingestion({"ticker": ticker})["company_id"]
    form = params.get("form", "10-K")
    count = params.get("count", 5)
    include_documents = params.get("include_documents", True)

    logger.info("handler_filing_ingestion_start", ticker=ticker, form=form, count=count)
    edgar_login(settings.edgar_api.edgar_contact)
    results = ingest_filings(company_id, ticker, form, count, include_documents)
    filing_ids = [str(r[3]) for r in results]

    # Chunk + embed + cluster each ingested filing's documents asynchronously, so
    # diffs/search have vectors without coupling ingestion latency to embedding.
    # Also enqueue the filing's period-over-period diff here: diffs are filing-domain
    # (they need only the two sides embedded), so they're triggered at ingestion —
    # the FILING_DIFF job backs off until the embeddings land.
    if include_documents:
        for fid in filing_ids:
            _enqueue_embed_filing(fid)
            _enqueue_filing_diff_for(fid)

    logger.info("handler_filing_ingestion_done", ticker=ticker, filings_count=len(filing_ids))
    return {"ticker": ticker, "form": form, "filing_ids": filing_ids}


def _enqueue_embed_filing(filing_id: str) -> None:
    """Enqueue an EMBED_FILING job for a freshly-ingested filing (INGEST band).

    Chunk+embed is fast, required feedstock — diffs and content both wait on it —
    so it rides in the INGEST band ahead of generated content, not alongside it.
    """
    from symbology.database.jobs import JobPriority, JobType, create_job

    create_job(JobType.EMBED_FILING, params={"filing_id": filing_id},
               priority=JobPriority.INGEST)


@register_handler(JobType.CONTENT_GENERATION)
def handle_content_generation(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generate content using LLM.

    params:
        system_prompt_hash (str, required): Hash of the system prompt.
        model_config_hash (str, required): Hash of the model config.
        source_document_hashes (list[str]): Hashes of source documents.
        source_content_hashes (list[str]): Hashes of source generated content.
        company_ticker (str, optional): Company ticker (resolves company_id).
        description (str, optional): Description of the content.
        document_type (str, optional): Document type for disambiguation.
        form_type (str, optional): Filing form type (e.g. "10-K").
        content_stage (str, optional): ContentStage value to tag the content.
        company_group_id / filing_id / document_id (optional): Subject/scope FKs
            set per page-content kind (distinct from the source provenance links).
    """
    from symbology.database.base import get_db_session
    from symbology.database.companies import get_company_by_ticker
    from symbology.database.documents import Document
    from symbology.database.generated_content import (
        ContentStage,
        compute_generation_depth,
        create_generated_content,
        find_existing_generated_content,
        get_generated_content_by_hash,
    )
    from symbology.database.documents import DocumentType
    from symbology.database.prompts import Prompt
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
    force = params.get("force", False)
    # Subject/scope FKs (set per page-content kind; company_id is derived from ticker below).
    company_group_id = params.get("company_group_id")
    filing_id = params.get("filing_id")
    document_id = params.get("document_id")

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
    _seen_doc_ids: set = set()
    for doc_hash in source_doc_hashes:
        doc = session.query(Document).filter(Document.content_hash == doc_hash).first()
        if doc and doc.id not in _seen_doc_ids:
            _seen_doc_ids.add(doc.id)
            source_documents.append(doc)

    # Resolve source content. Distinct hashes can still resolve to the same row
    # when the same content recurs across filings (identical sections share one
    # content-hashed row); dedupe by id so the many-to-many association insert
    # doesn't violate its composite PK and the prompt isn't fed duplicate sources.
    source_content = []
    _seen_content_ids: set = set()
    for content_hash in source_content_hashes:
        content = get_generated_content_by_hash(content_hash)
        if content and content.id not in _seen_content_ids:
            _seen_content_ids.add(content.id)
            source_content.append(content)

    # Build user prompt
    user_prompt_text = format_user_prompt_content(
        source_documents=source_documents or None,
        source_content=source_content or None,
    )

    # Offload oversized prompts from the local endpoint to Anthropic (no-op when
    # disabled / already Anthropic / under threshold). The returned config is
    # what we both call and record below, so provenance reflects the offload.
    # This preemptive resolve also keys the dedup check below; the actual LLM call
    # re-applies it (deterministically) and adds a reactive fallback.
    from symbology.worker.config_loader import (
        generate_with_overflow,
        resolve_generation_model_config,
    )
    model_config = resolve_generation_model_config(
        model_config, f"{system_prompt.content}\n{user_prompt_text}"
    )

    # Resolve structured metadata (needed for the dedup key below).
    resolved_document_type = DocumentType(document_type_str) if document_type_str else None
    resolved_content_stage = ContentStage(content_stage_str) if content_stage_str else None

    # Centralized dedup: skip the LLM call if content already exists for the same
    # (sources, prompt, *resolved* model, stage). This runs after overflow
    # resolution, so the key matches what we store — unlike the pre-overflow
    # stage-level checks, which miss whenever a prompt overflows to Anthropic.
    if not force:
        existing = find_existing_generated_content(
            content_stage=resolved_content_stage,
            system_prompt_id=system_prompt.id,
            model_config_id=model_config.id,
            source_document_ids=[d.id for d in source_documents] or None,
            source_content_ids=[c.id for c in source_content] or None,
        )
        if existing and existing.content_hash:
            logger.info(
                "handler_content_generation_reuse",
                description=description,
                content_id=str(existing.id),
                content_hash=existing.content_hash[:12],
            )
            return {
                "content_id": str(existing.id),
                "content_hash": existing.content_hash,
                "was_created": False,
            }

    # Call LLM. If the local model still reports a context overflow (the preemptive
    # estimate undershot), generate_with_overflow retries on Anthropic and returns
    # that config so the row below is recorded against the model that served it.
    logger.info("handler_content_generation_start", description=description)
    response, warning, model_config = generate_with_overflow(
        model_config, system_prompt.content, user_prompt_text
    )

    # Resolve company
    company_id = None
    if company_ticker:
        company = get_company_by_ticker(company_ticker)
        if company:
            company_id = company.id

    # Save generated content
    content_data = {
        "content": response.response,
        "summary": None,
        "company_id": company_id,
        "company_group_id": company_group_id,
        "filing_id": filing_id,
        "document_id": document_id,
        "description": description,
        "document_type": resolved_document_type,
        "form_type": form_type,
        "content_stage": resolved_content_stage,
        "generation_depth": compute_generation_depth(source_content),
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
        compute_generation_depth,
        create_generated_content,
        get_aggregate_summaries_by_ticker,
    )
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

    # Call LLM, offloading oversized prompts to Anthropic — preemptively (cross-company
    # inputs can be large) and reactively if the local model still overflows. ``mc`` is
    # reassigned to the model that served the request so the row below records it.
    from symbology.worker.config_loader import generate_with_overflow
    response, warning, mc = generate_with_overflow(
        mc, system_prompt.content, user_prompt_text
    )

    # Store result
    content_data = {
        "content": response.response,
        "summary": None,
        "company_id": None,
        "company_group_id": group.id if group else None,
        "description": "company_group_analysis",
        "content_stage": ContentStage.COMPANY_GROUP_ANALYSIS,
        "generation_depth": compute_generation_depth(all_sources),
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


def _resolve_filing_by_accession(accession_number: str):
    """Return the DB filing for an accession number, ingesting it if missing.

    Looks the filing up in the DB first; if absent, fetches it from EDGAR
    (creating/looking up the owning company) and ingests its documents so the
    page pipeline has section text to work with.
    """
    from symbology.database.filings import get_filing_by_accession_number
    from symbology.ingestion.bulk_discovery import get_or_create_company_from_filing
    from symbology.ingestion.edgar_db.accessors import edgar_login
    from symbology.ingestion.ingestion_helpers import ingest_single_filing
    from symbology.utils.config import settings

    filing = get_filing_by_accession_number(accession_number)
    if filing is not None:
        return filing

    from edgar import find

    edgar_login(settings.edgar_api.edgar_contact)
    edgar_filing = find(accession_number)
    if edgar_filing is None:
        raise ValueError(f"No EDGAR filing found for accession {accession_number}")

    company = get_or_create_company_from_filing(
        cik=str(edgar_filing.cik),
        company_name=edgar_filing.company,
    )
    ingest_single_filing(
        company_id=company.id,
        accession_number=accession_number,
        include_documents=True,
    )

    filing = get_filing_by_accession_number(accession_number)
    if filing is None:
        raise ValueError(f"Failed to ingest filing for accession {accession_number}")
    # Freshly ingested here (bypassing handle_filing_ingestion), so trigger
    # chunk/embed/cluster and its period-over-period diff; the already-present path
    # above skips this.
    _enqueue_embed_filing(str(filing.id))
    _enqueue_filing_diff_for(str(filing.id))
    return filing


def _resolve_filing_token(value):
    """Resolve a filing from a UUID string or an EDGAR accession number.

    Lets the embed/diff jobs accept either id form ergonomically: a value that
    parses as a UUID is looked up by id; anything else is treated as an accession
    number (ingested on demand via :func:`_resolve_filing_by_accession`).
    """
    from uuid import UUID

    from symbology.database.filings import get_filing

    try:
        UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return _resolve_filing_by_accession(str(value))

    filing = get_filing(value)
    if filing is None:
        raise ValueError(f"filing not found: {value}")
    return filing


@register_handler(JobType.FILING_PAGE_CONTENT)
def handle_filing_page_content(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generate + publish document and filing page content for one filing.

    Runs the filing page pipeline (producing DocumentPageContent per document and a
    FilingPageContent version) once the target filing is present.

    The target filing can be selected either by ticker + fiscal year (the
    default) or directly by EDGAR accession number. On the ticker/year path, a
    missing company/filing is treated as a dependency: the handler queues
    FILING_INGESTION and defers itself (BACKOFF) until the filing lands, rather
    than ingesting inline (a requested fiscal year that stays absent after
    ingestion is still a hard error). The accession-number path resolves (and, if
    truly absent, ingests) the single filing inline, since it needs an EDGAR
    metadata lookup to learn the company/form before any ingestion job could be
    keyed.

    params:
        accession_number (str, optional): EDGAR accession number of the target
            filing. When provided, ticker/year/form are ignored.
        ticker (str): Company ticker. Required unless accession_number is given.
        year (int): Fiscal year of the target filing. Required unless
            accession_number is given.
        form (str): Filing form type. Defaults to "10-K".
    """
    from uuid import UUID

    from symbology.database.base import get_db_session
    from symbology.database.companies import get_company_by_ticker
    from symbology.database.filings import Filing
    from symbology.worker.page_pipelines import (
        FilingHasNoPageableDocuments,
        filing_page_content_pipeline,
    )

    accession_number = params.get("accession_number")
    if accession_number:
        filing = _resolve_filing_by_accession(accession_number)
        try:
            page = filing_page_content_pipeline(filing)
        except FilingHasNoPageableDocuments:
            logger.info("filing_page_skipped_no_documents",
                        accession_number=accession_number, filing_id=str(filing.id))
            return {"accession_number": accession_number,
                    "filing_id": str(filing.id), "skipped": "no_documents"}
        logger.info("handler_filing_page_content_done",
                    accession_number=accession_number, filing_id=str(filing.id))
        return {
            "accession_number": accession_number,
            "filing_id": str(filing.id),
            "filing_page_content_id": str(page.id),
        }

    ticker = params["ticker"]
    year = int(params["year"])
    form = params.get("form", "10-K")

    logger.info("handler_filing_page_content_start", ticker=ticker, year=year, form=form)

    def _find_filing(company_id):
        session = get_db_session()
        filings = (
            session.query(Filing)
            .filter(Filing.company_id == UUID(str(company_id)), Filing.form == form)
            .all()
        )
        for f in filings:
            if (f.period_of_report and f.period_of_report.year == year) or (
                f.filing_date and f.filing_date.year == year
            ):
                return f
        return None

    # Ingestion dependency gate (mirrors the company page): rather than ingesting
    # inline, treat a missing company/filing as a dependency — queue FILING_INGESTION
    # (which ingests the company too) and defer (BACKOFF) until it lands.
    from symbology.database.jobs import JobType, get_active_jobs

    company = get_company_by_ticker(ticker.upper())
    if company is None:
        _await_filing_ingestion(
            ticker, [form],
            reason_subject=f"filing page {ticker} {year} {form}",
        )  # raises DependencyNotReady

    # Company present; locate the target fiscal year's filing.
    filing = _find_filing(company.id)
    if filing is None:
        # Wait while an ingestion for this form is still running; once it has
        # finished, decide between "year genuinely absent" (hard fail, bounded) and
        # "never ingested this form yet" (queue + backoff).
        if _filing_ingestion_in_flight(ticker, form, get_active_jobs(JobType.FILING_INGESTION)):
            raise DependencyNotReady(
                f"filing page {ticker} {year} {form} waiting on in-flight ingestion"
            )
        if _company_has_filings(company.id, form):
            raise ValueError(
                f"No {form} filing for {ticker} fiscal year {year} after ingestion"
            )
        _await_filing_ingestion(
            ticker, [form],
            reason_subject=f"filing page {ticker} {year} {form}",
        )  # raises DependencyNotReady

    try:
        page = filing_page_content_pipeline(filing)
    except FilingHasNoPageableDocuments:
        logger.info("filing_page_skipped_no_documents", ticker=ticker, year=year,
                    form=form, filing_id=str(filing.id))
        return {"ticker": ticker, "year": year, "form": form,
                "filing_id": str(filing.id), "skipped": "no_documents"}

    logger.info("handler_filing_page_content_done", ticker=ticker, year=year,
                form=form, filing_id=str(filing.id))
    return {
        "ticker": ticker,
        "year": year,
        "form": form,
        "filing_id": str(filing.id),
        "filing_page_content_id": str(page.id),
    }


@register_handler(JobType.COMPANY_PAGE_CONTENT)
def handle_company_page_content(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Publish company page content by synthesizing already-published pages.

    Pure synthesis: it does *not* ingest or generate inline. The company page
    pipeline requires each source filing (and its documents) to already have
    published page content — so a CompanyPageContent never cites analysis that
    isn't itself available on the site. Rather than fail when a prerequisite is
    absent, the handler resolves it as a *dependency*: it queues the missing work
    (FILING_INGESTION when the company/filings aren't ingested; FILING_PAGE_CONTENT
    when filing pages aren't published) and defers itself (BACKOFF) until the
    dependency lands, consuming no retry budget.

    params:
        ticker (str, required): Company ticker.
        lookback (int): Number of recent filings to span. Defaults to 5.
        form (str): Filing form type. Defaults to "10-K".
    """
    from symbology.database.companies import get_company_by_ticker
    from symbology.database.jobs import JobType, get_active_jobs
    from symbology.worker.page_pipelines import (
        COMPANY_CHANGE_REPORT_FORM,
        DEFAULT_COMPANY_LOOKBACK,
        QUARTERLY_FORM,
        FilingPageContentNotReady,
        company_page_content_pipeline,
    )

    ticker = params["ticker"]
    lookback = int(params.get("lookback", DEFAULT_COMPANY_LOOKBACK))
    form = params.get("form", "10-K")

    logger.info("handler_company_page_content_start", ticker=ticker,
                lookback=lookback, form=form)

    # Ingestion dependency gate: the company page is pure synthesis over published
    # filing pages, which in turn need the filings (and company) ingested. If the
    # primary form isn't ingested yet, queue FILING_INGESTION (which ingests the
    # company too) and defer (BACKOFF) — for a 10-Q page we also opportunistically
    # ingest the 10-K it anchors on. A genuinely bad ticker simply backs off
    # forever (visible + cancellable).
    company = get_company_by_ticker(ticker.upper())
    if company is None or not _company_has_filings(company.id, form):
        _await_filing_ingestion(
            ticker, _required_company_forms(form), lookback=lookback,
            reason_subject=f"company page {ticker} {form}",
        )  # raises DependencyNotReady

    # Primary form present. For a 10-Q page, wait out an in-flight 10-K-anchor
    # ingestion so the page anchors on the annual rather than the quarter-only
    # fallback. Bounded: the job always terminates; if the company files no 10-K it
    # completes empty and the next poll proceeds via _select_source_filings.
    if form == QUARTERLY_FORM and _filing_ingestion_in_flight(
        ticker, COMPANY_CHANGE_REPORT_FORM, get_active_jobs(JobType.FILING_INGESTION)
    ):
        raise DependencyNotReady(
            f"company page {ticker} 10-Q waiting on 10-K anchor ingestion"
        )

    try:
        page = company_page_content_pipeline(company, lookback=lookback, form=form)
    except FilingPageContentNotReady as exc:
        # Dependency gate, not a real failure: the source filing pages aren't
        # published yet. Ensure each missing filing has a page job in flight
        # (queue one if not), then raise DependencyNotReady so the worker defers
        # this same job (BACKOFF) rather than burning retries on a crash loop.
        _await_filing_page_content(ticker, form, exc)

    # Diffs are not triggered here: they're filing-domain and enqueued at ingestion
    # (see _enqueue_filing_diff_for), so by the time the company page publishes its
    # source filings' period-over-period diffs are already in flight or done.
    logger.info("handler_company_page_content_done", ticker=ticker,
                form=form, company_id=str(company.id))
    return {
        "ticker": ticker,
        "form": form,
        "company_id": str(company.id),
        "company_page_content_id": str(page.id),
    }


def _filing_page_job_in_flight(filing, active_jobs) -> bool:
    """Whether a FILING_PAGE_CONTENT job for ``filing`` is already PENDING/IN_PROGRESS.

    FILING_PAGE_CONTENT jobs are parameterized either by ``accession_number`` or
    by ``ticker``+``year``(+``form``), so match on both shapes. Year is compared
    against the filing's period-of-report and filing-date years to mirror how
    ``handle_filing_page_content`` resolves a filing from a fiscal year.
    """
    acc = filing.accession_number
    fticker = (filing.company.ticker or "").upper()
    fform = filing.form
    fyears = set()
    if filing.period_of_report:
        fyears.add(filing.period_of_report.year)
    if filing.filing_date:
        fyears.add(filing.filing_date.year)

    for job in active_jobs:
        p = job.params or {}
        if acc and p.get("accession_number") == acc:
            return True
        if (p.get("ticker") or "").upper() == fticker and p.get("form", "10-K") == fform:
            year = p.get("year")
            if year is not None and int(year) in fyears:
                return True
    return False


def _await_filing_page_content(ticker, form, exc):
    """React to missing source filing pages: enqueue what's absent, then defer.

    For each missing filing id from ``exc``: if a filing page job is already in
    flight, leave it; otherwise queue a fresh one by accession number (covers the
    never-queued case *and* a prior job that died transiently — it's no longer in
    flight, so we re-queue). Then raise :class:`DependencyNotReady`, which the
    worker turns into a BACKOFF defer of this same company page job (no retry
    burned, no copy spawned). A company page is pure synthesis and can't degrade
    to a partial, so it waits until its filing pages land rather than emitting a
    page that cites unpublished analysis.
    """
    from uuid import UUID

    from symbology.database.base import get_db_session
    from symbology.database.filings import Filing
    from symbology.database.jobs import JobPriority, JobType, create_job, get_active_jobs

    session = get_db_session()
    active_filing_jobs = get_active_jobs(JobType.FILING_PAGE_CONTENT)

    queued, waiting, unresolved = [], [], []
    for fid in exc.missing_filing_ids:
        filing = session.query(Filing).filter(Filing.id == UUID(fid)).first()
        if filing is None:
            # Can't queue a precise job without the row; surface it and move on.
            unresolved.append(fid)
            logger.warning("dep_filing_not_found", filing_id=fid, ticker=ticker)
            continue
        if _filing_page_job_in_flight(filing, active_filing_jobs):
            waiting.append(fid)
            logger.info("dep_filing_page_in_flight", filing_id=fid, ticker=ticker)
            continue
        job = create_job(
            job_type=JobType.FILING_PAGE_CONTENT,
            params={"accession_number": filing.accession_number},
            # A company page is parked waiting on this — unblock it ahead of the queue.
            priority=JobPriority.DEP_UNBLOCK,
        )
        queued.append(filing.accession_number)
        logger.info("dep_filing_page_queued", filing_id=fid,
                    accession_number=filing.accession_number, job_id=str(job.id))

    logger.info("company_page_waiting_on_filing_pages", ticker=ticker, form=form,
                queued_filing_pages=queued, waiting_on=waiting, unresolved=unresolved)
    raise DependencyNotReady(
        f"company page {ticker} {form} waiting on filing pages "
        f"(queued={len(queued)}, in_flight={len(waiting)}, unresolved={len(unresolved)})"
    )


# Default filing counts to ingest per form when a page job triggers ingestion.
_INGEST_DEFAULT_COUNTS = {"10-K": 5, "10-Q": 6}

# The periodic forms that may be diffed against each other (a 10-K stands in for
# Q4, so a cycle's first 10-Q diffs against the anchoring 10-K).
_PERIODIC_FORMS = {"10-K", "10-Q"}


def _filing_ingestion_in_flight(ticker, form, active_jobs) -> bool:
    """Whether a FILING_INGESTION job for ``ticker``+``form`` is PENDING/IN_PROGRESS.

    Mirrors :func:`_filing_page_job_in_flight`. FILING_INGESTION jobs are keyed by
    ``ticker`` (case-insensitive) and ``form`` (defaulting to ``"10-K"``), so match
    on both — used to avoid enqueuing a duplicate ingestion before deferring.
    """
    t = ticker.upper()
    for job in active_jobs:
        p = job.params or {}
        if (p.get("ticker") or "").upper() == t and p.get("form", "10-K") == form:
            return True
    return False


def _company_has_filings(company_id, form) -> bool:
    """Whether the company already has at least one ingested filing of ``form``."""
    from symbology.database.base import get_db_session
    from symbology.database.filings import Filing

    session = get_db_session()
    return (
        session.query(Filing.id)
        .filter(Filing.company_id == company_id, Filing.form == form)
        .first()
        is not None
    )


def _required_company_forms(form: str):
    """Forms whose filings a company page for ``form`` needs ingested.

    Just ``[form]`` for an annual page; a 10-Q page also anchors on a 10-K (see
    ``_select_source_filings``), so the annual form is appended for it.
    """
    from symbology.worker.page_pipelines import (
        COMPANY_CHANGE_REPORT_FORM,
        QUARTERLY_FORM,
    )

    forms = [form]
    if form == QUARTERLY_FORM and COMPANY_CHANGE_REPORT_FORM not in forms:
        forms.append(COMPANY_CHANGE_REPORT_FORM)
    return forms


def _await_filing_ingestion(ticker, forms, *, lookback=None, reason_subject):
    """Enqueue FILING_INGESTION for each missing form, then defer this job (BACKOFF).

    The ingestion analogue of :func:`_await_filing_page_content`: for each form not
    already in flight, queue a high-priority FILING_INGESTION job (which ingests the
    company too when missing — see :func:`handle_filing_ingestion`), then raise
    :class:`DependencyNotReady` so the worker defers this same page job rather than
    burning retries. ``lookback`` (when given) bumps the ingest count so enough
    filings land to cover the page's span.
    """
    from symbology.database.jobs import JobPriority, JobType, create_job, get_active_jobs

    active = get_active_jobs(JobType.FILING_INGESTION)
    queued, waiting = [], []
    for form in forms:
        if _filing_ingestion_in_flight(ticker, form, active):
            waiting.append(form)
            logger.info("dep_filing_ingestion_in_flight", ticker=ticker, form=form)
            continue
        count = _INGEST_DEFAULT_COUNTS.get(form, 5)
        if lookback:
            count = max(count, lookback + 1)
        job = create_job(
            JobType.FILING_INGESTION,
            params={"ticker": ticker, "form": form, "count": count,
                    "include_documents": True},
            # A page job is parked waiting on this ingestion — unblock it first.
            priority=JobPriority.DEP_UNBLOCK,
        )
        queued.append(form)
        logger.info("dep_filing_ingestion_queued", ticker=ticker, form=form,
                    count=count, job_id=str(job.id))

    logger.info("page_waiting_on_ingestion", ticker=ticker, subject=reason_subject,
                queued=queued, waiting_on=waiting)
    raise DependencyNotReady(
        f"{reason_subject} waiting on filing ingestion "
        f"(queued={queued}, in_flight={waiting})"
    )


def _backfill_query(params: Dict[str, Any]):
    """Build the (document_id, company_id, document_type) query for backfill jobs.

    Scopes by optional ticker/company_id/document_types and caps with limit.
    Selects ids only (Document.content is deferred and loaded per-document later).
    """
    from uuid import UUID

    from symbology.database.base import get_db_session
    from symbology.database.companies import get_company_by_ticker
    from symbology.database.documents import Document, DocumentType

    session = get_db_session()
    q = (
        session.query(Document.id, Document.company_id, Document.document_type)
        .filter(Document.content_hash.isnot(None))
    )
    if params.get("ticker"):
        company = get_company_by_ticker(params["ticker"].upper())
        if company is None:
            raise ValueError(f"company {params['ticker']} not ingested")
        q = q.filter(Document.company_id == company.id)
    elif params.get("company_id"):
        q = q.filter(Document.company_id == UUID(str(params["company_id"])))
    if params.get("document_types"):
        q = q.filter(
            Document.document_type.in_([DocumentType(d) for d in params["document_types"]])
        )
    q = q.order_by(Document.company_id, Document.document_type)
    if params.get("limit"):
        q = q.limit(int(params["limit"]))
    return q


@register_handler(JobType.EMBED_FILING)
def handle_embed_filing(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Ensure section chunks + embeddings + topics exist for one filing's documents.

    The sole owner of chunk/embed/cluster for ingested filings (auto-enqueued by
    filing ingestion). Idempotent: re-chunking carries ``topic_id`` forward by
    content_hash, so re-runs don't churn topic identity. Non-fatal per document.

    params:
        filing_id (str): UUID of the filing. OR
        accession_number (str): EDGAR accession number (ingested on demand).
    """
    from symbology.llm.content_processing import chunk_embed_and_cluster_document

    value = params.get("filing_id") or params.get("accession_number")
    if not value:
        raise ValueError("embed_filing requires filing_id or accession_number")
    filing = _resolve_filing_token(value)

    documents = list(filing.documents)
    processed = 0
    for doc in documents:
        try:
            chunk_embed_and_cluster_document(doc.id, embed=True, cluster=True)
            processed += 1
        except Exception as e:
            logger.error("embed_filing_document_failed", filing_id=str(filing.id),
                         document_id=str(doc.id), error=str(e), exc_info=True)

    logger.info("handler_embed_filing_done", filing_id=str(filing.id),
                documents_processed=processed, documents_total=len(documents))
    return {
        "filing_id": str(filing.id),
        "documents_processed": processed,
        "documents_total": len(documents),
    }


@register_handler(JobType.BACKFILL_CHUNKS)
def handle_backfill_chunks(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Section-chunk + embed existing documents, then recluster each scope.

    Chunks each document with clustering deferred, then recomputes topics
    per (company, document_type) from scratch (deterministic) — the clean way to
    bring existing data up to the section-aware primitive.

    params (all optional):
        ticker / company_id: limit to one company.
        document_types: list of DocumentType values to limit to.
        limit: cap the number of documents processed.
        embed: embed chunks (default True). recluster: recluster scopes (default True).
    """
    from symbology.llm.content_processing import chunk_embed_and_cluster_document
    from symbology.llm.topic_clustering import recluster_company_doctype

    embed = params.get("embed", True)
    do_recluster = params.get("recluster", True)
    rows = _backfill_query(params).all()

    scopes = set()
    processed = 0
    for doc_id, company_id, document_type in rows:
        try:
            chunk_embed_and_cluster_document(doc_id, embed=embed, cluster=False)
            processed += 1
            if company_id and document_type is not None:
                scopes.add((company_id, document_type))
        except Exception as e:
            logger.error("backfill_chunk_document_failed", document_id=str(doc_id),
                         error=str(e), exc_info=True)

    reclustered = 0
    if do_recluster and embed:
        for company_id, document_type in scopes:
            try:
                recluster_company_doctype(company_id, document_type)
                reclustered += 1
            except Exception as e:
                logger.error("backfill_recluster_failed", company_id=str(company_id),
                             document_type=getattr(document_type, "value", str(document_type)),
                             error=str(e), exc_info=True)

    logger.info("handler_backfill_chunks_done", documents=processed,
                total=len(rows), scopes_reclustered=reclustered)
    return {
        "documents_processed": processed,
        "total_documents": len(rows),
        "scopes_reclustered": reclustered,
    }


@register_handler(JobType.BACKFILL_EMBEDDINGS)
def handle_backfill_embeddings(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Re-embed documents that have any unembedded chunks.

    Finds documents with at least one ``embedding IS NULL`` chunk and re-runs the
    section chunk+embed+cluster path on them (deterministic re-chunk carries
    topic_id forward, so only embeddings are filled in). Scope params match
    :func:`handle_backfill_chunks`.
    """
    from symbology.database.base import get_db_session
    from symbology.database.document_chunks import DocumentChunk
    from symbology.llm.content_processing import chunk_embed_and_cluster_document

    session = get_db_session()
    candidate_ids = {row[0] for row in _backfill_query(params).all()}
    if not candidate_ids:
        return {"documents_processed": 0}

    # Documents (within scope) that still have an unembedded chunk.
    unembedded = {
        doc_id
        for (doc_id,) in session.query(DocumentChunk.document_id)
        .filter(DocumentChunk.document_id.in_(candidate_ids), DocumentChunk.embedding.is_(None))
        .distinct()
        .all()
    }

    processed = 0
    for doc_id in unembedded:
        try:
            chunk_embed_and_cluster_document(doc_id, embed=True, cluster=True)
            processed += 1
        except Exception as e:
            logger.error("backfill_embeddings_failed", document_id=str(doc_id),
                         error=str(e), exc_info=True)

    logger.info("handler_backfill_embeddings_done", documents=processed,
                candidates=len(unembedded))
    return {"documents_processed": processed, "candidates": len(unembedded)}


def _filing_ready_for_diff(filing_id) -> bool:
    """Whether a filing has semantic, clustered chunks (i.e. EMBED_FILING has run)."""
    from symbology.database.base import get_db_session
    from symbology.database.document_chunks import DocumentChunk
    from symbology.database.documents import Document

    session = get_db_session()
    return (
        session.query(DocumentChunk.id)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(
            Document.filing_id == filing_id,
            DocumentChunk.is_semantic.is_(True),
            DocumentChunk.topic_id.isnot(None),
        )
        .first()
        is not None
    )


def _filing_has_chunks(filing_id) -> bool:
    """Whether EMBED_FILING has already produced *any* chunks for this filing.

    Distinguishes "embedding hasn't run yet" (no chunks → genuinely pending, defer)
    from "embedding ran but produced no semantic/clustered chunks" (chunks exist
    yet :func:`_filing_ready_for_diff` is still False). The latter is terminal: the
    filing's sections only yield non-semantic fallback chunks (a short 10-Q
    risk-factors stub, or legal_proceedings — never heading-segmented), which are
    excluded from topic clustering, so ``topic_id`` stays NULL and re-embedding is
    a no-op. Backing off such a side loops forever.
    """
    from symbology.database.base import get_db_session
    from symbology.database.document_chunks import DocumentChunk
    from symbology.database.documents import Document

    session = get_db_session()
    return (
        session.query(DocumentChunk.id)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(Document.filing_id == filing_id)
        .first()
        is not None
    )


def _order_filings(a, b):
    """Return ``(older, newer)`` by period_of_report, falling back to filing_date."""
    from datetime import date

    def sort_key(f):
        return (f.period_of_report or date.min, f.filing_date or date.min)

    return (a, b) if sort_key(a) <= sort_key(b) else (b, a)


def _await_filing_diff_embeddings(not_ready):
    """Enqueue EMBED_FILING for not-yet-embedded filings, then defer this diff job.

    Mirrors :func:`_await_filing_page_content`. Queues an embed job for each
    not-yet-embedded side that doesn't already have one in flight, then raises
    :class:`DependencyNotReady` so the worker defers this same diff job (BACKOFF)
    until the embeddings land — rather than diffing best-effort over partial
    chunks.
    """
    from symbology.database.jobs import JobPriority, JobType, create_job, get_active_jobs

    in_flight = {(j.params or {}).get("filing_id") for j in get_active_jobs(JobType.EMBED_FILING)}

    queued, waiting = [], []
    for filing in not_ready:
        fid = str(filing.id)
        if fid in in_flight:
            waiting.append(fid)
            continue
        # A diff job is parked waiting on these embeddings — unblock it first.
        job = create_job(JobType.EMBED_FILING, params={"filing_id": fid},
                         priority=JobPriority.DEP_UNBLOCK)
        queued.append(fid)
        logger.info("dep_embed_filing_queued", filing_id=fid, job_id=str(job.id))

    logger.info("filing_diff_waiting_on_embeddings", queued_embeds=queued, waiting_on=waiting)
    raise DependencyNotReady(
        f"filing diff waiting on embeddings (queued={len(queued)}, in_flight={len(waiting)})"
    )


@register_handler(JobType.FILING_DIFF)
def handle_filing_diff(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Compute + persist section diffs for an explicit ``(from, to)`` filing pair.

    ``from``/``to`` (aliases ``left_filing_id``/``right_filing_id``) each accept a
    filing UUID or an EDGAR accession number. The pair must be the same company +
    form; it is reordered so the older filing is the diff's left side.

    If either side lacks chunks/topics, an EMBED_FILING job is enqueued and this
    job is deferred (BACKOFF) until the embeddings land, then re-runs.

    params:
        from / left_filing_id (str): older filing (id or accession).
        to / right_filing_id (str): newer filing (id or accession).
        form (str, optional): overrides the form inferred from the filings.
        generate_summaries (bool): per-topic LLM summaries (default True).
    """
    from symbology.worker.diff_pipeline import filing_diff_pipeline

    left_token = params.get("from") or params.get("left_filing_id")
    right_token = params.get("to") or params.get("right_filing_id")
    if not left_token or not right_token:
        raise ValueError("filing_diff requires `from` and `to` (filing id or accession)")

    a = _resolve_filing_token(left_token)
    b = _resolve_filing_token(right_token)
    if a.id == b.id:
        raise ValueError("filing_diff: from and to are the same filing")
    if a.company_id != b.company_id:
        raise ValueError("filing_diff: from/to belong to different companies")
    # Same form, or the {10-K, 10-Q} anchor pairing (a 10-K stands in for Q4, so the
    # first quarter of a cycle diffs against the annual). Topics are scoped by
    # (company, document_type) — not form — so cross-form alignment is sound. Any
    # other mix (e.g. 8-K vs 10-K) is rejected.
    if a.form != b.form and {a.form, b.form} != _PERIODIC_FORMS:
        raise ValueError(f"filing_diff: incompatible forms ({a.form} vs {b.form})")

    left_filing, right_filing = _order_filings(a, b)
    # Tag the diff with the newer side's form (so a 10-K→10-Q anchor pair is a
    # quarterly diff using the 10-Q's document types), unless explicitly overridden.
    form = params.get("form") or right_filing.form
    generate_summaries = params.get("generate_summaries", True)

    not_ready = [f for f in (left_filing, right_filing) if not _filing_ready_for_diff(f.id)]
    if not_ready:
        from symbology.worker.config_loader import load_pipeline_config
        from symbology.worker.page_pipelines import _filing_has_pageable_documents

        # A not-ready side with no pageable documents can never be embedded — skip
        # the diff (complete) rather than back off forever. Sides that *have*
        # documents are just pending embedding, so those still defer (BACKOFF).
        doc_types = load_pipeline_config().form_document_types.get(form, [])
        undocumented = [f for f in not_ready if not _filing_has_pageable_documents(f, doc_types)]
        if undocumented:
            logger.info("filing_diff_skipped_no_documents", form=form,
                        filing_ids=[str(f.id) for f in undocumented])
            return {
                "left_filing_id": str(left_filing.id),
                "right_filing_id": str(right_filing.id),
                "form": form,
                "skipped": "no_documents",
            }
        # A not-ready side that already has chunks has been embedded, but its
        # sections only yield non-semantic fallback chunks (no topic_id) — so the
        # readiness gate can never pass and re-embedding loops forever. Skip
        # (terminal) rather than backing off. See _filing_has_chunks.
        unclusterable = [f for f in not_ready if _filing_has_chunks(f.id)]
        if unclusterable:
            logger.info("filing_diff_skipped_no_semantic_chunks", form=form,
                        filing_ids=[str(f.id) for f in unclusterable])
            return {
                "left_filing_id": str(left_filing.id),
                "right_filing_id": str(right_filing.id),
                "form": form,
                "skipped": "no_semantic_chunks",
            }
        # Raises DependencyNotReady → worker defers (BACKOFF) until embeddings land.
        _await_filing_diff_embeddings(not_ready)

    # Compute the structural diff only — fast, no LLM. Per-topic "what changed"
    # summaries are decoupled into a separate low-priority DIFF_SUMMARY job so the
    # diff itself is available immediately rather than waiting on a string of LLM
    # calls (`generate_summaries` now means "enqueue the summary job", not "do it
    # inline"). `max_summaries` (if given) caps topics summarised per set.
    max_summaries = int(params["max_summaries"]) if params.get("max_summaries") is not None else None
    diff_sets = filing_diff_pipeline(
        left_filing, right_filing, form, generate_summaries=False
    )
    summary_jobs = (
        _enqueue_diff_summaries(diff_sets, form, max_summaries) if generate_summaries else []
    )
    logger.info("handler_filing_diff_done", left_filing_id=str(left_filing.id),
                right_filing_id=str(right_filing.id), form=form, diff_sets=len(diff_sets),
                summary_jobs=len(summary_jobs))
    return {
        "left_filing_id": str(left_filing.id),
        "right_filing_id": str(right_filing.id),
        "form": form,
        "diff_sets": len(diff_sets),
        "document_types": [ds.document_type.value for ds in diff_sets],
        "summary_jobs_enqueued": len(summary_jobs),
    }


def _diff_summary_in_flight(diff_set_id, active_jobs) -> bool:
    """Whether a DIFF_SUMMARY job for ``diff_set_id`` is already PENDING/IN_PROGRESS."""
    for job in active_jobs:
        if (job.params or {}).get("diff_set_id") == diff_set_id:
            return True
    return False


def _enqueue_diff_summaries(diff_sets, form, max_summaries=None):
    """Enqueue one low-priority DIFF_SUMMARY job per diff set with displayed changes.

    Only enqueues for sets that have a *displayed* (card/list) topic still lacking a
    summary — matching what summarize_diff_set will actually do — and skips sets that
    already have a DIFF_SUMMARY in flight. The SUMMARY band keeps summaries below the
    structural diffs / ingestion / page content so they fill in as spare capacity
    allows. Returns the ids of the jobs created.
    """
    from symbology.database.jobs import JobPriority, JobType, create_job, get_active_jobs
    from symbology.worker.diff_pipeline import is_displayed_change

    active = get_active_jobs(JobType.DIFF_SUMMARY)
    enqueued = []
    for ds in diff_sets:
        has_work = any(
            is_displayed_change(sd) and sd.summary_content_id is None
            for sd in ds.section_diffs
        )
        if not has_work:
            continue
        if _diff_summary_in_flight(str(ds.id), active):
            continue
        job_params = {"diff_set_id": str(ds.id), "form": form}
        if max_summaries is not None:
            job_params["max_summaries"] = max_summaries
        job = create_job(JobType.DIFF_SUMMARY, params=job_params,
                         priority=JobPriority.SUMMARY)
        enqueued.append(str(job.id))
        logger.info("diff_summary_enqueued", diff_set_id=str(ds.id), form=form,
                    job_id=str(job.id))
    return enqueued


@register_handler(JobType.DIFF_SUMMARY)
def handle_diff_summary(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generate per-topic "what changed" summaries for one diff set (low priority).

    Decoupled from FILING_DIFF so the structural diff is available immediately; this
    fills in ``summary_content_id`` for the most significant changed topics and is
    resume-friendly (already-summarised topics are skipped). A no-op if the diff set
    was re-computed away (deleted/replaced) before this ran.

    params:
        diff_set_id (str, required): the DiffSet to summarise.
        form (str, optional): overrides the form stored on the diff set.
        max_summaries (int, optional): cap on topics summarised (default
            ``MAX_TOPIC_SUMMARIES``; pass an explicit value to widen/narrow).
        force (bool, optional): re-summarise topics that already have a summary
            (replacing it), rather than only filling in missing ones.
    """
    from uuid import UUID

    from symbology.database.base import get_db_session
    from symbology.database.companies import get_company
    from symbology.database.section_diffs import DiffSet
    from symbology.worker.diff_pipeline import MAX_TOPIC_SUMMARIES, summarize_diff_set

    diff_set_id = params.get("diff_set_id")
    if not diff_set_id:
        raise ValueError("diff_summary requires diff_set_id")

    session = get_db_session()
    diff_set = session.query(DiffSet).filter(DiffSet.id == UUID(str(diff_set_id))).first()
    if diff_set is None:
        # The diff was re-computed (delete + re-create) before this ran; the fresh
        # FILING_DIFF enqueues a new summary job for the new set, so just stop.
        logger.info("diff_summary_set_gone", diff_set_id=diff_set_id)
        return {"diff_set_id": diff_set_id, "summarized": 0, "skipped": "set_gone"}

    company = get_company(diff_set.company_id)
    if company is None:
        logger.warning("diff_summary_company_missing", diff_set_id=diff_set_id,
                       company_id=str(diff_set.company_id))
        return {"diff_set_id": diff_set_id, "summarized": 0}

    form = params.get("form") or diff_set.form
    max_summaries = (
        int(params["max_summaries"]) if params.get("max_summaries") is not None
        else MAX_TOPIC_SUMMARIES
    )
    # `force` (set by `jobs retry --force`) re-summarises topics that already have a
    # summary — used to backfill blanks from an earlier run.
    force = bool(params.get("force"))
    summarized = summarize_diff_set(diff_set, company, form, max_summaries=max_summaries, force=force)
    logger.info("handler_diff_summary_done", diff_set_id=diff_set_id,
                summarized=summarized, force=force)
    return {"diff_set_id": diff_set_id, "summarized": summarized}


def _filing_diff_in_flight(left, right, active_jobs) -> bool:
    """Whether a FILING_DIFF job for the ``(left, right)`` pair is already active."""
    left_keys = {str(left.id), left.accession_number}
    right_keys = {str(right.id), right.accession_number}
    for job in active_jobs:
        p = job.params or {}
        lt = p.get("from") or p.get("left_filing_id")
        rt = p.get("to") or p.get("right_filing_id")
        if lt in left_keys and rt in right_keys:
            return True
    return False


def _pair_has_current_diff(company_id, doc_types, left_id, right_id) -> bool:
    """Whether any document type already has a current diff for this exact pairing.

    "Complete" for a ``(left, right)`` pair means at least one doc type has a current
    DiffSet whose left side matches ``left_id`` — avoids re-enqueuing pairs that
    already produced a diff (even an empty/partial one).
    """
    from symbology.database.section_diffs import get_current_diff_set

    for dt in doc_types:
        ds = get_current_diff_set(company_id, dt, right_filing_id=right_id)
        if ds is not None and ds.left_filing_id == left_id:
            return True
    return False


def _previous_periodic_filing(session, filing):
    """The company's filing immediately preceding ``filing`` for diff purposes.

    For a 10-Q the predecessor is the most recent *periodic* filing — the prior
    quarter, or the anchoring 10-K when ``filing`` is the first quarter of a cycle
    (a 10-K stands in for Q4) — so the quarterly chain never straddles the annual.
    For any other form (e.g. a 10-K) it's the most recent filing of the same form.
    Chronology keys off period_of_report (filing_date as fallback), matching the
    rest of the diff code. Returns None when there's no earlier filing.
    """
    from datetime import date

    from symbology.database.filings import Filing

    def _key(f):
        return (f.period_of_report or date.min, f.filing_date or date.min)

    forms = list(_PERIODIC_FORMS) if filing.form == "10-Q" else [filing.form]
    candidates = (
        session.query(Filing)
        .filter(
            Filing.company_id == filing.company_id,
            Filing.form.in_(forms),
            Filing.id != filing.id,
        )
        .all()
    )
    this_key = _key(filing)
    earlier = [f for f in candidates if _key(f) < this_key]
    return max(earlier, key=_key) if earlier else None


def _enqueue_filing_diff_for(filing_id) -> None:
    """Enqueue a FILING_DIFF of a freshly-ingested filing vs the previous periodic one.

    Diffs are filing-domain: a filing only needs both sides *embedded* to be
    diffed, so this is triggered at ingestion (alongside EMBED_FILING) rather than
    by page generation. Skips when there's no prior filing, when a current diff
    already covers the pair, or when a FILING_DIFF for it is already in flight. The
    FILING_DIFF job embeds first (EMBED_FILING + BACKOFF) if the sides aren't
    chunked yet. Non-fatal: a hiccup here must not fail the ingestion.
    """
    from uuid import UUID

    try:
        from symbology.database.base import get_db_session
        from symbology.database.documents import DocumentType
        from symbology.database.filings import Filing
        from symbology.database.jobs import JobPriority, JobType, create_job, get_active_jobs
        from symbology.worker.config_loader import load_pipeline_config

        session = get_db_session()
        filing = session.query(Filing).filter(Filing.id == UUID(str(filing_id))).first()
        if filing is None:
            return
        prev = _previous_periodic_filing(session, filing)
        if prev is None:
            logger.info("filing_diff_skip_no_prior", filing_id=str(filing.id),
                        form=filing.form)
            return

        from symbology.worker.page_pipelines import _filing_has_pageable_documents

        cfg = load_pipeline_config()
        doc_types_str = cfg.form_document_types.get(filing.form, [])
        doc_types = [DocumentType(d) for d in doc_types_str]
        # A side with no pageable documents can never be embedded/chunked, so a diff
        # involving it would back off forever waiting on embeddings. Skip it.
        if not _filing_has_pageable_documents(filing, doc_types_str) or not _filing_has_pageable_documents(
            prev, doc_types_str
        ):
            logger.info("filing_diff_skip_no_documents", filing_id=str(filing.id),
                        prev_id=str(prev.id), form=filing.form)
            return
        if _pair_has_current_diff(filing.company_id, doc_types, prev.id, filing.id):
            return
        if _filing_diff_in_flight(prev, filing, get_active_jobs(JobType.FILING_DIFF)):
            return

        job = create_job(
            JobType.FILING_DIFF,
            params={"left_filing_id": str(prev.id), "right_filing_id": str(filing.id),
                    "form": filing.form},
            # Required derived data — outranks generated content, behind ingest/embed.
            priority=JobPriority.DIFF,
        )
        logger.info("filing_diff_enqueued", left_filing_id=str(prev.id),
                    right_filing_id=str(filing.id), form=filing.form, job_id=str(job.id))
    except Exception:
        logger.error("filing_diff_enqueue_failed", filing_id=str(filing_id), exc_info=True)
