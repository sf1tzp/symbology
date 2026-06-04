"""Integration test for the year-over-year diff pipeline.

Embeddings are mocked by *topic keyword* so reworded versions of the same risk
cluster together across years (a hash-of-text fake would make every reworded
risk a brand-new topic). Then the pipeline's alignment + classification is
asserted: new / removed / escalated / unchanged, with lossless ops.
"""
from datetime import date

import pytest

from symbology.database.base import get_db_session
from symbology.database.companies import Company
from symbology.database.documents import Document, DocumentType
from symbology.database.filings import Filing
from symbology.database.section_diffs import get_current_diff_set
from symbology.llm import content_processing
from symbology.llm.topic_clustering import recluster_company_doctype
from symbology.worker.diff_pipeline import company_diff_pipeline
from symbology.utils.config import settings

pytestmark = pytest.mark.integration

DIM = settings.openai.embedding_dimensions
# Keyword -> embedding axis: any chunk containing the keyword maps to that axis,
# so reworded versions of the same risk share a topic across filings.
_TOPIC_AXES = {"customer": 0, "semiconductor": 1, "cyber": 2, "pandemic": 3}


def _fake_embed_texts(texts, **kwargs):
    out = []
    for t in texts:
        tl = t.lower()
        axis = next((ax for kw, ax in _TOPIC_AXES.items() if kw in tl), 100)
        v = [0.0] * DIM
        v[axis] = 1.0
        out.append(v)
    return out


@pytest.fixture
def patched_embeddings(monkeypatch):
    monkeypatch.setattr(content_processing, "embed_texts", _fake_embed_texts)
    monkeypatch.setattr(content_processing, "init_embedding_client", lambda *a, **k: object())


_SEMI = (
    "Our products rely on specialized semiconductor components.\n\n"
    "A meaningful portion of our products depend on semiconductor components sourced "
    "from a limited number of foundries, and a loss of supply or substantial price "
    "increases could materially affect our ability to manufacture and deliver products."
)
_INTRO = (
    "Item 1A. Risk Factors\n\n"
    "You should carefully consider the following risks together with all other "
    "information in this report before investing in our securities, as any of them "
    "could materially and adversely affect our business and results of operations."
)

FY24_RF = "\n\n".join([
    _INTRO,
    "We depend on a limited number of customers.\n\n"
    "A significant portion of our net sales is concentrated among a small number of "
    "customers, and the loss of any one of them could hurt our results.",
    _SEMI,
    "Pandemic-related disruptions could reduce demand.\n\n"
    "A resurgence of pandemic conditions could disrupt travel and reduce demand for "
    "our commercial aviation products across multiple operating segments and regions.",
])

FY25_RF = "\n\n".join([
    _INTRO,
    # Customer risk — materially expanded ⇒ escalated, still clusters on "customer".
    "We depend on a limited number of customers.\n\n"
    "A significant and growing portion of our net sales is concentrated among a small "
    "number of customers. The loss of any one of these key customers, a material "
    "reduction in their order volumes, delays in their programs, or a deterioration in "
    "their financial condition could each materially and adversely affect our revenue, "
    "our operating margins, and our results of operations in any given fiscal period.",
    _SEMI,  # identical ⇒ unchanged
    # Brand-new cyber risk.
    "Cybersecurity threats could disrupt our operations.\n\n"
    "We face persistent cybersecurity threats from a range of actors, and a successful "
    "attack on our information systems could result in the theft of sensitive data and "
    "significant disruption of our operations and remediation costs.",
    # Pandemic risk dropped ⇒ removed.
])


def _setup(db_session):
    company = Company(name="Heico Corp", ticker="HEI", exchanges=["NYSE"], cik="0000046619")
    db_session.add(company)
    db_session.flush()
    for yr, content in ((2024, FY24_RF), (2025, FY25_RF)):
        f = Filing(company_id=company.id, accession_number=f"HEI-{yr}", form="10-K",
                   filing_date=date(yr, 12, 21), period_of_report=date(yr, 9, 30))
        db_session.add(f)
        db_session.flush()
        d = Document(company_id=company.id, filing_id=f.id, title=f"RF{yr}",
                     document_type=DocumentType.RISK_FACTORS, content=content)
        d.update_content_hash()
        db_session.add(d)
        db_session.flush()
        content_processing.chunk_embed_and_cluster_document(d.id, cluster=False)
    # Deterministic topics across both filings.
    recluster_company_doctype(company.id, DocumentType.RISK_FACTORS)
    return company


def test_diff_pipeline_aligns_classifies_and_counts(db_session, patched_embeddings):
    company = _setup(db_session)
    diff_sets = company_diff_pipeline(company, form="10-K", generate_summaries=False)

    rf = [ds for ds in diff_sets if ds.document_type == DocumentType.RISK_FACTORS]
    assert len(rf) == 1
    diff_set = rf[0]
    counts = diff_set.counts
    assert counts["new"] == 1        # cyber
    assert counts["removed"] == 1    # pandemic
    assert counts["escalated"] == 1  # customers (expanded)
    assert counts["unchanged"] == 2  # intro + semiconductor (identical)
    assert counts["total_compared"] == 5

    by_kind = {}
    for sd in diff_set.section_diffs:
        by_kind.setdefault(sd.change_kind, []).append(sd)

    new = by_kind["new"][0]
    assert "cyber" in (new.heading or "").lower()
    assert new.left_chunk_id is None and new.right_chunk_id is not None
    assert new.ops and new.ops[0]["op"] == "insert"

    removed = by_kind["removed"][0]
    assert "pandemic" in (removed.heading or "").lower()
    assert removed.right_chunk_id is None and removed.left_chunk_id is not None

    escalated = by_kind["escalated"][0]
    assert "customer" in (escalated.heading or "").lower()
    assert escalated.length_delta > 0
    # ops losslessly reconstruct both columns.
    left = "".join(o["text"] for o in escalated.ops if o["op"] in ("equal", "delete"))
    right = "".join(o["text"] for o in escalated.ops if o["op"] in ("equal", "insert"))
    assert "concentrated among a small number of" in left
    assert "operating margins" in right


def test_noise_representative_heading_falls_back_to_readable_member(db_session):
    # A topic whose representative (longest) chunk has a "__________" heading
    # should display a *readable* member heading instead; a topic where every
    # member heading is noise displays nothing (UI falls back to section path).
    from symbology.database.chunk_topics import create_chunk_topic
    from symbology.database.document_chunks import DocumentChunk
    from symbology.worker.diff_pipeline import _diff_one_doctype

    company = Company(name="Ciena", ticker="CIEN", exchanges=["NYSE"], cik="0000936395")
    db_session.add(company)
    db_session.flush()

    filings, docs = {}, {}
    for yr in (2024, 2025):
        f = Filing(company_id=company.id, accession_number=f"CIEN-{yr}", form="10-K",
                   filing_date=date(yr, 12, 15), period_of_report=date(yr, 9, 30))
        db_session.add(f)
        db_session.flush()
        d = Document(company_id=company.id, filing_id=f.id, title=f"RF{yr}",
                     document_type=DocumentType.RISK_FACTORS, content="x")
        d.update_content_hash()
        db_session.add(d)
        db_session.flush()
        filings[yr], docs[yr] = f, d

    topic_a = create_chunk_topic(company.id, DocumentType.RISK_FACTORS, [1.0] + [0.0] * (DIM - 1))
    topic_b = create_chunk_topic(company.id, DocumentType.RISK_FACTORS, [0.0, 1.0] + [0.0] * (DIM - 2))

    def _chunk(doc_id, idx, content, heading, topic_id):
        c = DocumentChunk(document_id=doc_id, chunk_index=idx, content=content, embedding=None,
                          is_semantic=True, topic_id=topic_id, section_path=f"§1A.{idx}", heading=heading)
        c.update_content_hash()
        db_session.add(c)
        return c

    # Topic A: long representative carries a separator heading; a shorter member
    # of the same topic carries the readable heading.
    _chunk(docs[2024].id, 0, "Gary B. Smith joined Ciena in 1997 and has served as CEO since 2001.",
           "__________", topic_a.id)
    _chunk(docs[2025].id, 0,
           "Gary B. Smith joined Ciena in 1997 and has served as CEO since 2001, and also as President.",
           "__________", topic_a.id)
    _chunk(docs[2025].id, 1, "Executive officers table.",
           "Information about our Executive Officers", topic_a.id)
    # Topic B: every member heading is noise.
    _chunk(docs[2024].id, 2, "Pandemic risk.", "__________", topic_b.id)
    _chunk(docs[2025].id, 2, "Pandemic risk changed.", "__________", topic_b.id)
    db_session.flush()

    ds = _diff_one_doctype(company, DocumentType.RISK_FACTORS, filings[2024], filings[2025], "10-K")
    assert ds is not None
    by_topic = {sd.topic_id: sd for sd in ds.section_diffs}
    # Readable member heading substituted for the representative's separator.
    assert by_topic[topic_a.id].heading == "Information about our Executive Officers"
    # No readable heading anywhere → None (UI shows the section path).
    assert by_topic[topic_b.id].heading is None


def test_diff_pipeline_is_idempotent_for_the_pair(db_session, patched_embeddings):
    company = _setup(db_session)
    company_diff_pipeline(company, form="10-K", generate_summaries=False)
    # Snapshot the counts as a plain dict — the re-run below deletes this row.
    first_counts = dict(get_current_diff_set(company.id, DocumentType.RISK_FACTORS).counts)
    company_diff_pipeline(company, form="10-K", generate_summaries=False)
    second = get_current_diff_set(company.id, DocumentType.RISK_FACTORS)

    # Re-running replaces (not duplicates) the diff set for the pair.
    from symbology.database.section_diffs import DiffSet
    n = (
        get_db_session().query(DiffSet)
        .filter(DiffSet.company_id == company.id,
                DiffSet.document_type == DocumentType.RISK_FACTORS)
        .count()
    )
    assert n == 1
    assert second.counts == first_counts
