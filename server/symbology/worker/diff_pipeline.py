"""Year-over-year section diff pipeline.

Aligns the chunks of a ``(company, document_type)`` section between the two most
recent ``form`` filings by their stable ``topic_id``, computes a word-level diff
per aligned topic, classifies each change, and persists a :class:`DiffSet` with
its :class:`SectionDiff` rows. Optionally generates a short per-topic "what
changed" summary via the LLM (non-fatal).

This is pure synthesis over already chunked+clustered data (run the filing page
pipeline / backfill first). It is idempotent per filing pair: the prior diff set
for the pair is replaced on each run.
"""
import re
from pathlib import Path
from typing import Dict, List, Optional

from symbology.database.base import get_db_session
from symbology.database.chunk_topics import is_noise_label
from symbology.database.document_chunks import DocumentChunk, get_chunks_by_document
from symbology.database.documents import Document, DocumentType
from symbology.database.filings import Filing
from symbology.database.section_diffs import (
    delete_diff_sets_for_pair,
    DiffSet,
    SectionDiff,
)
from symbology.utils import text_diff
from symbology.utils.logging import get_logger

logger = get_logger(__name__)

# Cap stored ops per section to bound JSON size; the UI shows a "truncated" note.
MAX_OPS = 400

# Display order for the change cards (mirrors the mockup's New / Escalated / …).
_KIND_ORDER = {
    text_diff.NEW: 0,
    text_diff.ESCALATED: 1,
    text_diff.DE_EMPHASISED: 2,
    text_diff.REWORDED: 3,
    text_diff.REMOVED: 4,
    text_diff.UNCHANGED: 5,
}

# Max topics to LLM-summarise per filing diff. Summaries are one LLM call each,
# so a filing with 100+ changed topics is slow; we rank by significance and
# summarise only the most material. Override per-job with the ``max_summaries``
# param. Mirrors the UI's ``scoreSectionDiff`` ranking.
MAX_TOPIC_SUMMARIES = 6

_KIND_WEIGHT = {
    text_diff.NEW: 1000,
    text_diff.REMOVED: 900,
    text_diff.ESCALATED: 600,
    text_diff.DE_EMPHASISED: 500,
    text_diff.REWORDED: 200,
    text_diff.UNCHANGED: 0,
}


def _significance(sd) -> float:
    """Heuristic 'analyst significance' of a section diff (kind + edit volume)."""
    kind = _KIND_WEIGHT.get(sd.change_kind, 100)
    return kind + (sd.tokens_added or 0) + (sd.tokens_removed or 0) + abs(sd.length_delta or 0) * 0.1


# Change kinds the UI actually surfaces (cards + side-by-side): shifts in emphasis /
# wording of existing disclosures. Brand-new and removed topics are not shown — and
# a per-topic "what changed" summary (prior vs current prose) is meaningless for them
# anyway — so they aren't worth an LLM call. Mirrors VISIBLE_KINDS in
# ui/src/lib/utils/changes.ts.
DISPLAYED_CHANGE_KINDS = frozenset(
    {text_diff.ESCALATED, text_diff.DE_EMPHASISED, text_diff.REWORDED}
)

# Numeric-noise gate, mirroring isNumericNoise() in ui/src/lib/utils/changes.ts: a
# change whose *edited* text is essentially just figures (year-over-year tables where
# only the numbers moved) is hidden on-page, so it isn't summarised either.
_NUMERIC_NOISE_MIN_CHARS = 8
_NUMERIC_NOISE_MAX_ALPHA = 0.2


def _is_numeric_noise(ops) -> bool:
    if not ops:
        return False
    changed = "".join(o.get("text", "") for o in ops if o.get("op") != "equal")
    letters = len(re.findall(r"[^\W\d_]", changed))
    digits = len(re.findall(r"\d", changed))
    if digits == 0 or letters + digits < _NUMERIC_NOISE_MIN_CHARS:
        return False
    return letters / (letters + digits) < _NUMERIC_NOISE_MAX_ALPHA


def is_displayed_change(sd) -> bool:
    """Whether a SectionDiff is one the UI shows — and thus worth summarising.

    Mirrors ``isVisibleTopic`` in the UI: an emphasis/wording shift (DISPLAYED_CHANGE_KINDS)
    whose change is more than just figures. Keeps the per-topic summary budget aimed
    at exactly the topics that appear as change cards / list rows, instead of spending
    it on never-shown new/removed (or figures-only) rows.
    """
    return sd.change_kind in DISPLAYED_CHANGE_KINDS and not _is_numeric_noise(sd.ops)


def _document_for(filing_id, document_type: DocumentType) -> Optional[Document]:
    session = get_db_session()
    return (
        session.query(Document)
        .filter(Document.filing_id == filing_id, Document.document_type == document_type)
        .first()
    )


def _topic_representatives(filing_id, document_type: DocumentType):
    """Per-topic representative chunk + display label for a filing's section.

    Returns ``(reps, labels)`` where ``reps`` maps ``topic_id -> representative
    DocumentChunk`` (the longest chunk if a topic has several on one side, e.g.
    an item split) and ``labels`` maps ``topic_id -> readable heading``.

    The label prefers the representative's own heading, but falls back to any
    *other* member chunk's readable heading when the representative's is a
    separator artifact (e.g. ``"__________"``). It stays ``None`` only if no
    member has a readable heading — the UI then shows the section path. Only
    semantic, clustered, non-empty chunks participate.
    """
    document = _document_for(filing_id, document_type)
    if document is None:
        return {}, {}
    reps: Dict = {}
    readable_headings: Dict = {}  # topic_id -> first readable member heading
    for chunk in get_chunks_by_document(document.id):
        if not chunk.is_semantic or chunk.topic_id is None or not chunk.content:
            continue
        current = reps.get(chunk.topic_id)
        if current is None or len(chunk.content) > len(current.content):
            reps[chunk.topic_id] = chunk
        if chunk.topic_id not in readable_headings and chunk.heading and not is_noise_label(chunk.heading):
            readable_headings[chunk.topic_id] = chunk.heading

    labels: Dict = {}
    for topic_id, rep in reps.items():
        if rep.heading and not is_noise_label(rep.heading):
            labels[topic_id] = rep.heading
        else:
            labels[topic_id] = readable_headings.get(topic_id)
    return reps, labels


def _entry_from_matched(left: DocumentChunk, right: DocumentChunk, heading: Optional[str]) -> List[dict]:
    """Build section-diff entry dict(s) for a topic present in both filings.

    Normally one entry; if the two texts are so different they're likely a false
    merge of unrelated topics, split into a REMOVED + a NEW entry instead.
    """
    ops, added, removed = text_diff.compute_token_diff(left.content, right.content)
    if text_diff.edit_ratio(left.content, right.content, ops) > text_diff.FALSE_MERGE_RATIO:
        return [
            _entry_removed(left, heading),
            _entry_new(right, heading),
        ]
    kind = text_diff.classify_change(left.content, right.content, ops)
    return [{
        "topic_id": right.topic_id,
        "section_path": right.section_path,
        "heading": heading,
        "change_kind": kind,
        "ops": ops,
        "left_chunk_id": left.id,
        "right_chunk_id": right.id,
        "length_delta": len(right.content) - len(left.content),
        "tokens_added": added,
        "tokens_removed": removed,
        "left_text": left.content,
        "right_text": right.content,
    }]


def _entry_new(right: DocumentChunk, heading: Optional[str]) -> dict:
    return {
        "topic_id": right.topic_id,
        "section_path": right.section_path,
        "heading": heading,
        "change_kind": text_diff.NEW,
        "ops": [{"op": "insert", "text": right.content}],
        "left_chunk_id": None,
        "right_chunk_id": right.id,
        "length_delta": len(right.content),
        "tokens_added": len(right.content.split()),
        "tokens_removed": 0,
        "left_text": None,
        "right_text": right.content,
    }


def _entry_removed(left: DocumentChunk, heading: Optional[str]) -> dict:
    return {
        "topic_id": left.topic_id,
        "section_path": left.section_path,
        "heading": heading,
        "change_kind": text_diff.REMOVED,
        "ops": [{"op": "delete", "text": left.content}],
        "left_chunk_id": left.id,
        "right_chunk_id": None,
        "length_delta": -len(left.content),
        "tokens_added": 0,
        "tokens_removed": len(left.content.split()),
        "left_text": left.content,
        "right_text": None,
    }


def _diff_one_doctype(
    company,
    document_type: DocumentType,
    left_filing: Filing,
    right_filing: Filing,
    form: str,
) -> Optional[DiffSet]:
    """Compute + persist the diff set for one document type between two filings."""
    left_reps, left_labels = _topic_representatives(left_filing.id, document_type)
    right_reps, right_labels = _topic_representatives(right_filing.id, document_type)
    if not left_reps and not right_reps:
        return None

    entries: List[dict] = []
    for topic_id in left_reps.keys() | right_reps.keys():
        left, right = left_reps.get(topic_id), right_reps.get(topic_id)
        # Display label: prefer the newer (right) side's readable heading, fall
        # back to the older side. Each side already substitutes a readable member
        # heading for a "__________" separator artifact, or None → section path.
        heading = right_labels.get(topic_id) or left_labels.get(topic_id)
        if left is not None and right is not None:
            entries.extend(_entry_from_matched(left, right, heading))
        elif right is not None:
            entries.append(_entry_new(right, heading))
        else:
            entries.append(_entry_removed(left, heading))

    # Order for display, then assign ordinals.
    entries.sort(key=lambda e: (_KIND_ORDER.get(e["change_kind"], 9), e["section_path"] or ""))

    counts: Dict[str, int] = {}
    for e in entries:
        counts[e["change_kind"]] = counts.get(e["change_kind"], 0) + 1
    counts["total_compared"] = len(entries)

    session = get_db_session()
    delete_diff_sets_for_pair(company.id, document_type, left_filing.id, right_filing.id)
    diff_set = DiffSet(
        company_id=company.id,
        document_type=document_type,
        form=form,
        left_filing_id=left_filing.id,
        right_filing_id=right_filing.id,
        counts=counts,
        diff_lib="difflib-word",
    )
    session.add(diff_set)
    session.flush()

    for ordinal, e in enumerate(entries):
        ops = e["ops"]
        truncated = len(ops) > MAX_OPS
        session.add(SectionDiff(
            diff_set_id=diff_set.id,
            ordinal=ordinal,
            topic_id=e["topic_id"],
            section_path=e["section_path"],
            heading=e["heading"],
            change_kind=e["change_kind"],
            ops=ops[:MAX_OPS] if truncated else ops,
            left_chunk_id=e["left_chunk_id"],
            right_chunk_id=e["right_chunk_id"],
            length_delta=e["length_delta"],
            tokens_added=e["tokens_added"],
            tokens_removed=e["tokens_removed"],
            truncated=truncated,
        ))
    session.commit()
    logger.info(
        "diff_set_published",
        company_id=str(company.id), document_type=document_type.value,
        diff_set_id=str(diff_set.id), entries=len(entries), counts=counts,
    )
    return diff_set


def filing_diff_pipeline(
    left_filing: Filing,
    right_filing: Filing,
    form: str,
    prompts_dir: Optional[Path] = None,
    generate_summaries: bool = False,
    max_summaries: int = MAX_TOPIC_SUMMARIES,
) -> List[DiffSet]:
    """Diff an explicit ordered filing pair (``left`` older, ``right`` newer).

    Produces one :class:`DiffSet` per document type (per ``form_document_types``)
    for the pair, replacing any prior diff sets for it. Both filings must already
    be chunked+clustered. Returns the published diff sets (possibly empty if the
    section has no clustered chunks on either side).
    """
    from symbology.worker.config_loader import load_pipeline_config

    company = right_filing.company
    cfg = load_pipeline_config(prompts_dir)
    doc_types = cfg.form_document_types.get(form, [])

    diff_sets: List[DiffSet] = []
    for doc_type_str in doc_types:
        try:
            diff_set = _diff_one_doctype(
                company, DocumentType(doc_type_str), left_filing, right_filing, form
            )
            if diff_set is not None:
                diff_sets.append(diff_set)
        except Exception as e:
            logger.error("filing_diff_doctype_failed", company_id=str(company.id),
                         document_type=doc_type_str, error=str(e), exc_info=True)

    if generate_summaries:
        _generate_topic_summaries(company, diff_sets, form, prompts_dir, max_summaries)

    return diff_sets


def _previous_period_pair(session, company):
    """The latest 10-Q and the periodic filing immediately before it.

    A 10-K stands in for Q4 (no Q4 10-Q is filed), so the period *before* a
    quarter is the prior quarter of its cycle, or — for the first quarter after
    an annual — the 10-K itself. The older side is therefore the most recent
    10-K/10-Q filed before the latest 10-Q, which never straddles the annual to a
    quarter of the previous cycle. Returns ``(left, right)`` (older, newer); either
    may be ``None`` when there aren't enough filings.
    """
    filings = (
        session.query(Filing)
        .filter(Filing.company_id == company.id, Filing.form.in_(["10-K", "10-Q"]))
        .order_by(Filing.period_of_report.desc().nullslast(), Filing.filing_date.desc())
        .all()
    )

    def _key(f):
        return f.period_of_report or f.filing_date

    right = next((f for f in filings if f.form == "10-Q"), None)
    if right is None:
        return None, None
    rkey = _key(right)
    left = next(
        (f for f in filings if f.id != right.id and _key(f) and rkey and _key(f) < rkey),
        None,
    )
    return left, right


def company_diff_pipeline(
    company,
    form: str = "10-K",
    prompts_dir: Optional[Path] = None,
    generate_summaries: bool = False,
    max_summaries: int = MAX_TOPIC_SUMMARIES,
) -> List[DiffSet]:
    """Compute the most recent period-over-period diffs for a company.

    Thin wrapper over :func:`filing_diff_pipeline`. For an annual page (10-K) this
    is the two most recent 10-Ks (year over year). For a quarterly page (10-Q) the
    latest 10-Q is paired with the periodic filing immediately before it — the
    prior quarter, or the anchoring 10-K when it's the first quarter after an
    annual — so the diff never straddles the annual (see ``_previous_period_pair``).
    Returns the published diff sets (empty if there's no comparable pair).
    """
    session = get_db_session()
    if form == "10-Q":
        left_filing, right_filing = _previous_period_pair(session, company)
    else:
        filings = (
            session.query(Filing)
            .filter(Filing.company_id == company.id, Filing.form == form)
            .order_by(Filing.period_of_report.desc().nullslast(), Filing.filing_date.desc())
            .limit(2)
            .all()
        )
        right_filing = filings[0] if filings else None
        left_filing = filings[1] if len(filings) >= 2 else None

    if left_filing is None or right_filing is None:
        logger.info("company_diff_pipeline_insufficient_filings",
                    company_id=str(company.id), form=form)
        return []
    return filing_diff_pipeline(
        left_filing, right_filing, form, prompts_dir, generate_summaries, max_summaries
    )


def summarize_diff_set(
    diff_set: DiffSet,
    company,
    form: str,
    max_summaries: Optional[int] = MAX_TOPIC_SUMMARIES,
    prompts_dir=None,
    force: bool = False,
) -> int:
    """LLM-summarise the most significant *unsummarised* changed topics in one diff set.

    Ranks the set's changed topics by :func:`_significance` and summarises the top
    ``max_summaries`` that don't already have a summary (pass ``None`` for no cap),
    setting each ``summary_content_id``. Resume-friendly: already-summarised topics
    are skipped, so retries / re-runs don't redo work. Each summary is one LLM call
    (direct — the page-content generator only accepts GeneratedContent sources, not
    raw chunk text); non-fatal per topic. Returns the number summarised.

    Decoupled from the structural diff so it can run as its own low-priority
    DIFF_SUMMARY job, keeping the diff itself available without waiting on LLM calls.
    """
    from symbology.database.generated_content import ContentStage, create_generated_content
    from symbology.llm.client import remove_thinking_tags
    from symbology.worker.config_loader import (
        ensure_stage_model_config,
        generate_with_overflow,
        load_pipeline_config,
    )
    from symbology.worker.pipeline import ensure_prompt

    session = get_db_session()
    cfg = load_pipeline_config(prompts_dir)
    try:
        system_prompt = ensure_prompt(cfg.prompt_path("topic_diff_summary"), prompts_dir)
        base_model_config = ensure_stage_model_config("l2_topic_diff_summary", prompts_dir)
    except Exception as e:
        logger.error("topic_summary_setup_failed", error=str(e), exc_info=True)
        return 0

    # Rank the set's *displayed*, not-yet-summarised topics; summarise only the most
    # significant `max_summaries`. Restricting to displayed topics (vs all changed)
    # keeps the budget on the rows that actually appear as change cards / list items,
    # so cards reliably get prose instead of the budget being spent on never-shown
    # new/removed (or figures-only) topics.
    # Normally skip topics that already have a summary; ``force`` re-summarises every
    # displayed topic (replacing the old summary_content_id) — e.g. to backfill blanks
    # left by an earlier failed/empty run.
    candidates = [
        sd for sd in diff_set.section_diffs
        if is_displayed_change(sd) and (force or sd.summary_content_id is None)
    ]
    candidates.sort(key=_significance, reverse=True)
    selected = candidates if max_summaries is None else candidates[:max_summaries]
    logger.info("topic_summaries_selected", diff_set_id=str(diff_set.id),
                total_changed=len(candidates), summarising=len(selected),
                max_summaries=max_summaries)

    summarized = 0
    for sd in selected:
        # Feed the *full* topic text on each side (all of the topic's clustered
        # chunks), not just the representative chunk — a single chunk (e.g. one table
        # row) often lacks the context needed to describe the change.
        prev_text = _topic_text(diff_set.left_filing_id, diff_set.document_type, sd.topic_id) \
            or "(not present in the prior filing)"
        curr_text = _topic_text(diff_set.right_filing_id, diff_set.document_type, sd.topic_id) \
            or "(removed — not present in the current filing)"
        user_prompt = (
            f"<prior_period>\n{prev_text}\n</prior_period>\n\n"
            f"<current_period>\n{curr_text}\n</current_period>"
        )
        try:
            # Offload oversized prompts to Anthropic — preemptively and reactively
            # if the local model still overflows. model_config is the one that
            # served the request, recorded on the row below.
            response, warning, model_config = generate_with_overflow(
                base_model_config, system_prompt.content, user_prompt
            )
            # Strip any reasoning tags and require real prose. A reasoning model that
            # runs out of tokens mid-think returns empty content — don't store that
            # (it would render a blank card) and don't mark the topic summarised, so a
            # later DIFF_SUMMARY run can retry it instead of skipping it forever.
            summary_text = (remove_thinking_tags(response.response) or "").strip()
            if not summary_text:
                logger.warning("topic_summary_empty", section_diff_id=str(sd.id),
                               output_tokens=response.output_tokens)
                continue
            generated, _ = create_generated_content({
                "content": summary_text,
                "company_id": company.id,
                "filing_id": diff_set.right_filing_id,
                "document_type": diff_set.document_type,
                "form_type": form,
                "content_stage": ContentStage.TOPIC_DIFF_SUMMARY,
                "description": f"topic diff summary: {sd.heading or sd.section_path}",
                "source_type": "documents",
                "model_config_id": model_config.id,
                "system_prompt_id": system_prompt.id,
                "total_duration": response.total_duration,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "warning": warning,
            })
            sd.summary_content_id = generated.id
            session.commit()
            summarized += 1
        except Exception as e:
            session.rollback()
            logger.error("topic_summary_failed", section_diff_id=str(sd.id),
                         error=str(e), exc_info=True)
    return summarized


def _topic_text(filing_id, document_type: DocumentType, topic_id) -> str:
    """The full text of one topic on one side: its clustered chunks, concatenated.

    Returns "" when the filing/topic is absent or the section has no clustered chunks
    for that topic (e.g. a topic present only on the other side).
    """
    if filing_id is None or topic_id is None:
        return ""
    document = _document_for(filing_id, document_type)
    if document is None:
        return ""
    parts = [
        chunk.content
        for chunk in get_chunks_by_document(document.id)
        if chunk.topic_id == topic_id and chunk.content
    ]
    return "\n\n".join(parts)


def _generate_topic_summaries(
    company,
    diff_sets: List[DiffSet],
    form: str,
    prompts_dir,
    max_summaries: int = MAX_TOPIC_SUMMARIES,
) -> None:
    """Inline summariser kept for direct pipeline use (e.g. ``filing_diff_pipeline``
    with ``generate_summaries=True``). Summarises each diff set's top topics; the
    job path uses :func:`summarize_diff_set` per set instead."""
    for ds in diff_sets:
        summarize_diff_set(ds, company, form, max_summaries=max_summaries, prompts_dir=prompts_dir)
