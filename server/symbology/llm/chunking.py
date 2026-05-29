"""Text chunking utilities for embedding long documents.

Splits long text into overlapping, embeddable chunks. Chunking is
character-based (a reliable proxy for token count that needs no tokenizer
dependency) and tries to break on natural boundaries — paragraphs, then
sentences, then whitespace — so chunks stay semantically coherent.

Usage:
    from symbology.llm.chunking import chunk_text

    chunks = chunk_text(document.content)  # -> list[str]
"""
import re
from dataclasses import dataclass
from typing import List, Optional

from symbology.utils.config import settings
from symbology.utils.logging import get_logger

logger = get_logger(__name__)

# Preferred break points, from coarsest to finest. The chunker prefers to end a
# chunk at the latest boundary that falls within the target window.
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class Chunk:
    """A single ordered piece of a larger text."""
    index: int
    content: str


def _find_break(text: str, target: int, hard_max: int) -> int:
    """Find a good split offset at or before ``hard_max``, near ``target``.

    Prefers a paragraph break, then a sentence break, then a whitespace break,
    falling back to a hard cut at ``hard_max`` if no boundary is found.
    """
    window = text[:hard_max]

    # Prefer the last paragraph break at/after the target offset.
    candidates = [m.end() for m in _PARAGRAPH_BREAK.finditer(window) if m.end() >= target]
    if candidates:
        return candidates[0]

    # Then the last sentence break in the window.
    sentence_ends = [m.end() for m in _SENTENCE_BREAK.finditer(window) if m.end() >= target]
    if sentence_ends:
        return sentence_ends[0]

    # Then any whitespace at/after the target.
    ws = [m.start() for m in re.finditer(r"\s", window) if m.start() >= target]
    if ws:
        return ws[0]

    # No boundary found — hard cut.
    return hard_max


def chunk_text(
    text: Optional[str],
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> List[str]:
    """Split text into overlapping chunks suitable for embedding.

    Args:
        text: The text to split. ``None``/empty/whitespace returns ``[]``.
        chunk_size: Target chunk size in characters (defaults to config).
        chunk_overlap: Overlap between consecutive chunks (defaults to config).

    Returns:
        Ordered list of non-empty chunk strings.
    """
    if not text or not text.strip():
        return []

    cfg = settings.openai
    chunk_size = chunk_size or cfg.chunk_size
    chunk_overlap = cfg.chunk_overlap if chunk_overlap is None else chunk_overlap

    if chunk_overlap >= chunk_size:
        raise ValueError(f"chunk_overlap ({chunk_overlap}) must be smaller than chunk_size ({chunk_size})")

    text = text.strip()
    if len(text) <= chunk_size:
        return [text]

    # Aim to start looking for a boundary ~75% through the window so chunks
    # don't end up tiny, but still have room to extend to a clean break.
    target = max(1, int(chunk_size * 0.75))

    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        remaining = text[start:]
        if len(remaining) <= chunk_size:
            chunk = remaining.strip()
            if chunk:
                chunks.append(chunk)
            break

        split_at = _find_break(remaining, target=target, hard_max=chunk_size)
        chunk = remaining[:split_at].strip()
        if chunk:
            chunks.append(chunk)

        # Advance, retaining ``chunk_overlap`` characters of context. Guard
        # against pathological cases where no forward progress is made.
        advance = max(1, split_at - chunk_overlap)
        start += advance

    logger.debug("chunked_text", input_chars=n, chunks=len(chunks), chunk_size=chunk_size, overlap=chunk_overlap)
    return chunks


def chunk_text_with_index(
    text: Optional[str],
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> List[Chunk]:
    """Like :func:`chunk_text` but returns ordered ``Chunk`` objects with indexes."""
    return [Chunk(index=i, content=c) for i, c in enumerate(chunk_text(text, chunk_size, chunk_overlap))]
