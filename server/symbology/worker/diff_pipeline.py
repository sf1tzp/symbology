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
MAX_TOPIC_SUMMARIES = 10

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


def company_diff_pipeline(
    company,
    form: str = "10-K",
    prompts_dir: Optional[Path] = None,
    generate_summaries: bool = False,
    max_summaries: int = MAX_TOPIC_SUMMARIES,
) -> List[DiffSet]:
    """Compute year-over-year diffs for a company's most recent ``form`` filing pair.

    Thin wrapper over :func:`filing_diff_pipeline` that resolves the two most
    recent ``form`` filings. Returns the published diff sets (empty if <2 filings).
    """
    session = get_db_session()
    filings = (
        session.query(Filing)
        .filter(Filing.company_id == company.id, Filing.form == form)
        .order_by(Filing.period_of_report.desc().nullslast(), Filing.filing_date.desc())
        .limit(2)
        .all()
    )
    if len(filings) < 2:
        logger.info("company_diff_pipeline_insufficient_filings",
                    company_id=str(company.id), form=form, filings=len(filings))
        return []
    right_filing, left_filing = filings[0], filings[1]
    return filing_diff_pipeline(
        left_filing, right_filing, form, prompts_dir, generate_summaries, max_summaries
    )


def _generate_topic_summaries(
    company,
    diff_sets: List[DiffSet],
    form: str,
    prompts_dir,
    max_summaries: int = MAX_TOPIC_SUMMARIES,
) -> None:
    """LLM-summarise the most significant changed topics across a filing's sections.

    Each summary is one LLM call, so a filing with 100+ changed topics is slow.
    We rank every changed topic by :func:`_significance` and summarise only the
    top ``max_summaries`` (pass ``None`` for no cap); the rest keep
    ``summary_content_id`` NULL and the UI falls back to heading/section path.
    Direct LLM call (the page-content generator only accepts GeneratedContent
    sources, not raw chunk text). Non-fatal per topic.
    """
    from symbology.database.generated_content import ContentStage, create_generated_content
    from symbology.llm.client import get_generate_response
    from symbology.worker.config_loader import (
        ensure_stage_model_config,
        load_pipeline_config,
        resolve_generation_model_config,
    )
    from symbology.worker.pipeline import ensure_prompt

    session = get_db_session()
    cfg = load_pipeline_config(prompts_dir)
    try:
        system_prompt = ensure_prompt(cfg.prompt_path("topic_diff_summary"), prompts_dir)
        base_model_config = ensure_stage_model_config("l2_topic_diff_summary", prompts_dir)
    except Exception as e:
        logger.error("topic_summary_setup_failed", error=str(e), exc_info=True)
        return

    # Rank all changed topics across the filing's sections; summarise only the
    # most significant `max_summaries` to bound LLM calls.
    candidates = [
        (ds, sd)
        for ds in diff_sets
        for sd in ds.section_diffs
        if sd.change_kind != text_diff.UNCHANGED
    ]
    candidates.sort(key=lambda pair: _significance(pair[1]), reverse=True)
    selected = candidates if max_summaries is None else candidates[:max_summaries]
    logger.info("topic_summaries_selected", total_changed=len(candidates),
                summarising=len(selected), max_summaries=max_summaries)

    for diff_set, sd in selected:
        left = session.get(DocumentChunk, sd.left_chunk_id) if sd.left_chunk_id else None
        right = session.get(DocumentChunk, sd.right_chunk_id) if sd.right_chunk_id else None
        prev_text = left.content if left else "(not present in the prior filing)"
        curr_text = right.content if right else "(removed — not present in the current filing)"
        user_prompt = (
            f"<prior_period>\n{prev_text}\n</prior_period>\n\n"
            f"<current_period>\n{curr_text}\n</current_period>"
        )
        try:
            model_config = resolve_generation_model_config(
                base_model_config, f"{system_prompt.content}\n{user_prompt}"
            )
            response, warning = get_generate_response(
                model_config, system_prompt.content, user_prompt
            )
            generated, _ = create_generated_content({
                "content": response.response,
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
        except Exception as e:
            session.rollback()
            logger.error("topic_summary_failed", section_diff_id=str(sd.id),
                         error=str(e), exc_info=True)
