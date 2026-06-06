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

    older = CompanyPageContent(company_id=company.id, form="10-K", created_at=datetime(2026, 1, 1))
    db_session.add(older)

    current = CompanyPageContent(
        company_id=company.id, form="10-K", main_content_id=main.id, intro_content_id=intro.id,
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


def test_company_page_current_filters_by_form(db_session, company):
    # A newer 10-Q page must not shadow the current 10-K page when a form is given.
    annual = CompanyPageContent(company_id=company.id, form="10-K",
                                created_at=datetime(2026, 1, 1))
    quarterly = CompanyPageContent(company_id=company.id, form="10-Q",
                                   created_at=datetime(2026, 3, 1))
    db_session.add_all([annual, quarterly])
    db_session.flush()

    assert get_current_company_page_content(company.id).id == quarterly.id  # latest of any form
    assert get_current_company_page_content(company.id, form="10-K").id == annual.id
    assert get_current_company_page_content(company.id, form="10-Q").id == quarterly.id


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


def _filing(db_session, company, form: str, period: date) -> Filing:
    f = Filing(
        company_id=company.id,
        accession_number=f"{form}-{period.isoformat()}",
        form=form,
        filing_date=period,
        period_of_report=period,
    )
    db_session.add(f)
    db_session.flush()
    return f


def test_select_source_filings_annual_takes_recent_10ks(db_session, company):
    from symbology.worker.page_pipelines import _select_source_filings

    k23 = _filing(db_session, company, "10-K", date(2023, 12, 31))
    k24 = _filing(db_session, company, "10-K", date(2024, 12, 31))
    k25 = _filing(db_session, company, "10-K", date(2025, 12, 31))
    _filing(db_session, company, "10-Q", date(2026, 3, 31))  # ignored for an annual page

    got = _select_source_filings(db_session, company, "10-K", lookback=2)
    assert [f.id for f in got] == [k25.id, k24.id]  # newest first, quarters excluded
    assert k23 not in got


def test_select_source_filings_quarterly_anchors_on_latest_10k(db_session, company):
    """A 10-Q page anchors on the most recent 10-K + the quarters since it,
    rather than straddling the annual (the CVS Q3-25 / Q1-26 gap)."""
    from symbology.worker.page_pipelines import _select_source_filings

    _filing(db_session, company, "10-Q", date(2025, 3, 31))   # FY25 Q1 (pre-annual)
    _filing(db_session, company, "10-Q", date(2025, 9, 30))   # FY25 Q3 (pre-annual)
    k25 = _filing(db_session, company, "10-K", date(2025, 12, 31))  # FY25 annual
    q1_26 = _filing(db_session, company, "10-Q", date(2026, 3, 31))  # FY26 Q1 (post-annual)

    # lookback=2 → the anchor annual + its single subsequent quarter, no straddle.
    got = _select_source_filings(db_session, company, "10-Q", lookback=2)
    assert [f.id for f in got] == [q1_26.id, k25.id]


def test_select_source_filings_quarterly_caps_cycle_quarters(db_session, company):
    from symbology.worker.page_pipelines import _select_source_filings

    k = _filing(db_session, company, "10-K", date(2024, 12, 31))
    q1 = _filing(db_session, company, "10-Q", date(2025, 3, 31))
    q2 = _filing(db_session, company, "10-Q", date(2025, 6, 30))
    q3 = _filing(db_session, company, "10-Q", date(2025, 9, 30))

    # lookback=5 → anchor + all three quarters of the cycle (newest first).
    got = _select_source_filings(db_session, company, "10-Q", lookback=5)
    assert [f.id for f in got] == [q3.id, q2.id, q1.id, k.id]

    # lookback=3 → anchor + the two most recent quarters of the cycle.
    got2 = _select_source_filings(db_session, company, "10-Q", lookback=3)
    assert [f.id for f in got2] == [q3.id, q2.id, k.id]


def test_select_source_filings_quarterly_falls_back_to_prior_cycle(db_session, company):
    """When no quarter has been filed since the most recent 10-K yet, anchor on
    the previous 10-K and use its (just-completed) cycle."""
    from symbology.worker.page_pipelines import _select_source_filings

    k24 = _filing(db_session, company, "10-K", date(2024, 12, 31))
    q2_25 = _filing(db_session, company, "10-Q", date(2025, 6, 30))
    q3_25 = _filing(db_session, company, "10-Q", date(2025, 9, 30))
    _filing(db_session, company, "10-K", date(2025, 12, 31))  # newest annual, no quarter after it

    got = _select_source_filings(db_session, company, "10-Q", lookback=5)
    assert [f.id for f in got] == [q3_25.id, q2_25.id, k24.id]


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
