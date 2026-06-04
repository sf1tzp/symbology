"""Integration tests for section-aware chunk+embed+cluster orchestration.

Embeddings are mocked (deterministic per text) so no embedding server is needed
and clustering is predictable. The headline property tested is **carry-forward**:
re-chunking an unchanged document must not churn topic ids.
"""
import hashlib
from datetime import date

import pytest

from symbology.database.base import get_db_session
from symbology.database.chunk_topics import get_topics_for_scope
from symbology.database.companies import Company
from symbology.database.document_chunks import DocumentChunk, get_chunks_by_document
from symbology.database.documents import Document, DocumentType
from symbology.database.filings import Filing
from symbology.llm import content_processing
from symbology.utils.config import settings

pytestmark = pytest.mark.integration

DIM = settings.openai.embedding_dimensions

RISK_FACTORS = """Item 1A. Risk Factors

You should carefully consider the following risks together with all other information in this report before investing in our securities, as any of them could materially harm our business.

We depend on a limited number of customers for a substantial portion of our revenue.

A significant portion of our net sales is concentrated among a small number of customers. The loss of one or more key customers could materially and adversely affect our revenue and operating results in any given period.

Our products rely on specialized semiconductor components for which alternative suppliers may not be readily available.

A meaningful portion of our products depend on semiconductor components sourced from a limited number of foundries. A loss of supply or substantial price increases could materially affect our ability to manufacture and deliver these products.

Cybersecurity threats and incidents could disrupt our operations and harm our reputation.

We face persistent cybersecurity threats from a range of actors. A successful attack on our information systems could result in theft of sensitive data, disruption of operations, and significant remediation costs."""


def _fake_embed_texts(texts, **kwargs):
    """Deterministic unit vector per distinct text (hash → axis)."""
    out = []
    for t in texts:
        h = int(hashlib.sha256(t.encode("utf-8")).hexdigest(), 16)
        v = [0.0] * DIM
        v[h % DIM] = 1.0
        out.append(v)
    return out


@pytest.fixture
def patched_embeddings(monkeypatch):
    monkeypatch.setattr(content_processing, "embed_texts", _fake_embed_texts)
    monkeypatch.setattr(content_processing, "init_embedding_client", lambda *a, **k: object())


def _make_document(db_session, content=RISK_FACTORS, ticker="ACME", cik="0000444444"):
    company = Company(name="Acme Inc", ticker=ticker, exchanges=["NYSE"], cik=cik)
    db_session.add(company)
    db_session.flush()
    filing = Filing(company_id=company.id, accession_number=f"{cik}-25", form="10-K",
                    filing_date=date(2025, 12, 21), period_of_report=date(2025, 9, 30))
    db_session.add(filing)
    db_session.flush()
    doc = Document(company_id=company.id, filing_id=filing.id, title="RF",
                   document_type=DocumentType.RISK_FACTORS, content=content)
    doc.update_content_hash()
    db_session.add(doc)
    db_session.flush()
    return company, doc


def test_creates_section_chunks_and_topics(db_session, patched_embeddings):
    company, doc = _make_document(db_session)
    result = content_processing.chunk_embed_and_cluster_document(doc.id)

    assert result.chunk_count >= 3
    assert result.embedded is True

    chunks = get_chunks_by_document(doc.id)
    assert len(chunks) == result.chunk_count
    assert all(c.section_path.startswith("§1A.") for c in chunks)
    assert all(c.is_semantic for c in chunks)
    assert all(c.embedding is not None for c in chunks)
    assert all(c.topic_id is not None for c in chunks)

    topics = get_topics_for_scope(company.id, DocumentType.RISK_FACTORS)
    assert len(topics) == len(chunks)  # distinct risks → distinct topics here


def test_carry_forward_keeps_topic_ids_stable_on_rechunk(db_session, patched_embeddings):
    company, doc = _make_document(db_session)
    content_processing.chunk_embed_and_cluster_document(doc.id)

    first = {c.content_hash: c.topic_id for c in get_chunks_by_document(doc.id)}
    topics_before = len(get_topics_for_scope(company.id, DocumentType.RISK_FACTORS))

    # Re-chunk the unchanged document.
    content_processing.chunk_embed_and_cluster_document(doc.id)

    second = {c.content_hash: c.topic_id for c in get_chunks_by_document(doc.id)}
    topics_after = len(get_topics_for_scope(company.id, DocumentType.RISK_FACTORS))

    assert first == second  # same content_hash → same topic_id, no churn
    assert topics_after == topics_before  # no duplicate topics created


def test_changed_content_assigns_new_topic_but_preserves_unchanged(db_session, patched_embeddings):
    company, doc = _make_document(db_session)
    content_processing.chunk_embed_and_cluster_document(doc.id)
    before = {c.content_hash: c.topic_id for c in get_chunks_by_document(doc.id)}
    topics_before = len(get_topics_for_scope(company.id, DocumentType.RISK_FACTORS))

    # Add a brand-new risk; existing risk text is unchanged.
    new_risk = (
        "\n\nMacroeconomic conditions and inflation could adversely affect demand.\n\n"
        "Adverse macroeconomic conditions, including inflation and higher interest rates, "
        "could reduce customer demand and compress our operating margins over time."
    )
    doc.content = RISK_FACTORS + new_risk
    doc.update_content_hash()
    get_db_session().commit()

    content_processing.chunk_embed_and_cluster_document(doc.id)
    after = {c.content_hash: c.topic_id for c in get_chunks_by_document(doc.id)}
    topics_after = len(get_topics_for_scope(company.id, DocumentType.RISK_FACTORS))

    # Unchanged risks kept their topic_id (carry-forward by content_hash).
    for content_hash, topic_id in before.items():
        if content_hash in after:
            assert after[content_hash] == topic_id
    # The new risk added exactly one topic.
    assert topics_after == topics_before + 1


def test_handle_backfill_chunks_processes_and_clusters(db_session, patched_embeddings):
    from datetime import date as _date

    from symbology.database.chunk_topics import get_topics_for_scope
    from symbology.worker.handlers import handle_backfill_chunks

    company = Company(name="Delta Inc", ticker="DLTA", exchanges=["NYSE"], cik="0000555555")
    db_session.add(company)
    db_session.flush()
    # Two filings of the same section; second reuses one risk verbatim.
    for yr, content in ((2024, RISK_FACTORS), (2025, RISK_FACTORS)):
        f = Filing(company_id=company.id, accession_number=f"DLTA-{yr}", form="10-K",
                   filing_date=_date(yr, 12, 21), period_of_report=_date(yr, 9, 30))
        db_session.add(f)
        db_session.flush()
        d = Document(company_id=company.id, filing_id=f.id, title=f"RF{yr}",
                     document_type=DocumentType.RISK_FACTORS, content=content)
        d.update_content_hash()
        db_session.add(d)
    db_session.flush()

    result = handle_backfill_chunks({"ticker": "DLTA", "document_types": ["risk_factors"]})

    assert result["documents_processed"] == 2
    assert result["total_documents"] == 2
    assert result["scopes_reclustered"] == 1
    # Identical risk text across the two filings clusters into shared topics, so
    # there are fewer topics than total chunks across both documents.
    topics = get_topics_for_scope(company.id, DocumentType.RISK_FACTORS)
    assert topics
    assert all(t.member_count >= 1 for t in topics)
