"""Deterministic, section-aware document chunking.

Unlike :mod:`symbology.llm.chunking` (a generic character-window splitter with
overlap, used for generated-content RAG), this module splits an SEC filing
*section* into **addressable, non-overlapping** chunks that line up with the
units humans cite — one risk-factor item, one MD&A subsection, one
business-description heading block.

Design contract (these properties are what downstream topic-clustering and
diffing rely on, so they are tested, not incidental):

* **Pure & deterministic** — output depends only on ``(content, document_type)``.
  The same input yields a byte-identical chunk list every run. No overlap, no
  randomness, no config/time dependence.
* **Partitioning** — chunks are ordered and never overlap; each chunk's text is
  the verbatim ``content[char_start:char_end]`` slice (stripped), so offsets and
  text stay consistent and the parent ``Document.content`` remains canonical.
* **Graceful degradation** — sections whose heading structure can't be detected
  fall back to paragraph-merged chunks flagged ``is_semantic=False`` (excluded
  from topic clustering). Every section still chunks; quality degrades, it never
  fails.

The structure signal is the **blank-line block layout** that edgartools'
text extraction + :func:`symbology.utils.text.normalize_filing_text` preserve:
headings sit on their own short lines, bodies are paragraph blocks beneath them.

Usage:
    from symbology.llm.section_chunker import chunk_document_sections
    chunks = chunk_document_sections(document.content, document.document_type)
"""
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from symbology.database.documents import DocumentType
from symbology.utils.logging import get_logger

logger = get_logger(__name__)

# --- Tunables (named so the behavior is auditable and stable across versions) ---
# A heading line is short and has few words; bodies are longer paragraph blocks.
HEADING_MAX_CHARS = 160
HEADING_MAX_WORDS = 25
# Sections shorter than this merge forward (kills tiny fragments / bare category
# headers like "Risks Related to Our Business").
MIN_SECTION_CHARS = 150
# A single semantic section longer than this is sub-split at paragraph
# boundaries so one runaway block doesn't become an un-embeddable mega-chunk.
SECTION_MAX_CHARS = 6000
# Paragraph-fallback window (non-semantic chunks).
FALLBACK_MIN_CHARS = 600
FALLBACK_MAX_CHARS = 3000

# Document types we attempt to split by heading. Everything else is prose we
# don't reliably segment, so it goes straight to the paragraph fallback.
_SEMANTIC_DOC_TYPES = {
    DocumentType.RISK_FACTORS,
    DocumentType.MDA,
    DocumentType.DESCRIPTION,
}

# Display locator prefix per document type (the human-citable "§1A.7" style).
# Stable identity is the topic, not this; the prefix is for readability.
_SECTION_PREFIX = {
    DocumentType.RISK_FACTORS: "§1A",
    DocumentType.MDA: "§7",
    DocumentType.DESCRIPTION: "§1",
    DocumentType.MARKET_RISK: "§7A",
    DocumentType.CONTROLS_PROCEDURES: "§9A",
    DocumentType.LEGAL_PROCEEDINGS: "§3",
    DocumentType.EXECUTIVE_COMPENSATION: "§11",
    DocumentType.DIRECTORS_OFFICERS: "§10",
}

_BLANK_LINE = re.compile(r"\n[ \t]*\n")


@dataclass(frozen=True)
class SectionChunk:
    """One addressable, non-overlapping slice of a Document's content."""
    chunk_index: int
    section_path: str
    heading: Optional[str]
    text: str
    char_start: int
    char_end: int
    is_semantic: bool


def _prefix_for(document_type: Optional[DocumentType]) -> str:
    if document_type is None:
        return "§"
    return _SECTION_PREFIX.get(document_type, "§" + document_type.value)


def _iter_blocks(content: str) -> List[Tuple[int, int, str]]:
    """Split content into blank-line-delimited blocks, keeping their char spans.

    Returns ``(start, end, text)`` tuples for every non-empty block, where
    ``start``/``end`` index into ``content`` and ``text`` is the raw slice.
    """
    blocks: List[Tuple[int, int, str]] = []
    pos = 0
    for m in _BLANK_LINE.finditer(content):
        raw = content[pos:m.start()]
        if raw.strip():
            blocks.append((pos, m.start(), raw))
        pos = m.end()
    tail = content[pos:]
    if tail.strip():
        blocks.append((pos, len(content), tail))
    return blocks


def _is_heading_block(text: str) -> bool:
    """Heuristic: is this block a heading line rather than body prose?

    Deterministic and intentionally simple — a heading is a single short line
    with few words that doesn't trail off mid-clause. Risk-factor headings are
    often full sentences ending in a period, so terminal periods are allowed;
    only mid-clause punctuation (',', ';') disqualifies.
    """
    s = text.strip()
    if "\n" in s:  # multi-line ⇒ paragraph, not a heading
        return False
    n = len(s)
    if n < 3 or n > HEADING_MAX_CHARS:
        return False
    if len(s.split()) > HEADING_MAX_WORDS:
        return False
    if s[-1] in ",;":
        return False
    return True


def _greedy_merge(
    blocks: List[Tuple[int, int, str]], min_chars: int, max_chars: int
) -> List[Tuple[int, int]]:
    """Merge consecutive blocks into ``(start, end)`` groups within a size window.

    Greedy left-to-right: keep appending blocks to the current group until it
    reaches ``min_chars``; never start a new group that would leave the current
    one below ``min_chars`` unless adding the next block would exceed
    ``max_chars``. Deterministic; no overlap.
    """
    if not blocks:
        return []
    groups: List[Tuple[int, int]] = []
    cur_start = blocks[0][0]
    cur_end = blocks[0][1]
    cur_len = len(blocks[0][2].strip())
    for start, end, text in blocks[1:]:
        block_len = len(text.strip())
        # Close the current group once it's big enough, unless it's still under
        # min and merging wouldn't blow the max.
        if cur_len >= min_chars and cur_len + block_len > max_chars:
            groups.append((cur_start, cur_end))
            cur_start, cur_end, cur_len = start, end, block_len
        else:
            cur_end = end
            cur_len += block_len
    groups.append((cur_start, cur_end))
    return groups


def _fallback_chunks(
    content: str, blocks: List[Tuple[int, int, str]], prefix: str
) -> List[SectionChunk]:
    """Paragraph-merged, non-semantic chunks for prose we can't segment."""
    chunks: List[SectionChunk] = []
    for i, (start, end) in enumerate(_greedy_merge(blocks, FALLBACK_MIN_CHARS, FALLBACK_MAX_CHARS)):
        sliced = content[start:end].strip()
        if not sliced:
            continue
        chunks.append(
            SectionChunk(
                chunk_index=len(chunks),
                section_path=f"{prefix}.#{i + 1}",
                heading=None,
                text=sliced,
                char_start=start,
                char_end=end,
                is_semantic=False,
            )
        )
    return chunks


def _emit_section(
    content: str,
    chunks: List[SectionChunk],
    prefix: str,
    ordinal: int,
    heading: Optional[str],
    start: int,
    end: int,
) -> None:
    """Append a section as one or more chunks (sub-splitting if over-long)."""
    sliced = content[start:end].strip()
    if not sliced:
        return
    section_path = f"{prefix}.{ordinal}"

    if len(sliced) <= SECTION_MAX_CHARS:
        chunks.append(
            SectionChunk(
                chunk_index=len(chunks),
                section_path=section_path,
                heading=heading,
                text=sliced,
                char_start=start,
                char_end=end,
                is_semantic=True,
            )
        )
        return

    # Over-long section: sub-split at paragraph boundaries, sharing the locator.
    sub_blocks = _iter_blocks(content[start:end])
    for start_rel, end_rel in _greedy_merge(sub_blocks, FALLBACK_MIN_CHARS, SECTION_MAX_CHARS):
        abs_start, abs_end = start + start_rel, start + end_rel
        sub = content[abs_start:abs_end].strip()
        if not sub:
            continue
        chunks.append(
            SectionChunk(
                chunk_index=len(chunks),
                section_path=section_path,
                heading=heading,
                text=sub,
                char_start=abs_start,
                char_end=abs_end,
                is_semantic=True,
            )
        )


def chunk_document_sections(
    content: Optional[str],
    document_type: Optional[DocumentType],
) -> List[SectionChunk]:
    """Split a document's section text into addressable, non-overlapping chunks.

    Args:
        content: The (already normalized) section text. Empty/whitespace ⇒ ``[]``.
        document_type: Drives the locator prefix and whether heading-based
            splitting is attempted (prose types fall back to paragraph merge).

    Returns:
        Ordered ``SectionChunk`` list partitioning the content.
    """
    if not content or not content.strip():
        return []

    prefix = _prefix_for(document_type)
    blocks = _iter_blocks(content)
    if not blocks:
        return []

    # Prose types we don't segment by heading → paragraph fallback.
    if document_type not in _SEMANTIC_DOC_TYPES:
        return _fallback_chunks(content, blocks, prefix)

    # Locate heading blocks; the indices between them delimit sections.
    heading_idxs = [i for i, b in enumerate(blocks) if _is_heading_block(b[2])]
    if not heading_idxs:
        # No detectable structure — degrade to paragraph chunks.
        return _fallback_chunks(content, blocks, prefix)

    # Build raw section boundaries: a preamble (content before the first heading)
    # plus one section starting at each heading block.
    # boundaries: list of (heading_text_or_None, first_block_idx)
    boundaries: List[Tuple[Optional[str], int]] = []
    if heading_idxs[0] != 0:
        boundaries.append((None, 0))  # leading preamble with no heading
    for i in heading_idxs:
        boundaries.append((blocks[i][2].strip(), i))

    # Convert to char spans: section k runs from its first block's start to the
    # next section's first block start (or end of content).
    raw_sections: List[Tuple[Optional[str], int, int]] = []
    for k, (heading, blk_idx) in enumerate(boundaries):
        start = blocks[blk_idx][0]
        if k + 1 < len(boundaries):
            end = blocks[boundaries[k + 1][1]][0]
        else:
            end = len(content)
        raw_sections.append((heading, start, end))

    # Fold tiny sections *forward* into the next one so every emitted section
    # carries real body text. A bare category header ("Risks Related to Our
    # Business") thus becomes a prefix line of the first real risk beneath it,
    # and that risk keeps its own heading. Deterministic left-to-right.
    merged: List[Tuple[Optional[str], int, int]] = []
    carry_start: Optional[int] = None
    for k, (heading, start, end) in enumerate(raw_sections):
        seg_start = carry_start if carry_start is not None else start
        too_small = len(content[seg_start:end].strip()) < MIN_SECTION_CHARS
        if too_small and k + 1 < len(raw_sections):
            carry_start = seg_start  # defer; adopt the next section's heading
            continue
        merged.append((heading, seg_start, end))
        carry_start = None

    chunks: List[SectionChunk] = []
    for ordinal, (heading, start, end) in enumerate(merged):
        _emit_section(content, chunks, prefix, ordinal, heading, start, end)

    logger.debug(
        "chunked_document_sections",
        document_type=document_type.value if document_type else None,
        input_chars=len(content),
        sections=len(merged),
        chunks=len(chunks),
    )
    return chunks
