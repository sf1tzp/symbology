"""Topic-clustering tests with hand-crafted embeddings (no embedding server).

Uses orthogonal/near-duplicate unit vectors so cluster membership is exactly
predictable, and asserts the properties cross-year diffing depends on: the same
risk clusters together across years, distinct risks stay apart, re-runs converge
without inflating membership, and unembedded/non-semantic chunks are skipped.
"""
from datetime import date

import pytest

from symbology.database.base import get_db_session
from symbology.database.chunk_topics import ChunkTopic, get_topics_for_scope
from symbology.database.companies import Company
from symbology.database.document_chunks import DocumentChunk, get_chunks_for_company_doctype
from symbology.database.documents import Document, DocumentType
from symbology.database.filings import Filing
from symbology.llm.topic_clustering import (
    assign_unclustered_chunks,
    recluster_company_doctype,
    TOPIC_DISTANCE_THRESHOLD,
)
from symbology.utils.config import settings

pytestmark = pytest.mark.integration

# Match the configured embedding dimension so hand-crafted vectors insert into
# the Vector(EMBEDDING_DIM) column regardless of the standardized model.
DIM = settings.openai.embedding_dimensions


def _vec(i: int, blend=None) -> list[float]:
    """Unit vector along axis ``i``; ``blend=(j, w)`` mixes in axis ``j`` by ``w``
    (a near-duplicate of ``_vec(i)`` for small ``w``)."""
    v = [0.0] * DIM
    if blend is None:
        v[i] = 1.0
    else:
        j, w = blend
        v[i] = 1.0 - w
        v[j] = w
    return v


def _add_chunk(document_id, idx, content, embedding, *, is_semantic=True) -> DocumentChunk:
    chunk = DocumentChunk(
        document_id=document_id,
        chunk_index=idx,
        content=content,
        embedding=embedding,
        is_semantic=is_semantic,
        section_path=f"§1A.{idx}",
        heading=content[:40],
    )
    chunk.update_content_hash()
    get_db_session().add(chunk)
    return chunk


def _setup_two_years(db_session):
    """One company, two 10-K filings (FY24, FY25) of risk factors.

    FY24: 'customers' (axis 0), 'semiconductor' (axis 1).
    FY25: 'customers' reworded (~axis 0), 'semiconductor' (~axis 1), 'cyber' (axis 2 — new).
    Returns ``(company_id, {label: DocumentChunk})``.
    """
    company = Company(name="Acme Inc", ticker="ACME", exchanges=["NYSE"], cik="0000111111")
    db_session.add(company)
    db_session.flush()

    f24 = Filing(company_id=company.id, accession_number="0000-24", form="10-K",
                 filing_date=date(2024, 12, 21), period_of_report=date(2024, 9, 30))
    f25 = Filing(company_id=company.id, accession_number="0000-25", form="10-K",
                 filing_date=date(2025, 12, 21), period_of_report=date(2025, 9, 30))
    db_session.add_all([f24, f25])
    db_session.flush()

    d24 = Document(company_id=company.id, filing_id=f24.id, title="RF24",
                   document_type=DocumentType.RISK_FACTORS, content="rf24")
    d25 = Document(company_id=company.id, filing_id=f25.id, title="RF25",
                   document_type=DocumentType.RISK_FACTORS, content="rf25")
    db_session.add_all([d24, d25])
    db_session.flush()

    chunks = {
        "cust24": _add_chunk(d24.id, 0, "customer concentration risk", _vec(0)),
        "semi24": _add_chunk(d24.id, 1, "semiconductor supply risk", _vec(1)),
        "cust25": _add_chunk(d25.id, 0, "customer concentration risk reworded", _vec(0, blend=(5, 0.05))),
        "semi25": _add_chunk(d25.id, 1, "semiconductor supply risk", _vec(1)),
        "cyber25": _add_chunk(d25.id, 2, "new cybersecurity risk", _vec(2)),
    }
    db_session.flush()
    return company.id, chunks


def _topic_of(chunk_id):
    return get_db_session().get(DocumentChunk, chunk_id).topic_id


def test_recluster_groups_same_risk_across_years(db_session):
    company_id, chunks = _setup_two_years(db_session)
    recluster_company_doctype(company_id, DocumentType.RISK_FACTORS)

    # Same risk across years shares a topic; distinct risks do not.
    assert _topic_of(chunks["cust24"].id) == _topic_of(chunks["cust25"].id)
    assert _topic_of(chunks["semi24"].id) == _topic_of(chunks["semi25"].id)
    assert _topic_of(chunks["cust24"].id) != _topic_of(chunks["semi24"].id)
    assert _topic_of(chunks["cyber25"].id) not in {
        _topic_of(chunks["cust24"].id), _topic_of(chunks["semi24"].id)
    }

    topics = get_topics_for_scope(company_id, DocumentType.RISK_FACTORS)
    assert len(topics) == 3
    by_id = {t.id: t for t in topics}
    assert by_id[_topic_of(chunks["cust24"].id)].member_count == 2
    assert by_id[_topic_of(chunks["semi24"].id)].member_count == 2
    assert by_id[_topic_of(chunks["cyber25"].id)].member_count == 1


def test_recluster_is_idempotent_grouping(db_session):
    company_id, chunks = _setup_two_years(db_session)
    recluster_company_doctype(company_id, DocumentType.RISK_FACTORS)

    def partition():
        # Group chunk labels by their topic id → a frozenset of frozensets.
        groups = {}
        for label, c in chunks.items():
            groups.setdefault(_topic_of(c.id), set()).add(label)
        return frozenset(frozenset(v) for v in groups.values())

    first = partition()
    recluster_company_doctype(company_id, DocumentType.RISK_FACTORS)
    second = partition()

    # The grouping (which chunks share a topic) is stable, and membership counts
    # are not inflated by the second run.
    assert first == second
    topics = get_topics_for_scope(company_id, DocumentType.RISK_FACTORS)
    assert len(topics) == 3
    assert sorted(t.member_count for t in topics) == [1, 2, 2]


def test_incremental_cold_start_then_attach_then_noop(db_session):
    company_id, chunks = _setup_two_years(db_session)
    fy24 = [chunks["cust24"], chunks["semi24"]]
    fy25 = [chunks["cust25"], chunks["semi25"], chunks["cyber25"]]

    cold = assign_unclustered_chunks(company_id, DocumentType.RISK_FACTORS, fy24)
    assert cold == {"created": 2, "attached": 0, "skipped": 0}

    nxt = assign_unclustered_chunks(company_id, DocumentType.RISK_FACTORS, fy25)
    assert nxt == {"created": 1, "attached": 2, "skipped": 0}

    # Re-running over already-clustered chunks is a no-op (carry-forward intent).
    again = assign_unclustered_chunks(
        company_id, DocumentType.RISK_FACTORS, fy24 + fy25
    )
    assert again == {"created": 0, "attached": 0, "skipped": 0}
    assert len(get_topics_for_scope(company_id, DocumentType.RISK_FACTORS)) == 3


def test_unembedded_and_non_semantic_chunks_are_skipped(db_session):
    company = Company(name="Beta Inc", ticker="BETA", exchanges=["NYSE"], cik="0000222222")
    db_session.add(company)
    db_session.flush()
    doc = Document(company_id=company.id, title="RF", document_type=DocumentType.RISK_FACTORS, content="x")
    db_session.add(doc)
    db_session.flush()

    no_emb = _add_chunk(doc.id, 0, "risk with no embedding", None)
    non_sem = _add_chunk(doc.id, 1, "paragraph fallback chunk", _vec(3), is_semantic=False)
    ok = _add_chunk(doc.id, 2, "a real semantic risk", _vec(4))
    db_session.flush()

    result = assign_unclustered_chunks(
        company.id, DocumentType.RISK_FACTORS, [no_emb, non_sem, ok]
    )
    assert result == {"created": 1, "attached": 0, "skipped": 2}
    assert _topic_of(no_emb.id) is None
    assert _topic_of(non_sem.id) is None
    assert _topic_of(ok.id) is not None


def test_noise_heading_chunk_clusters_but_label_is_not_seeded(db_session):
    # A chunk whose heading is a separator artifact ("__________") still clusters
    # (its body is kept for diffing), but it must not seed the topic's label with
    # the garbage heading — canonical_label stays NULL.
    company = Company(name="Delta Inc", ticker="DLTA", exchanges=["NYSE"], cik="0000444444")
    db_session.add(company)
    db_session.flush()
    doc = Document(company_id=company.id, title="RF", document_type=DocumentType.RISK_FACTORS, content="x")
    db_session.add(doc)
    db_session.flush()

    noise = _add_chunk(doc.id, 0, "__________", _vec(5))
    ok = _add_chunk(doc.id, 1, "a real semantic risk", _vec(6))
    db_session.flush()

    result = assign_unclustered_chunks(company.id, DocumentType.RISK_FACTORS, [noise, ok])
    assert result == {"created": 2, "attached": 0, "skipped": 0}
    noise_topic_id = _topic_of(noise.id)
    assert noise_topic_id is not None  # clustered, not dropped
    noise_topic = get_db_session().get(ChunkTopic, noise_topic_id)
    assert noise_topic.canonical_label is None  # garbage heading not used as label
    ok_topic = get_db_session().get(ChunkTopic, _topic_of(ok.id))
    assert ok_topic.canonical_label == "a real semantic risk"


def test_threshold_separates_borderline_chunks(db_session):
    # A near-duplicate (well within threshold) attaches; an orthogonal vector
    # (distance 1.0 ≫ threshold) starts its own topic.
    assert TOPIC_DISTANCE_THRESHOLD < 0.5  # guard: sane default
    company = Company(name="Gamma Inc", ticker="GAMA", exchanges=["NYSE"], cik="0000333333")
    db_session.add(company)
    db_session.flush()
    doc = Document(company_id=company.id, title="RF", document_type=DocumentType.RISK_FACTORS, content="x")
    db_session.add(doc)
    db_session.flush()

    base = _add_chunk(doc.id, 0, "base risk", _vec(7))
    near = _add_chunk(doc.id, 1, "near duplicate risk", _vec(7, blend=(8, 0.05)))
    far = _add_chunk(doc.id, 2, "unrelated risk", _vec(9))
    db_session.flush()

    assign_unclustered_chunks(company.id, DocumentType.RISK_FACTORS, [base, near, far])
    assert _topic_of(base.id) == _topic_of(near.id)
    assert _topic_of(far.id) != _topic_of(base.id)
    assert len(get_topics_for_scope(company.id, DocumentType.RISK_FACTORS)) == 2
