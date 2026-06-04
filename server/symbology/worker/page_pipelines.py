"""Page-content pipelines: generate the constituent GeneratedContent and
publish an immutable PageContent version for a page.

Bottom-up: ``document_page_content_pipeline`` (one document) and
``filing_page_content_pipeline`` (one filing, composing the document pipelines).
Configs and prompts come from the declarative ``model_configs.yaml`` via
``config_loader``; the LLM provider is selected by model name in the client.

All-or-nothing: a filing's content is generated *in full* before anything is
published. If any generation step fails (or no documents are present), the
pipeline raises and publishes nothing — a transient outage must never overwrite
the current published page with a degraded/empty version.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from symbology.database.documents import Document, DocumentType, select_substantive_document
from symbology.database.page_content import (
    get_current_document_page_content,
    get_current_filing_page_content,
    publish_company_page_content,
    publish_document_page_content,
    publish_filing_page_content,
)
from symbology.utils.logging import get_logger
from symbology.worker.config_loader import (
    ensure_stage_model_config,
    load_pipeline_config,
)
from symbology.worker.pipeline import (
    ensure_prompt,
    generate_page_content,
    generate_single_summaries,
)

# Document types whose change reports compose a company page (per form).
COMPANY_CHANGE_REPORT_FORM = "10-K"
DEFAULT_COMPANY_LOOKBACK = 5

logger = get_logger(__name__)


class PageContentGenerationError(RuntimeError):
    """Raised when page content could not be fully generated (publish is skipped)."""


class FilingPageContentNotReady(PageContentGenerationError):
    """Source filings still lack published page content — a dependency, not a hard failure.

    Distinguished from a generic ``PageContentGenerationError`` so a caller can
    react (wait for in-flight filing page jobs, or enqueue missing ones) instead
    of treating it as a terminal failure. Carries the offending filing ids.
    Subclasses ``PageContentGenerationError`` so existing ``except`` clauses
    still catch it.
    """

    def __init__(self, message: str, missing_filing_ids: List[str]):
        super().__init__(message)
        self.missing_filing_ids = missing_filing_ids


def _generate_document_page_content(
    filing,
    document,
    prompts_dir: Optional[Path],
    force: bool,
) -> Tuple[str, str]:
    """Generate a document's L1 summary + page intro (no publish).

    Returns ``(l1_hash, intro_hash)``. Raises PageContentGenerationError if
    either generation step fails (all-or-nothing).
    """
    cfg = load_pipeline_config(prompts_dir)
    doc_type_str = document.document_type.value
    ticker = filing.company.ticker
    form = filing.form

    # L1: single document summary (depth 1) — reuse the existing stage primitive.
    l1_prompt = ensure_prompt(cfg.doc_type_prompt_path(doc_type_str), prompts_dir)
    mc_single = ensure_stage_model_config("l1_document_summary", prompts_dir)
    hashes, *_ = generate_single_summaries(
        str(filing.company_id),
        ticker,
        form,
        doc_type_str,
        [filing],
        l1_prompt,
        mc_single,
        force=force,
    )
    if not hashes:
        raise PageContentGenerationError(
            f"L1 summary failed for {doc_type_str} in filing {filing.id}"
        )
    l1_hash = hashes[0]

    # L2: document page intro (depth 2), scoped to the document.
    intro_prompt = ensure_prompt(cfg.prompt_path("document_page_intro"), prompts_dir)
    mc_intro = ensure_stage_model_config("l2_document_page_intro", prompts_dir)
    intro_hash, intro_ok = generate_page_content(
        "document_page_intro",
        [l1_hash],
        intro_prompt,
        mc_intro,
        document_id=document.id,
        document_type=doc_type_str,
        form_type=form,
        force=force,
    )
    if not intro_ok:
        raise PageContentGenerationError(
            f"document page intro failed for {doc_type_str} in filing {filing.id}"
        )
    return l1_hash, intro_hash


def document_page_content_pipeline(
    filing,
    document: Document,
    prompts_dir: Optional[Path] = None,
    force: bool = False,
) -> str:
    """Generate a document's L1 summary + page intro and publish DocumentPageContent.

    Returns the L1 summary content hash. Raises PageContentGenerationError on any
    generation failure (nothing is published in that case).
    """
    l1_hash, intro_hash = _generate_document_page_content(
        filing, document, prompts_dir, force
    )
    publish_document_page_content(
        document.id, summary_hash=l1_hash, intro_hash=intro_hash
    )
    return l1_hash


def filing_page_content_pipeline(
    filing,
    prompts_dir: Optional[Path] = None,
    force: bool = False,
):
    """Generate document + filing page content for one filing and publish.

    Generates L1 summary + intro for each present document, then aggregates the
    L1 summaries into filing main content (L2) + intro (L3). Only after *all*
    generation succeeds are the DocumentPageContent rows and the
    FilingPageContent version published. Raises PageContentGenerationError if any
    step fails or no documents are present.
    """
    cfg = load_pipeline_config(prompts_dir)
    form = filing.form
    doc_types = cfg.form_document_types.get(form, [])

    # 1. Generate (no publish) for every present document — all must succeed.
    generated: List[Tuple[Document, str, str]] = []  # (document, l1_hash, intro_hash)
    for doc_type_str in doc_types:
        document = select_substantive_document(
            filing.documents, DocumentType(doc_type_str)
        )
        if document is None or not document.content_hash:
            continue  # section genuinely absent from this filing — not a failure
        # Chunking/embedding/clustering is owned by the EMBED_FILING job (enqueued
        # at ingestion); page synthesis below reads raw document.content, so it is
        # independent of chunks and need not trigger them here.
        l1_hash, intro_hash = _generate_document_page_content( # note: DocumentPageContents are published at the end of this pipeline
            filing, document, prompts_dir, force
        )
        generated.append((document, l1_hash, intro_hash))

    if not generated:
        raise PageContentGenerationError(
            f"no document content generated for filing {filing.id}"
        )

    # 2. Generate filing main content (L2) + intro (L3) — both must succeed.
    l1_hashes = [l1_hash for _, l1_hash, _ in generated]
    main_prompt = ensure_prompt(cfg.prompt_path("filing_main_content"), prompts_dir)
    mc_main = ensure_stage_model_config("l2_filing_main_content", prompts_dir)
    main_hash, main_ok = generate_page_content(
        "filing_main_content",
        l1_hashes,
        main_prompt,
        mc_main,
        filing_id=filing.id,
        form_type=form,
        force=force,
    )
    if not main_ok:
        raise PageContentGenerationError(
            f"filing main content failed for filing {filing.id}"
        )

    intro_prompt = ensure_prompt(cfg.prompt_path("filing_intro"), prompts_dir)
    mc_intro = ensure_stage_model_config("l3_filing_intro_content", prompts_dir)
    intro_hash, intro_ok = generate_page_content(
        "filing_intro",
        [main_hash],
        intro_prompt,
        mc_intro,
        filing_id=filing.id,
        form_type=form,
        force=force,
    )
    if not intro_ok:
        raise PageContentGenerationError(f"filing intro failed for filing {filing.id}")

    # 3. All generation succeeded — publish the document pages + the filing page.
    for document, l1_hash, doc_intro_hash in generated:
        publish_document_page_content(
            document.id, summary_hash=l1_hash, intro_hash=doc_intro_hash
        )
    page = publish_filing_page_content(
        filing.id,
        main_hash=main_hash,
        intro_hash=intro_hash,
        source_document_ids=[doc.id for doc, _, _ in generated],
    )
    logger.info(
        "filing_page_content_pipeline_done",
        filing_id=str(filing.id),
        documents=len(generated),
        page_id=str(page.id),
    )
    return page


def _published_l1_summary_hashes(filings: List, doc_type_str: str) -> List[str]:
    """L1 summary hashes from the *published* document pages for one doc type.

    Gathers each filing's current DocumentPageContent summary slot (in the order
    given). A section genuinely absent from a filing is skipped; but a document
    that exists without a published page summary raises PageContentGenerationError
    — the company page must not synthesize from content that isn't itself
    available on the site.
    """
    doc_type = DocumentType(doc_type_str)
    hashes: List[str] = []
    for filing in filings:
        document = select_substantive_document(filing.documents, doc_type)
        if document is None or not document.content_hash:
            continue  # section not present in this filing — not a missing dependency
        page = get_current_document_page_content(document.id)
        summary = page.summary_content if page else None
        if summary is None or not summary.content_hash:
            raise PageContentGenerationError(
                f"document page content missing for {doc_type_str} in filing "
                f"{filing.id}; generate the filing page content first"
            )
        hashes.append(summary.content_hash)
    return hashes


def _generate_change_report(
    company,
    filings: List,
    doc_type_str: str,
    prompts_dir: Optional[Path],
) -> Optional[Tuple[str, str]]:
    """Generate an L2 change report + L3 intro for one document type (no publish).

    Aggregates the *already-published* L1 summaries for ``doc_type_str`` across
    ``filings`` (ordered oldest -> newest so the change narrative reads
    chronologically). Returns ``(change_report_hash, intro_hash)``, or ``None``
    if the section is genuinely absent across the lookback. Raises
    PageContentGenerationError if a dependency summary is missing or a generation
    step fails (all-or-nothing).
    """
    cfg = load_pipeline_config(prompts_dir)
    ticker = company.ticker
    form = filings[0].form if filings else COMPANY_CHANGE_REPORT_FORM

    hashes = _published_l1_summary_hashes(filings, doc_type_str)
    if not hashes:
        return None  # section not present in any of the lookback filings

    # L2: change report aggregating the published L1 summaries.
    cr_prompt = ensure_prompt(cfg.prompt_path("change_report"), prompts_dir)
    mc_cr = ensure_stage_model_config("l2_change_report_content", prompts_dir)
    cr_hash, cr_ok = generate_page_content(
        "change_report",
        hashes,
        cr_prompt,
        mc_cr,
        ticker=ticker,
        document_type=doc_type_str,
        form_type=form,
    )
    if not cr_ok:
        raise PageContentGenerationError(
            f"change report failed for {doc_type_str} ({ticker})"
        )

    # L3: brief introduction to the change report.
    cri_prompt = ensure_prompt(cfg.prompt_path("change_report_intro"), prompts_dir)
    mc_cri = ensure_stage_model_config("l3_change_report_intro_content", prompts_dir)
    cri_hash, cri_ok = generate_page_content(
        "change_report_intro",
        [cr_hash],
        cri_prompt,
        mc_cri,
        ticker=ticker,
        document_type=doc_type_str,
        form_type=form,
    )
    if not cri_ok:
        raise PageContentGenerationError(
            f"change report intro failed for {doc_type_str} ({ticker})"
        )
    return cr_hash, cri_hash


def company_page_content_pipeline(
    company,
    lookback: int = DEFAULT_COMPANY_LOOKBACK,
    form: str = COMPANY_CHANGE_REPORT_FORM,
    prompts_dir: Optional[Path] = None,
):
    """Publish a CompanyPageContent version for one company.

    Pure synthesis over *already-published* page content: for the company's most
    recent ``lookback`` ``form`` filings it requires each filing to have a
    published FilingPageContent and each constituent document a published
    DocumentPageContent, then builds a per-document-type change report (+intro),
    the company main content (L3, from the business-description change report)
    and a company intro (L4). Only after all of that succeeds is a new immutable
    CompanyPageContent published.

    Raises PageContentGenerationError if there are no filings, if any source
    filing or document page is missing (so the company page never cites analysis
    that isn't itself on the site), or if a generation step fails.
    """
    from symbology.database.base import get_db_session
    from symbology.database.filings import Filing

    cfg = load_pipeline_config(prompts_dir)
    session = get_db_session()

    # Most recent `lookback` filings, newest first (for provenance + selection).
    filings_desc = (
        session.query(Filing)
        .filter(Filing.company_id == company.id, Filing.form == form)
        .order_by(Filing.period_of_report.desc().nullslast(), Filing.filing_date.desc())
        .limit(lookback)
        .all()
    )
    if not filings_desc:
        raise PageContentGenerationError(
            f"no {form} filings for company {company.id} ({company.ticker})"
        )

    # Dependency gate: every source filing must already be published as a page.
    missing_pages = [
        f for f in filings_desc if get_current_filing_page_content(f.id) is None
    ]
    if missing_pages:
        missing_ids = [str(f.id) for f in missing_pages]
        raise FilingPageContentNotReady(
            f"{len(missing_pages)} of {len(filings_desc)} source filings for "
            f"{company.ticker} lack published filing page content "
            f"({missing_ids}); generate it first",
            missing_filing_ids=missing_ids,
        )

    # Chronological order (oldest first) for change-report narratives.
    filings_chrono = list(reversed(filings_desc))

    # 1. Change report (+intro) per document type. Missing document pages raise
    #    (via _published_l1_summary_hashes); a section absent from every filing
    #    is simply skipped.
    doc_types = cfg.form_document_types.get(form, [])
    change_reports: Dict[str, Tuple[str, str]] = {}
    for doc_type_str in doc_types:
        result = _generate_change_report(
            company, filings_chrono, doc_type_str, prompts_dir
        )
        if result is not None:
            change_reports[doc_type_str] = result

    if not change_reports:
        raise PageContentGenerationError(
            f"no change reports generated for company {company.ticker}"
        )

    # 2. Company main content (L3) from the business-description change report.
    bd = change_reports.get("business_description")
    if bd is None:
        raise PageContentGenerationError(
            f"business_description change report required for {company.ticker} main content"
        )
    bd_cr_hash, _ = bd
    main_prompt = ensure_prompt(cfg.prompt_path("company_main_content"), prompts_dir)
    mc_main = ensure_stage_model_config("l3_company_main_content", prompts_dir)
    main_hash, main_ok = generate_page_content(
        "company_main_content",
        [bd_cr_hash],
        main_prompt,
        mc_main,
        ticker=company.ticker,
        form_type=form,
    )
    if not main_ok:
        raise PageContentGenerationError(
            f"company main content failed for {company.ticker}"
        )

    # 3. Company intro (L4) from the main content.
    intro_prompt = ensure_prompt(cfg.prompt_path("company_intro"), prompts_dir)
    mc_intro = ensure_stage_model_config("l4_company_intro_content", prompts_dir)
    intro_hash, intro_ok = generate_page_content(
        "company_intro",
        [main_hash],
        intro_prompt,
        mc_intro,
        ticker=company.ticker,
        form_type=form,
    )
    if not intro_ok:
        raise PageContentGenerationError(
            f"company intro failed for {company.ticker}"
        )

    # 4. All generation succeeded — publish the company page version.
    page = publish_company_page_content(
        company.id,
        main_hash=main_hash,
        intro_hash=intro_hash,
        change_reports=change_reports,
        source_filing_ids=[f.id for f in filings_desc],
    )

    # 5. Precompute the structured year-over-year diffs for the latest filing pair.
    #    Non-fatal and summary-free here (a separate COMPANY_DIFF job can add the
    #    per-topic LLM summaries): a diff failure must not block page publication.
    try:
        from symbology.worker.diff_pipeline import company_diff_pipeline
        company_diff_pipeline(company, form=form, prompts_dir=prompts_dir, generate_summaries=False)
    except Exception as e:
        logger.error("company_page_diff_failed", company_id=str(company.id),
                     error=str(e), exc_info=True)
    logger.info(
        "company_page_content_pipeline_done",
        company_id=str(company.id),
        ticker=company.ticker,
        change_reports=len(change_reports),
        source_filings=len(filings_desc),
        page_id=str(page.id),
    )
    return page
