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

from symbology.database.document_chunks import replace_document_chunks
from symbology.database.documents import get_document
from symbology.database.generated_content import get_generated_content
from symbology.database.generated_content_chunks import replace_content_chunks
from symbology.llm.chunking import chunk_text
from symbology.llm.embeddings import embed_texts, init_embedding_client
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
