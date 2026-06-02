"""Integration tests for the new page-content stage writer (chunk 3).

Exercises generate_page_content -> handle_content_generation against the DB:
content_stage tagging, subject/scope FK assignment (company / filing / document),
and write-time generation_depth. Note there is **no per-test get_db_session
patching** — the db_session fixture now wires the application's session centrally.
"""
import json
import types
from datetime import date
from unittest.mock import patch

import pytest

from symbology.database.companies import Company
from symbology.database.documents import Document, DocumentType
from symbology.database.filings import Filing
from symbology.database.generated_content import (
    ContentSourceType,
    ContentStage,
    GeneratedContent,
    get_generated_content_by_hash,
)
from symbology.database.model_configs import ModelConfig
from symbology.database.prompts import create_prompt
from symbology.worker.pipeline import generate_page_content

pytestmark = pytest.mark.integration


def _fake_generate_response(*args, **kwargs):
    """Stand in for the LLM call: return an adapter + no warning."""
    adapter = types.SimpleNamespace(
        response="GENERATED PAGE CONTENT",
        content="GENERATED PAGE CONTENT",
        total_duration=1.0,
        input_tokens=100,
        output_tokens=50,
        done=True,
        done_reason="end_turn",
    )
    return adapter, None


@pytest.fixture
def model_config(db_session) -> ModelConfig:
    mc = ModelConfig(
        model="claude-haiku-4-5-20251001",
        options_json=json.dumps({"max_tokens": 512, "temperature": 0.3}),
    )
    mc.update_content_hash()
    db_session.add(mc)
    db_session.flush()
    return mc


@pytest.fixture
def prompt(db_session):
    prompt, _ = create_prompt({
        "name": "test-stage-prompt",
        "role": "system",
        "content": "You write page content.",
        "description": "test",
    })
    return prompt


@pytest.fixture
def source_summary(db_session) -> GeneratedContent:
    """An L1 single_summary at depth 1 — the source for the new stages."""
    gc = GeneratedContent(
        source_type=ContentSourceType.DOCUMENTS,
        content="L1 summary content",
        content_stage=ContentStage.SINGLE_SUMMARY,
        generation_depth=1,
    )
    gc.update_content_hash()
    db_session.add(gc)
    db_session.flush()
    return gc


@pytest.fixture
def company(db_session) -> Company:
    company = Company(name="Test Co", ticker="TEST", exchanges=["NYSE"])
    db_session.add(company)
    db_session.flush()
    return company


def test_company_scope_stage_and_depth(db_session, model_config, prompt, source_summary, company):
    with patch("symbology.llm.client.get_generate_response", _fake_generate_response):
        content_hash, ok = generate_page_content(
            "company_main_content",
            [source_summary.content_hash],
            prompt, model_config,
            ticker="TEST",
        )

    assert ok and content_hash
    gc = get_generated_content_by_hash(content_hash)
    assert gc.content_stage == ContentStage.COMPANY_MAIN_CONTENT
    assert gc.company_id == company.id
    assert gc.filing_id is None and gc.document_id is None
    assert gc.generation_depth == 2  # source depth 1 + 1


def test_filing_scope(db_session, model_config, prompt, source_summary, company):
    filing = Filing(
        company_id=company.id, accession_number="0001234567-23-000001",
        form="10-K", filing_date=date(2023, 3, 15),
    )
    db_session.add(filing)
    db_session.flush()

    with patch("symbology.llm.client.get_generate_response", _fake_generate_response):
        content_hash, ok = generate_page_content(
            "filing_main_content",
            [source_summary.content_hash],
            prompt, model_config,
            filing_id=filing.id,
        )

    assert ok
    gc = get_generated_content_by_hash(content_hash)
    assert gc.content_stage == ContentStage.FILING_MAIN_CONTENT
    assert gc.filing_id == filing.id
    assert gc.company_id is None
    assert gc.generation_depth == 2


def test_document_scope(db_session, model_config, prompt, source_summary, company):
    filing = Filing(
        company_id=company.id, accession_number="0001234567-23-000002",
        form="10-K", filing_date=date(2023, 3, 15),
    )
    db_session.add(filing)
    db_session.flush()
    document = Document(
        company_id=company.id, filing_id=filing.id, title="doc.html",
        document_type=DocumentType.MDA, content="doc body", content_hash="dochash1",
    )
    db_session.add(document)
    db_session.flush()

    with patch("symbology.llm.client.get_generate_response", _fake_generate_response):
        content_hash, ok = generate_page_content(
            "document_page_intro",
            [source_summary.content_hash],
            prompt, model_config,
            document_id=document.id,
        )

    assert ok
    gc = get_generated_content_by_hash(content_hash)
    assert gc.content_stage == ContentStage.DOCUMENT_PAGE_INTRO
    assert gc.document_id == document.id
    assert gc.generation_depth == 2


def test_reuses_existing_page_content(db_session, model_config, prompt, source_summary, company):
    """Second call with the same (stage, sources, prompt, model_config) reuses
    the first result instead of re-invoking the LLM (mirrors L1 dedup)."""
    filing = Filing(
        company_id=company.id, accession_number="0001234567-23-000003",
        form="10-K", filing_date=date(2023, 3, 15),
    )
    db_session.add(filing)
    db_session.flush()
    document = Document(
        company_id=company.id, filing_id=filing.id, title="doc.html",
        document_type=DocumentType.MDA, content="doc body", content_hash="dochash-reuse",
    )
    db_session.add(document)
    db_session.flush()

    call_count = {"n": 0}

    def _counting_generate(*args, **kwargs):
        call_count["n"] += 1
        return _fake_generate_response(*args, **kwargs)

    with patch("symbology.llm.client.get_generate_response", _counting_generate):
        first_hash, first_ok = generate_page_content(
            "document_page_intro", [source_summary.content_hash],
            prompt, model_config, document_id=document.id,
        )
        second_hash, second_ok = generate_page_content(
            "document_page_intro", [source_summary.content_hash],
            prompt, model_config, document_id=document.id,
        )

    assert first_ok and second_ok
    assert first_hash == second_hash
    assert call_count["n"] == 1  # second call reused, no extra LLM invocation

    # force=True bypasses the dedup and re-invokes the LLM.
    with patch("symbology.llm.client.get_generate_response", _counting_generate):
        forced_hash, forced_ok = generate_page_content(
            "document_page_intro", [source_summary.content_hash],
            prompt, model_config, document_id=document.id, force=True,
        )
    assert forced_ok and forced_hash == first_hash
    assert call_count["n"] == 2


def test_no_sources_returns_failure(db_session, model_config, prompt):
    content_hash, ok = generate_page_content(
        "company_main_content", [], prompt, model_config, ticker="TEST",
    )
    assert content_hash is None and ok is False
