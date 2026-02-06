import html
import re

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
