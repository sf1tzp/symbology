"""Integration test for the filing-level page-content pipeline (Chunk A).

Runs filing_page_content_pipeline end-to-end against the DB with the LLM call
mocked: asserts the document/filing GeneratedContent stages + depths and the
published DocumentPageContent / FilingPageContent versions.
"""
import hashlib
import types
from datetime import date
from unittest.mock import patch

import pytest

from symbology.database.companies import Company
from symbology.database.documents import Document, DocumentType
from symbology.database.filings import Filing
from symbology.database.generated_content import ContentStage, GeneratedContent
from symbology.database.page_content import (
    DocumentPageContent,
    FilingPageContent,
    get_current_filing_page_content,
)
from symbology.llm.client import ShutdownRequested
from symbology.worker.page_pipelines import (
    FilingHasNoPageableDocuments,
    PageContentGenerationError,
    filing_page_content_pipeline,
)

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _mock_embeddings(monkeypatch):
    """The filing pipeline now section-chunks + embeds each document; stub the
    embedding endpoint so tests don't hit the network (mirrors the LLM mock)."""
    import symbology.llm.content_processing as cp
    from symbology.utils.config import settings

    dim = settings.openai.embedding_dimensions

    def _fake_embed_texts(texts, **kwargs):
        out = []
        for t in texts:
            v = [0.0] * dim
            v[int(hashlib.sha256(t.encode()).hexdigest(), 16) % dim] = 1.0
            out.append(v)
        return out

    monkeypatch.setattr(cp, "embed_texts", _fake_embed_texts)
    monkeypatch.setattr(cp, "init_embedding_client", lambda *a, **k: object())


def _fake_generate_response(model_config, system_prompt, user_prompt, *args, **kwargs):
    # Derive distinct output per (stage, source) so content-hash dedup doesn't
    # collapse different stages into one row (as it would with constant text).
    key = hashlib.sha256((system_prompt + "||" + user_prompt).encode()).hexdigest()[:16]
    text = f"GENERATED::{key}"
    adapter = types.SimpleNamespace(
        response=text, content=text, total_duration=1.0,
        input_tokens=10, output_tokens=5, done=True, done_reason="end_turn",
    )
    return adapter, None


@pytest.fixture
def filing_with_docs(db_session):
    company = Company(name="Test Co", ticker="TEST", exchanges=["NYSE"])
    db_session.add(company)
    db_session.flush()
    filing = Filing(
        company_id=company.id, accession_number="0001234567-26-000001",
        form="10-K", filing_date=date(2026, 3, 1), period_of_report=date(2025, 12, 31),
    )
    db_session.add(filing)
    db_session.flush()
    # Two of the 10-K document types present.
    for i, dt in enumerate([DocumentType.DESCRIPTION, DocumentType.RISK_FACTORS]):
        db_session.add(Document(
            company_id=company.id, filing_id=filing.id, title=f"doc{i}.html",
            document_type=dt, content=f"body {i}", content_hash=f"dochash{i}",
        ))
    db_session.flush()
    return filing


@pytest.fixture
def filing_without_docs(db_session):
    company = Company(name="No Docs Co", ticker="NODOC", exchanges=["NYSE"])
    db_session.add(company)
    db_session.flush()
    filing = Filing(
        company_id=company.id, accession_number="0001234567-26-000099",
        form="10-Q", filing_date=date(2026, 5, 5), period_of_report=date(2026, 3, 31),
    )
    db_session.add(filing)
    db_session.flush()
    return filing  # no Document rows — none of the form's pageable sections present


def test_no_pageable_documents_is_a_benign_skip(db_session, filing_without_docs):
    """A filing carrying none of its form's document types raises the benign
    FilingHasNoPageableDocuments (a skip, not a hard failure) and publishes nothing."""
    with pytest.raises(FilingHasNoPageableDocuments):
        filing_page_content_pipeline(filing_without_docs)

    assert get_current_filing_page_content(filing_without_docs.id) is None
    assert db_session.query(FilingPageContent).count() == 0
    assert db_session.query(DocumentPageContent).count() == 0


def test_filing_pipeline_generates_and_publishes(db_session, filing_with_docs):
    filing = filing_with_docs

    with patch("symbology.llm.client.get_generate_response", _fake_generate_response):
        page = filing_page_content_pipeline(filing)

    # FilingPageContent published with main + intro + 2 source documents.
    current = get_current_filing_page_content(filing.id)
    assert current is not None and current.id == page.id
    assert current.main_content is not None
    assert current.intro_content is not None
    assert len(current.source_documents) == 2

    # One DocumentPageContent per document, each with summary + intro.
    doc_pages = db_session.query(DocumentPageContent).all()
    assert len(doc_pages) == 2
    for dp in doc_pages:
        assert dp.summary_content_id is not None
        assert dp.intro_content_id is not None

    # Stage + depth checks across the generated content.
    def _by_stage(stage):
        return db_session.query(GeneratedContent).filter(
            GeneratedContent.content_stage == stage
        ).all()

    l1 = _by_stage(ContentStage.SINGLE_SUMMARY)
    assert len(l1) == 2 and all(g.generation_depth == 1 for g in l1)

    doc_intros = _by_stage(ContentStage.DOCUMENT_PAGE_INTRO)
    assert len(doc_intros) == 2
    assert all(g.generation_depth == 2 and g.document_id is not None for g in doc_intros)

    main = _by_stage(ContentStage.FILING_MAIN_CONTENT)
    assert len(main) == 1 and main[0].generation_depth == 2 and main[0].filing_id == filing.id

    intro = _by_stage(ContentStage.FILING_INTRO)
    assert len(intro) == 1 and intro[0].generation_depth == 3 and intro[0].filing_id == filing.id


def _raise(exc):
    def _fn(*args, **kwargs):
        raise exc
    return _fn


def test_generation_failure_publishes_nothing(db_session, filing_with_docs):
    """All-or-nothing: if generation fails, the pipeline raises and publishes nothing."""
    filing = filing_with_docs
    with patch("symbology.llm.client.get_generate_response",
               _raise(TypeError("auth not configured"))):
        with pytest.raises(PageContentGenerationError):
            filing_page_content_pipeline(filing)

    assert db_session.query(FilingPageContent).count() == 0
    assert db_session.query(DocumentPageContent).count() == 0


def test_shutdown_propagates_and_publishes_nothing(db_session, filing_with_docs):
    """A shutdown during generation propagates (not swallowed) and publishes nothing."""
    filing = filing_with_docs
    with patch("symbology.llm.client.get_generate_response",
               _raise(ShutdownRequested("shutdown"))):
        with pytest.raises(ShutdownRequested):
            filing_page_content_pipeline(filing)

    assert db_session.query(FilingPageContent).count() == 0
    assert db_session.query(DocumentPageContent).count() == 0
