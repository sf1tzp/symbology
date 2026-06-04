"""Within-company topic clustering for document chunks.

Gives each section chunk a **stable cross-filing identity** (``topic_id``) by
clustering its embedding against the topics already seen for the same
``(company, document_type)``. The same risk factor then carries the same topic
across years even as its number/heading drift — which is what makes
year-over-year diffing align.

Two entry points:

* :func:`assign_unclustered_chunks` — the incremental path, run after a single
  document is chunked+embedded. Only assigns chunks that don't already have a
  topic (carry-forward-by-content-hash in ``replace_document_chunks`` keeps an
  unchanged document a no-op, so re-chunking never churns topic ids).
* :func:`recluster_company_doctype` — the recompute-from-scratch repair/backfill
  path: drop the scope's topics and re-derive them from the *current* chunk set
  (cheap, because embeddings are cached on the chunk rows — no re-embedding).

Centroids update as a running mean (see :func:`~symbology.database.chunk_topics.add_member_to_topic`);
they are never re-fit, so existing assignments are never reshuffled.

Design notes:
* Chunks are processed in a deterministic order (oldest filing first, then
  ``chunk_index``) so a topic's centroid anchors on its earliest occurrence.
* The session uses ``autoflush=False`` (see ``database.base``), so we flush
  explicitly after each assignment — otherwise the next nearest-centroid query
  wouldn't see a topic created earlier in the same batch.
* Non-semantic (paragraph-fallback) chunks and chunks whose embedding failed are
  left unclustered (``topic_id`` stays NULL); diffing handles them as unaligned.
"""
from typing import Dict, Sequence, Union
from uuid import UUID

from symbology.database.base import get_db_session
from symbology.database.chunk_topics import (
    add_member_to_topic,
    create_chunk_topic,
    delete_topics_for_scope,
    is_noise_label,
    nearest_topic,
)
from symbology.database.document_chunks import DocumentChunk, get_chunks_for_company_doctype
from symbology.database.documents import DocumentType
from symbology.utils.logging import get_logger

logger = get_logger(__name__)

# Cosine *distance* below which a chunk joins an existing topic (distance =
# 1 - cosine_similarity for unit vectors). Model-dependent, so sourced from
# config (default 0.05, tuned for nomic-embed-text on same-company same-section
# text — see settings.openai.topic_distance_threshold). Read at call time so the
# value stays auditable and overridable via OPENAI_TOPIC_DISTANCE_THRESHOLD.
from symbology.utils.config import settings as _settings #noqa E402


def _threshold() -> float:
    return _settings.openai.topic_distance_threshold


# Module-level snapshot of the configured default (exported for introspection
# and tests); the clustering logic calls _threshold() so runtime overrides apply.
TOPIC_DISTANCE_THRESHOLD = _settings.openai.topic_distance_threshold


def _assign(
    company_id: Union[UUID, str],
    document_type: DocumentType,
    chunk: DocumentChunk,
) -> str:
    """Attach ``chunk`` to its nearest topic, or create a new one. Returns the
    action taken: ``"attached"`` or ``"created"``. Caller flushes."""
    embedding = list(chunk.embedding)
    match = nearest_topic(company_id, document_type, embedding)
    if match is not None and match[1] <= _threshold():
        topic, _distance = match
        add_member_to_topic(topic, embedding, commit=False)
        chunk.topic_id = topic.id
        return "attached"
    topic = create_chunk_topic(
        company_id,
        document_type,
        embedding,
        # Don't seed the label with a separator artifact (e.g. "__________"); a
        # later readable member heading is preferred when the topic is displayed.
        canonical_label=None if is_noise_label(chunk.heading) else chunk.heading,
        commit=False,
    )
    chunk.topic_id = topic.id
    return "created"


def assign_unclustered_chunks(
    company_id: Union[UUID, str],
    document_type: DocumentType,
    chunks: Sequence[DocumentChunk],
) -> Dict[str, int]:
    """Assign a topic to each chunk that lacks one (incremental path).

    ``chunks`` should be ordered (oldest filing first, then ``chunk_index``).
    Already-clustered, non-semantic, and unembedded chunks are left untouched.
    """
    session = get_db_session()
    created = attached = skipped = 0
    for chunk in chunks:
        if chunk.topic_id is not None:
            continue
        if not chunk.is_semantic or chunk.embedding is None:
            skipped += 1
            continue
        action = _assign(company_id, document_type, chunk)
        # autoflush is off — make this assignment visible to the next query.
        session.flush()
        if action == "created":
            created += 1
        else:
            attached += 1
    session.commit()
    result = {"created": created, "attached": attached, "skipped": skipped}
    logger.info(
        "assigned_chunk_topics",
        company_id=str(company_id),
        document_type=document_type.value if document_type else None,
        **result,
    )
    return result


def recluster_company_doctype(
    company_id: Union[UUID, str], document_type: DocumentType
) -> Dict[str, int]:
    """Recompute all topics for a scope from scratch (repair/backfill path).

    Drops the scope's existing topics (chunks' ``topic_id`` → NULL via the FK),
    then re-derives topics from the current chunk set in deterministic order.
    Idempotent: clustering becomes a pure function of the current chunks, so
    stale members can't accumulate and re-runs converge to the same result.
    """
    delete_topics_for_scope(company_id, document_type)
    # The topic delete nulls chunks' topic_id in the DB via the FK, but that
    # bypasses the session (synchronize_session=False). Expire cached objects so
    # the re-fetch reflects topic_id = NULL and every chunk is reconsidered.
    get_db_session().expire_all()
    chunks = get_chunks_for_company_doctype(company_id, document_type)
    return assign_unclustered_chunks(company_id, document_type, chunks)
