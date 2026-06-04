"""Word-level text diffing for year-over-year section comparison.

Produces an ordered list of ``{op, text}`` segments (op ∈ equal|insert|delete)
that the UI renders as ``.ins``/``.del`` highlights. The ops are **lossless**:
joining the equal+delete texts reconstructs the prior version exactly, and
equal+insert reconstructs the current version — so one op list drives both
side-by-side columns and no JS diff library is needed on the frontend.

Uses the stdlib :class:`difflib.SequenceMatcher` over *word* tokens (each token
keeps its trailing whitespace), which yields readable phrase-level highlights
without the sub-word noise of a character diff — adequate for SEC prose, with no
extra dependency. ``diff-match-patch`` (with semantic cleanup) is a possible
future upgrade if finer alignment is wanted.
"""
import re
from difflib import SequenceMatcher
from typing import Dict, List, Tuple

# Classification thresholds (named so behavior is auditable; tune as needed).
UNCHANGED_RATIO = 0.05   # edit fraction below which a change is cosmetic
ESCALATE_RATIO = 0.15    # relative length growth/shrink that counts as (de)emphasis
FALSE_MERGE_RATIO = 0.85  # matched pair this different is likely two unrelated topics

# Change-kind string values (mirror database.section_diffs.ChangeKind to avoid a
# utils -> database import).
NEW = "new"
REMOVED = "removed"
ESCALATED = "escalated"
DE_EMPHASISED = "de_emphasised"
REWORDED = "reworded"
UNCHANGED = "unchanged"

# A word run plus its trailing whitespace. Inputs are stripped section text, so
# "".join(tokens) reconstructs the input exactly.
_TOKEN_RE = re.compile(r"\S+\s*")


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text)


def compute_token_diff(
    prev_text: str, curr_text: str
) -> Tuple[List[Dict[str, str]], int, int]:
    """Diff two texts at word granularity.

    Returns ``(ops, tokens_added, tokens_removed)`` where ``ops`` is an ordered
    list of ``{"op": "equal"|"insert"|"delete", "text": str}``. Lossless:
    equal+delete reconstructs ``prev_text``; equal+insert reconstructs ``curr_text``.
    """
    a = _tokenize(prev_text or "")
    b = _tokenize(curr_text or "")
    matcher = SequenceMatcher(a=a, b=b, autojunk=False)

    ops: List[Dict[str, str]] = []
    added = removed = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            ops.append({"op": "equal", "text": "".join(a[i1:i2])})
        elif tag == "delete":
            ops.append({"op": "delete", "text": "".join(a[i1:i2])})
            removed += i2 - i1
        elif tag == "insert":
            ops.append({"op": "insert", "text": "".join(b[j1:j2])})
            added += j2 - j1
        elif tag == "replace":
            ops.append({"op": "delete", "text": "".join(a[i1:i2])})
            ops.append({"op": "insert", "text": "".join(b[j1:j2])})
            removed += i2 - i1
            added += j2 - j1
    return ops, added, removed


def edit_ratio(prev_text: str, curr_text: str, ops: List[Dict[str, str]]) -> float:
    """Fraction of the longer text touched by inserts/deletes (0..1)."""
    edit_chars = sum(len(o["text"]) for o in ops if o["op"] != "equal")
    return edit_chars / max(len(prev_text), len(curr_text), 1)


def classify_change(prev_text: str, curr_text: str, ops: List[Dict[str, str]]) -> str:
    """Classify a matched-pair change (interpretable, length-based, no sentiment).

    UNCHANGED below the edit threshold; otherwise ESCALATED / DE_EMPHASISED when
    the text grew/shrank materially, else REWORDED.
    """
    ratio = edit_ratio(prev_text, curr_text, ops)
    if ratio < UNCHANGED_RATIO:
        return UNCHANGED
    rel_len = (len(curr_text) - len(prev_text)) / max(len(prev_text), 1)
    if rel_len >= ESCALATE_RATIO:
        return ESCALATED
    if rel_len <= -ESCALATE_RATIO:
        return DE_EMPHASISED
    return REWORDED
