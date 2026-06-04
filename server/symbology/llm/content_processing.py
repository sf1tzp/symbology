"""High-level chunk-and-embed helpers for documents and generated content.

Ties together :mod:`symbology.llm.chunking`, :mod:`symbology.llm.embeddings`,
and the chunk database models so a single call turns a Document or
GeneratedContent body into persisted, embedded chunks.

Usage:
    from symbology.llm.content_processing import (
        chunk_and_embed_document,
        chunk_and_embed_generated_content,
    )

    n = chunk_and_embed_document(document_id)
"""
from dataclasses import dataclass
from typing import List, Optional, Union
from uuid import UUID

from openai import OpenAI

from symbology.database.document_chunks import (
    get_chunks_for_company_doctype,
    replace_document_chunks,
    replace_document_section_chunks,
)
from symbology.database.documents import get_document
from symbology.database.generated_content import get_generated_content
from symbology.database.generated_content_chunks import replace_content_chunks
from symbology.llm.chunking import chunk_text
from symbology.llm.embeddings import embed_texts, init_embedding_client
from symbology.llm.section_chunker import chunk_document_sections
from symbology.llm.topic_clustering import assign_unclustered_chunks
from symbology.utils.config import settings
from symbology.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ProcessingResult:
    """Outcome of a chunk-and-embed operation."""
    chunk_count: int
    embedded: bool
    model: str


def _chunk_and_embed_text(
    text: Optional[str],
    client: Optional[OpenAI],
    embed: bool,
) -> tuple[List[str], List[Optional[List[float]]], bool]:
    """Chunk text and (optionally) embed it.

    Returns (chunks, embeddings, embedded). Embedding failure is non-fatal:
    chunks are still returned with ``None`` embeddings so callers can persist
    text now and backfill vectors later.
    """
    chunks = chunk_text(text)
    if not chunks:
        return [], [], False

    if not embed:
        return chunks, [None] * len(chunks), False

    try:
        client = client or init_embedding_client()
        vectors: List[Optional[List[float]]] = list(embed_texts(chunks, client=client))
        return chunks, vectors, True
    except Exception as e:
        logger.error("embedding_failed_chunks_kept", chunk_count=len(chunks), error=str(e), exc_info=True)
        return chunks, [None] * len(chunks), False


def chunk_and_embed_document(
    document_id: Union[UUID, str],
    client: Optional[OpenAI] = None,
    embed: bool = True,
) -> ProcessingResult:
    """Chunk and embed a document's content, replacing any existing chunks.

    Args:
        document_id: The document to process.
        client: Reuse an embedding client (one is created if omitted).
        embed: If ``False``, persist chunks without embeddings.

    Returns:
        A :class:`ProcessingResult` summarising what was written.
    """
    document = get_document(document_id)
    if document is None or not document.content:
        logger.warning("chunk_and_embed_document_no_content", document_id=str(document_id))
        replace_document_chunks(document_id, [], [])
        return ProcessingResult(chunk_count=0, embedded=False, model=settings.openai.embedding_model)

    chunks, embeddings, embedded = _chunk_and_embed_text(document.content, client, embed)
    model = settings.openai.embedding_model if embedded else None
    replace_document_chunks(document_id, chunks, embeddings, embedding_model=model)

    logger.info("chunk_and_embed_document_done", document_id=str(document_id), chunks=len(chunks), embedded=embedded)
    return ProcessingResult(chunk_count=len(chunks), embedded=embedded, model=settings.openai.embedding_model)


def chunk_and_embed_generated_content(
    content_id: Union[UUID, str],
    client: Optional[OpenAI] = None,
    embed: bool = True,
) -> ProcessingResult:
    """Chunk and embed a generated content's body, replacing any existing chunks.

    Args:
        content_id: The generated content to process.
        client: Reuse an embedding client (one is created if omitted).
        embed: If ``False``, persist chunks without embeddings.

    Returns:
        A :class:`ProcessingResult` summarising what was written.
    """
    content = get_generated_content(content_id)
    if content is None or not content.content:
        logger.warning("chunk_and_embed_generated_content_no_content", content_id=str(content_id))
        replace_content_chunks(content_id, [], [])
        return ProcessingResult(chunk_count=0, embedded=False, model=settings.openai.embedding_model)

    chunks, embeddings, embedded = _chunk_and_embed_text(content.content, client, embed)
    model = settings.openai.embedding_model if embedded else None
    replace_content_chunks(content_id, chunks, embeddings, embedding_model=model)

    logger.info("chunk_and_embed_generated_content_done", content_id=str(content_id), chunks=len(chunks), embedded=embedded)
    return ProcessingResult(chunk_count=len(chunks), embedded=embedded, model=settings.openai.embedding_model)


def _embed_or_none(
    texts: List[str], client: Optional[OpenAI], embed: bool
) -> tuple[List[Optional[List[float]]], bool]:
    """Embed already-chunked texts; non-fatal (returns ``None`` vectors on failure)."""
    if not texts:
        return [], False
    if not embed:
        return [None] * len(texts), False
    try:
        client = client or init_embedding_client()
        return list(embed_texts(texts, client=client)), True
    except Exception as e:
        logger.error("embedding_failed_chunks_kept", chunk_count=len(texts), error=str(e), exc_info=True)
        return [None] * len(texts), False


def chunk_embed_and_cluster_document(
    document_id: Union[UUID, str],
    client: Optional[OpenAI] = None,
    embed: bool = True,
    cluster: bool = True,
) -> ProcessingResult:
    """Section-chunk a document, embed each chunk, and assign cross-filing topics.

    This is the section-aware successor to :func:`chunk_and_embed_document`: it
    splits the document into addressable, non-overlapping section chunks
    (:func:`~symbology.llm.section_chunker.chunk_document_sections`), embeds them,
    persists with ``content_hash`` carry-forward of ``topic_id``, then runs
    incremental within-company topic clustering over the scope.

    Each step is non-fatal: embedding failure still persists chunks (with ``None``
    vectors); clustering failure leaves ``topic_id`` NULL for later backfill.

    Args:
        document_id: The document to process.
        client: Reuse an embedding client (one is created if omitted).
        embed: If ``False``, persist chunks without embeddings (and skip clustering).
        cluster: If ``False``, persist+embed but skip topic assignment.

    Returns:
        A :class:`ProcessingResult` summarising what was written.
    """
    model_name = settings.openai.embedding_model
    document = get_document(document_id)
    if document is None or not document.content:
        logger.warning("chunk_embed_cluster_no_content", document_id=str(document_id))
        replace_document_section_chunks(document_id, [], [])
        return ProcessingResult(chunk_count=0, embedded=False, model=model_name)

    sections = chunk_document_sections(document.content, document.document_type)
    if not sections:
        replace_document_section_chunks(document_id, [], [])
        return ProcessingResult(chunk_count=0, embedded=False, model=model_name)

    embeddings, embedded = _embed_or_none([s.text for s in sections], client, embed)
    chunks = replace_document_section_chunks(
        document_id, sections, embeddings, embedding_model=model_name if embedded else None
    )

    if cluster and embedded and document.company_id and document.document_type is not None:
        # Incremental clustering: only this document's freshly-written chunks lack
        # a topic_id (others were carried forward), so processing the whole scope
        # in oldest-first order just assigns the new ones against existing topics.
        try:
            scope_chunks = get_chunks_for_company_doctype(
                document.company_id, document.document_type
            )
            assign_unclustered_chunks(
                document.company_id, document.document_type, scope_chunks
            )
        except Exception as e:
            logger.error(
                "topic_clustering_failed_chunks_kept",
                document_id=str(document_id), error=str(e), exc_info=True,
            )

    logger.info(
        "chunk_embed_cluster_done",
        document_id=str(document_id), chunks=len(chunks), embedded=embedded,
    )
    return ProcessingResult(chunk_count=len(chunks), embedded=embedded, model=model_name)
