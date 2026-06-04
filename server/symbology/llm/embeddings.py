"""OpenAI-compatible embedding client.

Talks to any OpenAI-compatible ``/v1/embeddings`` endpoint (configured via the
``OPENAI_*`` environment variables) to turn text into dense vectors. The default
target is the Jina embedding server which returns 1024-dimensional embeddings.

Usage:
    from symbology.llm.embeddings import embed_texts, embed_query

    vectors = embed_texts(["first chunk", "second chunk"])  # -> list[list[float]]
    query_vector = embed_query("how risky is this company?")  # -> list[float]
"""
import time
from typing import List, Optional

from openai import OpenAI

from symbology.llm.client import retry_backoff
from symbology.utils.config import settings
from symbology.utils.logging import get_logger

logger = get_logger(__name__)


class EmbeddingDimensionMismatch(ValueError):
    """Raised when the endpoint returns vectors of an unexpected dimensionality."""


def init_embedding_client(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: Optional[float] = None,
) -> OpenAI:
    """Create an OpenAI client pointed at the configured embedding endpoint.

    Args:
        base_url: Override the OpenAI-compatible base URL (defaults to config).
        api_key: Override the bearer token (defaults to config).
        timeout: Per-request timeout in seconds (defaults to config).

    Returns:
        A configured ``openai.OpenAI`` client instance.
    """
    cfg = settings.openai
    client = OpenAI(
        base_url=base_url or cfg.base_url,
        api_key=api_key or cfg.api_key,
        timeout=timeout if timeout is not None else cfg.request_timeout,
    )
    logger.debug("initialized_embedding_client", base_url=base_url or cfg.base_url)
    return client


def _embed_batch(client: OpenAI, texts: List[str], model: str, expected_dim: int) -> List[List[float]]:
    """Embed a single batch of texts, validating dimensionality."""
    response = retry_backoff(
        settings.openai.retry_timeout,
        client.embeddings.create,
        model=model,
        input=texts,
    )

    # The API guarantees output order matches input order, but sort defensively.
    data = sorted(response.data, key=lambda d: d.index)
    vectors = [d.embedding for d in data]

    for vector in vectors:
        if len(vector) != expected_dim:
            raise EmbeddingDimensionMismatch(
                f"expected {expected_dim}-dim embeddings, got {len(vector)} from model '{model}'"
            )

    return vectors


def embed_texts(
    texts: List[str],
    model: Optional[str] = None,
    client: Optional[OpenAI] = None,
    batch_size: Optional[int] = None,
) -> List[List[float]]:
    """Embed a list of texts, batching requests to respect endpoint limits.

    Args:
        texts: Texts to embed. Empty list returns an empty list.
        model: Override the embedding model name (defaults to config).
        client: Reuse an existing client (one is created if omitted).
        batch_size: Override the per-request batch size (defaults to config).

    Returns:
        A list of embedding vectors, one per input text, in the same order.
    """
    if not texts:
        return []

    cfg = settings.openai
    model = model or cfg.embedding_model
    batch_size = batch_size or cfg.embedding_batch_size
    expected_dim = cfg.embedding_dimensions

    if client is None:
        client = init_embedding_client()

    # Some models (e.g. nomic-embed-text) require a task-instruction prefix on
    # each input for well-calibrated vectors. Applied uniformly so chunk-vs-chunk
    # comparisons stay in one space; empty prefix is a no-op for other models.
    prefix = cfg.embedding_task_prefix
    if prefix:
        texts = [prefix + t for t in texts]

    logger.info("embedding_texts", count=len(texts), model=model, batch_size=batch_size)
    start_ns = time.time_ns()

    vectors: List[List[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        vectors.extend(_embed_batch(client, batch, model, expected_dim))

    duration = (time.time_ns() - start_ns) / 1e9
    logger.info(
        "embedded_texts",
        count=len(vectors),
        model=model,
        dimensions=expected_dim,
        duration=f"{duration:.2f}s",
    )
    return vectors


def embed_query(
    text: str,
    model: Optional[str] = None,
    client: Optional[OpenAI] = None,
) -> List[float]:
    """Embed a single text (e.g. a search query) and return its vector.

    Args:
        text: The text to embed.
        model: Override the embedding model name (defaults to config).
        client: Reuse an existing client (one is created if omitted).

    Returns:
        A single embedding vector.
    """
    return embed_texts([text], model=model, client=client)[0]
