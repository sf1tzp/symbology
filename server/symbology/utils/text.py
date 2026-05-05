import html
import re
from typing import Tuple

# Smart quotes, dashes, ellipsis → ASCII equivalents
_UNICODE_REPLACEMENTS = {
    "\u2018": "'",   # left single quote
    "\u2019": "'",   # right single quote
    "\u201c": '"',   # left double quote
    "\u201d": '"',   # right double quote
    "\u2013": "-",   # en-dash
    "\u2014": "-",   # em-dash
    "\u2026": "...", # ellipsis
    "\u00a0": " ",   # non-breaking space
}

_UNICODE_PATTERN = re.compile(
    "[" + re.escape("".join(_UNICODE_REPLACEMENTS.keys())) + "]"
)


def normalize_filing_text(text: str) -> str:
    """Normalize raw SEC filing text for storage.

    - Decodes HTML entities
    - Normalizes Unicode (smart quotes, dashes, ellipsis)
    - Collapses excessive blank lines (3+ newlines → 2)
    - Collapses inline whitespace (multiple spaces/tabs → single space)
    - Strips trailing whitespace per line
    - Strips leading/trailing whitespace from the full text
    """
    if not text:
        return text

    # Decode HTML entities (handles &amp;, &nbsp;, &#8220;, etc.)
    text = html.unescape(text)

    # Normalize Unicode characters
    text = _UNICODE_PATTERN.sub(lambda m: _UNICODE_REPLACEMENTS[m.group()], text)

    # Process line by line: collapse inline whitespace and strip trailing
    lines = text.split("\n")
    lines = [re.sub(r"[ \t]+", " ", line).rstrip() for line in lines]
    text = "\n".join(lines)

    # Collapse runs of 3+ newlines to 2 (preserving paragraph breaks)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# Pattern matching page references like "Page 3", "Pages 37-51", "Page(s) 12"
_PAGE_REF_PATTERN = re.compile(
    r"\bPages?\s*\(?\s*\d+(?:\s*[-,]\s*\d+)*\s*\)?",
    re.IGNORECASE,
)

# Minimum character count for a section to be considered substantive prose
_MIN_SECTION_LENGTH = 1500

# Maximum page-reference density (matches per 1000 chars) before flagging as TOC
_MAX_PAGE_REF_DENSITY = 1.5


def validate_section_content(text: str) -> Tuple[bool, str]:
    """Check whether extracted section content is substantive prose.

    Returns (True, "") if the content looks valid, or (False, reason) if it
    appears to be a table of contents or other structural artifact.
    """
    if not text or not text.strip():
        return False, "empty"

    stripped = text.strip()
    length = len(stripped)

    # Check page-reference density
    page_refs = _PAGE_REF_PATTERN.findall(stripped)
    if page_refs:
        density = len(page_refs) / (length / 1000)
        if density >= _MAX_PAGE_REF_DENSITY:
            return False, f"page_ref_density={density:.1f} ({len(page_refs)} refs in {length} chars)"

    # Check minimum length (applied after page-ref check so a short but
    # genuine section like Legal Proceedings "None" doesn't need the density
    # test to reject it — it just gets the length gate)
    if length < _MIN_SECTION_LENGTH:
        return False, f"too_short ({length} chars)"

    return True, ""
