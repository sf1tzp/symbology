"""Unit tests for the deterministic section-aware document chunker.

Pure functions, no database. The properties asserted here (determinism,
partitioning, granularity) are the contract topic-clustering and diffing rely
on, so they are tested explicitly rather than assumed.
"""
from symbology.database.documents import DocumentType
from symbology.llm.section_chunker import (
    chunk_document_sections,
    SectionChunk,
    _is_heading_block,
)

# A realistic Risk Factors blob in the shape edgartools + normalize_filing_text
# produce: a section title + intro, a bare category header, then per-risk
# heading lines (some end in a period, some don't) each followed by body prose.
RISK_FACTORS = """Item 1A. Risk Factors

You should carefully consider the following risk factors, together with all of the other information included in this Annual Report on Form 10-K, before deciding to invest in our securities. Our business, financial condition, and results of operations could be materially adversely affected by any of these risks.

Risks Related to Our Business and Industry

We depend on a limited number of customers for a substantial portion of our revenue.

A significant portion of our net sales is concentrated among a small number of customers. The loss of one or more of these key customers, or a significant reduction in orders from them, could materially and adversely affect our revenue and operating results in any given period.

Our products rely on specialized semiconductor components for which alternative suppliers may not be readily available.

A meaningful portion of our Electronic Technologies Group products depend on semiconductor components sourced from a limited number of foundries. A loss of supply or substantial price increases in these components could materially affect our ability to manufacture, deliver, or service these products and could harm our financial results.

We seek to qualify second sources where commercially practicable, but the certification cycle for replacement components can extend twelve to twenty-four months in certain defense applications.

Cybersecurity threats and incidents could disrupt our operations and harm our reputation.

We face persistent cybersecurity threats from a range of actors, including nation-state actors targeting the defense supply chain. A successful attack on our information systems or those of our suppliers could result in the theft of sensitive data, disruption of our operations, and significant remediation costs."""


def test_returns_empty_for_blank_input():
    assert chunk_document_sections(None, DocumentType.RISK_FACTORS) == []
    assert chunk_document_sections("   \n\n  ", DocumentType.RISK_FACTORS) == []


def test_deterministic():
    a = chunk_document_sections(RISK_FACTORS, DocumentType.RISK_FACTORS)
    b = chunk_document_sections(RISK_FACTORS, DocumentType.RISK_FACTORS)
    assert a == b  # frozen dataclasses compare by value
    assert len(a) >= 3


def test_partitioning_no_overlap_and_text_matches_offsets():
    chunks = chunk_document_sections(RISK_FACTORS, DocumentType.RISK_FACTORS)
    # chunk_index is sequential
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    prev_end = 0
    for c in chunks:
        # offsets are ordered and non-overlapping
        assert c.char_start >= prev_end
        assert c.char_end > c.char_start
        # stored text is exactly the (stripped) slice of the source
        assert c.text == RISK_FACTORS[c.char_start:c.char_end].strip()
        assert c.text  # non-empty
        prev_end = c.char_end


def test_section_paths_are_risk_factor_locators():
    chunks = chunk_document_sections(RISK_FACTORS, DocumentType.RISK_FACTORS)
    assert all(c.section_path.startswith("§1A.") for c in chunks)
    assert all(c.is_semantic for c in chunks)


def test_per_risk_granularity_and_heading_capture():
    chunks = chunk_document_sections(RISK_FACTORS, DocumentType.RISK_FACTORS)
    # The three distinct risks land in distinct chunks, each carrying the
    # relevant body text.
    semiconductor = [c for c in chunks if "semiconductor components sourced" in c.text]
    customers = [c for c in chunks if "concentrated among a small number" in c.text]
    cyber = [c for c in chunks if "persistent cybersecurity threats" in c.text]
    assert len(semiconductor) == 1
    assert len(customers) == 1
    assert len(cyber) == 1
    # They are three separate chunks (per-item, not one big blob).
    assert len({c.chunk_index for c in semiconductor + customers + cyber}) == 3
    # The semiconductor risk keeps its own heading, not the category header.
    assert "semiconductor components" in (semiconductor[0].heading or "")
    # The bare category header folded forward (it is not a chunk on its own).
    assert not any(c.text.strip() == "Risks Related to Our Business and Industry" for c in chunks)


def test_bare_category_header_folds_into_first_risk():
    chunks = chunk_document_sections(RISK_FACTORS, DocumentType.RISK_FACTORS)
    customers = next(c for c in chunks if "concentrated among a small number" in c.text)
    # The category header text is carried as a prefix of the first real risk.
    assert "Risks Related to Our Business and Industry" in customers.text


def test_paragraph_fallback_when_no_headings():
    # Pure prose, no short heading lines → non-semantic paragraph chunks.
    prose = "\n\n".join(
        "This is a substantial paragraph of continuous prose that runs well beyond "
        "the heading length threshold so that it can never be mistaken for a heading "
        f"line, sentence number {i}." for i in range(8)
    )
    chunks = chunk_document_sections(prose, DocumentType.RISK_FACTORS)
    assert chunks
    assert all(not c.is_semantic for c in chunks)
    assert all(c.heading is None for c in chunks)
    assert all("#" in c.section_path for c in chunks)


def test_non_semantic_doctype_uses_fallback_even_with_headings():
    # CONTROLS_PROCEDURES is prose we don't segment by heading.
    chunks = chunk_document_sections(RISK_FACTORS, DocumentType.CONTROLS_PROCEDURES)
    assert chunks
    assert all(not c.is_semantic for c in chunks)
    assert all(c.section_path.startswith("§9A") for c in chunks)


def test_numbering_drift_same_text_same_chunks():
    # The same risk text appearing under a different ordinal/year still produces
    # the same chunk text + heading (identity is content, not position).
    year_a = RISK_FACTORS
    # Simulate FY+1: an extra risk inserted up front shifts everything down.
    extra = (
        "Macroeconomic conditions and inflation could adversely affect demand.\n\n"
        "Adverse macroeconomic conditions, including inflation and higher interest "
        "rates, could reduce customer demand and compress our margins over time."
    )
    year_b = RISK_FACTORS.replace(
        "Risks Related to Our Business and Industry\n\n",
        "Risks Related to Our Business and Industry\n\n" + extra + "\n\n",
    )
    chunks_a = chunk_document_sections(year_a, DocumentType.RISK_FACTORS)
    chunks_b = chunk_document_sections(year_b, DocumentType.RISK_FACTORS)
    # The cybersecurity risk text is identical across years even though its
    # position/ordinal changed.
    cyber_a = next(c for c in chunks_a if "persistent cybersecurity threats" in c.text)
    cyber_b = next(c for c in chunks_b if "persistent cybersecurity threats" in c.text)
    assert cyber_a.text == cyber_b.text
    assert cyber_a.heading == cyber_b.heading


def test_is_heading_block_heuristic():
    assert _is_heading_block("We depend on a limited number of customers.")
    assert _is_heading_block("Risks Related to Our Business and Industry")
    assert _is_heading_block("Item 1A. Risk Factors")
    # SEC risk headings are often full sentences ending in a period — those are
    # accepted; the block layout (a short standalone line above a longer body
    # block) is what disambiguates heading from body, not this per-line check.
    assert _is_heading_block(
        "Our products rely on specialized semiconductor components for which "
        "alternative suppliers may not be readily available."
    )
    # A long multi-sentence body block is over the length budget ⇒ not a heading.
    assert not _is_heading_block(
        "A significant portion of our net sales is concentrated among a small "
        "number of customers. The loss of one or more of these key customers, or a "
        "significant reduction in orders from them, could materially and adversely "
        "affect our revenue and operating results in any given period."
    )
    # Mid-clause trailing punctuation disqualifies.
    assert not _is_heading_block("We depend on a limited number of customers,")
    # Multi-line block is a paragraph, not a heading.
    assert not _is_heading_block("First line\nsecond line")


def test_all_chunks_are_sectionchunk_instances():
    chunks = chunk_document_sections(RISK_FACTORS, DocumentType.RISK_FACTORS)
    assert all(isinstance(c, SectionChunk) for c in chunks)
