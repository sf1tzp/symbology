"""Integration tests for the PageContent publishing layer (Area 5).

Covers slot relationships, the change-report map (report + intro per doc_type),
M2M provenance to domain entities, and latest-by-created_at versioning via the
get_current_* read helpers. Uses the centrally-wired test session.
"""
from datetime import date, datetime

import pytest

from symbology.database.companies import Company
from symbology.database.company_groups import CompanyGroup
from symbology.database.documents import Document, DocumentType
from symbology.database.filings import Filing
from symbology.database.generated_content import ContentSourceType, GeneratedContent
from symbology.database.page_content import (
    CompanyPageContent,
    CompanyPageContentChangeReport,
    DocumentPageContent,
    FilingPageContent,
    GroupPageContent,
    get_current_company_page_content,
    get_current_document_page_content,
    get_current_filing_page_content,
    get_current_group_page_content,
)

pytestmark = pytest.mark.integration


def _gc(db_session, text: str) -> GeneratedContent:
    gc = GeneratedContent(source_type=ContentSourceType.GENERATED_CONTENT, content=text)
    gc.update_content_hash()
    db_session.add(gc)
    db_session.flush()
    return gc


@pytest.fixture
def company(db_session) -> Company:
    c = Company(name="Test Co", ticker="TEST", exchanges=["NYSE"])
    db_session.add(c)
    db_session.flush()
    return c


@pytest.fixture
def filing(db_session, company) -> Filing:
    f = Filing(company_id=company.id, accession_number="0001234567-23-000001",
               form="10-K", filing_date=date(2023, 3, 15))
    db_session.add(f)
    db_session.flush()
    return f


def test_company_page_current_slots_map_and_provenance(db_session, company, filing):
    main, intro = _gc(db_session, "company main"), _gc(db_session, "company intro")
    cr, cr_intro = _gc(db_session, "biz desc change report"), _gc(db_session, "cr intro")

    older = CompanyPageContent(company_id=company.id, created_at=datetime(2026, 1, 1))
    db_session.add(older)

    current = CompanyPageContent(
        company_id=company.id, main_content_id=main.id, intro_content_id=intro.id,
        created_at=datetime(2026, 2, 1),
    )
    current.source_filings.append(filing)
    current.change_reports.append(CompanyPageContentChangeReport(
        document_type=DocumentType.DESCRIPTION,
        change_report_id=cr.id, change_report_intro_id=cr_intro.id,
    ))
    db_session.add(current)
    db_session.flush()

    got = get_current_company_page_content(company.id)
    assert got.id == current.id  # latest by created_at wins
    assert got.main_content.content == "company main"
    assert got.intro_content.content == "company intro"
    assert [f.id for f in got.source_filings] == [filing.id]
    assert len(got.change_reports) == 1
    entry = got.change_reports[0]
    assert entry.document_type == DocumentType.DESCRIPTION
    assert entry.change_report.content == "biz desc change report"
    assert entry.change_report_intro.content == "cr intro"


def test_filing_page_current_and_source_documents(db_session, company, filing):
    doc = Document(company_id=company.id, filing_id=filing.id, title="d.html",
                   document_type=DocumentType.MDA, content="body", content_hash="h1")
    db_session.add(doc)
    db_session.flush()
    main = _gc(db_session, "filing main")

    fp = FilingPageContent(filing_id=filing.id, main_content_id=main.id,
                           created_at=datetime(2026, 1, 1))
    fp.source_documents.append(doc)
    db_session.add(fp)
    db_session.flush()

    got = get_current_filing_page_content(filing.id)
    assert got.id == fp.id
    assert got.main_content.content == "filing main"
    assert [d.id for d in got.source_documents] == [doc.id]


def test_document_page_current(db_session, company, filing):
    doc = Document(company_id=company.id, filing_id=filing.id, title="d.html",
                   document_type=DocumentType.MDA, content="body", content_hash="h2")
    db_session.add(doc)
    db_session.flush()
    summary, intro = _gc(db_session, "l1 summary"), _gc(db_session, "doc intro")

    dp = DocumentPageContent(document_id=doc.id, summary_content_id=summary.id,
                             intro_content_id=intro.id, created_at=datetime(2026, 1, 1))
    db_session.add(dp)
    db_session.flush()

    got = get_current_document_page_content(doc.id)
    assert got.summary_content.content == "l1 summary"
    assert got.intro_content.content == "doc intro"


def test_group_page_current_and_members(db_session, company):
    group = CompanyGroup(name="Sector", slug="sector")
    db_session.add(group)
    db_session.flush()
    main = _gc(db_session, "group main")

    gp = GroupPageContent(company_group_id=group.id, main_content_id=main.id,
                          created_at=datetime(2026, 1, 1))
    gp.member_companies.append(company)
    db_session.add(gp)
    db_session.flush()

    got = get_current_group_page_content(group.id)
    assert got.main_content.content == "group main"
    assert [c.id for c in got.member_companies] == [company.id]


def test_no_current_returns_none(db_session, company):
    assert get_current_company_page_content(company.id) is None
