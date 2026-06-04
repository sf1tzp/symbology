"""Pure (no-DB) unit tests for the document selection helper.

Lives at the top level (not under tests/database/) so it doesn't trigger that
package's autouse PostgreSQL fixture — this only exercises in-memory filtering.
"""
from types import SimpleNamespace

from symbology.database.documents import DocumentType, select_substantive_document


def _doc(doc_type, is_substantive):
    return SimpleNamespace(document_type=doc_type, is_substantive=is_substantive)


def test_picks_matching_substantive():
    docs = [
        _doc(DocumentType.RISK_FACTORS, True),
        _doc(DocumentType.MDA, True),
    ]
    assert select_substantive_document(docs, DocumentType.MDA) is docs[1]


def test_skips_non_substantive():
    docs = [_doc(DocumentType.LEGAL_PROCEEDINGS, False)]
    assert select_substantive_document(docs, DocumentType.LEGAL_PROCEEDINGS) is None


def test_absent_type_returns_none():
    docs = [_doc(DocumentType.MDA, True)]
    assert select_substantive_document(docs, DocumentType.RISK_FACTORS) is None


def test_prefers_substantive_of_same_type():
    non_sub = _doc(DocumentType.RISK_FACTORS, False)
    sub = _doc(DocumentType.RISK_FACTORS, True)
    # Non-substantive appears first; the substantive one must still be chosen.
    assert select_substantive_document([non_sub, sub], DocumentType.RISK_FACTORS) is sub


def test_empty():
    assert select_substantive_document([], DocumentType.MDA) is None
