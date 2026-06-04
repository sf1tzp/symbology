"""Unit tests for edgar section accessors.

These pin the performance-critical behavior of ``SectionAccessor.extract`` and
``get_sections_for_document_types``:

  * extraction must go through the bounded ``__getitem__`` path, never
    ``get_item_with_part`` (whose missing-section fallback re-parses the whole
    document via ParsedHtml10K/Q — ~150s on a large filing), and
  * the data object (``filing.obj()``) must be built once per filing and shared
    across every section lookup, not rebuilt per-section.
"""
from unittest import mock

from symbology.ingestion.edgar_db.accessors import (
    SectionAccessor,
    get_sections_for_document_types,
)


def _filing(form):
    f = mock.MagicMock()
    f.form = form
    return f


def test_extract_uses_getitem_not_get_item_with_part():
    """10-K extraction uses __getitem__ with a bare key and never get_item_with_part."""
    filing = _filing("10-K")
    filing_obj = mock.MagicMock()
    filing_obj.__getitem__.return_value = "Item 1 text"

    acc = SectionAccessor(item_key="Item 1", part="PART I")
    result = acc.extract(filing, filing_obj=filing_obj)

    assert result == "Item 1 text"
    filing_obj.__getitem__.assert_called_once_with("Item 1")
    filing_obj.get_item_with_part.assert_not_called()


def test_extract_reuses_passed_obj():
    """A pre-built obj is reused; extract() must not rebuild it via filing.obj()."""
    filing = _filing("10-K")
    filing_obj = mock.MagicMock()
    filing_obj.__getitem__.return_value = "text"

    SectionAccessor(item_key="Item 7", part="PART II").extract(filing, filing_obj=filing_obj)

    filing.obj.assert_not_called()


def test_extract_part_qualified_key_for_10q():
    """10-Q lookups are part-qualified so Item 1 in Part II != Part I."""
    filing = _filing("10-Q")
    filing_obj = mock.MagicMock()
    filing_obj.__getitem__.return_value = "Legal Proceedings text"

    SectionAccessor(item_key="Item 1", part="PART II").extract(filing, filing_obj=filing_obj)

    filing_obj.__getitem__.assert_called_once_with("PART II, Item 1")


def test_extract_property_short_circuits():
    """When the direct property yields content, no item lookup is attempted."""
    filing = _filing("10-K")
    filing_obj = mock.MagicMock()
    filing_obj.business = "Business text"

    acc = SectionAccessor(property_name="business", item_key="Item 1", part="PART I")
    result = acc.extract(filing, filing_obj=filing_obj)

    assert result == "Business text"
    filing_obj.__getitem__.assert_not_called()


def test_extract_returns_none_when_absent():
    """A missing section returns None (cheaply) rather than raising."""
    filing = _filing("10-K")
    filing_obj = mock.MagicMock()
    filing_obj.__getitem__.return_value = None

    acc = SectionAccessor(item_key="Item 11", part="PART III")
    assert acc.extract(filing, filing_obj=filing_obj) is None


def test_get_sections_builds_obj_once():
    """filing.obj() is built exactly once for the whole filing, not per-section."""
    filing = _filing("10-K")
    filing_obj = mock.MagicMock()
    filing_obj.__getitem__.return_value = None
    for prop in (
        "business",
        "risk_factors",
        "management_discussion",
        "directors_officers_and_governance",
    ):
        setattr(filing_obj, prop, None)
    filing.obj.return_value = filing_obj

    get_sections_for_document_types(filing)

    filing.obj.assert_called_once()
