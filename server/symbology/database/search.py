"""Database search functions using PostgreSQL full-text search."""
from datetime import date
from typing import Any, Dict, List, Optional

import sqlalchemy as sa
from sqlalchemy import func, literal, union_all
from symbology.database.base import get_db_session
from symbology.database.companies import Company
from symbology.database.filings import Filing
from symbology.database.generated_content import GeneratedContent
from symbology.utils.logging import get_logger

logger = get_logger(__name__)


def unified_search(
    query: str,
    entity_types: Optional[List[str]] = None,
    sic: Optional[str] = None,
    form_type: Optional[str] = None,
    document_type: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = 20,
    offset: int = 0,
) -> Dict[str, Any]:
    """Perform full-text search across companies, filings, and generated content.

    Uses PostgreSQL websearch_to_tsquery for Google-like query syntax and
    ts_rank for relevance scoring. Results from different entity types are
    combined with UNION ALL and ordered by rank.

    Args:
        query: Search string (supports AND, OR, - for exclusion, "exact phrases")
        entity_types: Filter to specific types: "company", "filing", "generated_content"
        sic: Filter companies by SIC code
        form_type: Filter filings by form type (10-K, 10-Q, etc.)
        document_type: Filter generated content by document type (MDA, RISK_FACTORS, etc.)
        date_from: Filter results from this date onwards
        date_to: Filter results up to this date
        limit: Maximum results to return
        offset: Pagination offset

    Returns:
        Dict with "results" list and "total" count
    """
    session = get_db_session()

    ts_query = func.websearch_to_tsquery("english", query)

    if not entity_types:
        entity_types = ["company", "filing", "generated_content"]

    subqueries = []

    if "company" in entity_types:
        company_q = session.query(
            literal("company").label("entity_type"),
            Company.id.label("id"),
            func.ts_rank(Company.search_vector, ts_query).label("rank"),
            func.ts_headline(
                "english",
                func.concat_ws(" ", Company.name, Company.ticker, Company.sic_description),
                ts_query,
                "MaxWords=50, MinWords=10, StartSel=<mark>, StopSel=</mark>",
            ).label("headline"),
            Company.name.label("title"),
            Company.ticker.label("subtitle"),
            literal(None).cast(sa.Date).label("date_value"),
        ).filter(Company.search_vector.op("@@")(ts_query))

        if sic:
            company_q = company_q.filter(Company.sic == sic)

        subqueries.append(company_q)

    if "filing" in entity_types:
        filing_q = session.query(
            literal("filing").label("entity_type"),
            Filing.id.label("id"),
            func.ts_rank(Filing.search_vector, ts_query).label("rank"),
            func.ts_headline(
                "english",
                func.concat_ws(" ", Filing.accession_number, Filing.form),
                ts_query,
                "MaxWords=50, MinWords=10, StartSel=<mark>, StopSel=</mark>",
            ).label("headline"),
            Filing.form.label("title"),
            Filing.accession_number.label("subtitle"),
            Filing.filing_date.label("date_value"),
        ).filter(Filing.search_vector.op("@@")(ts_query))

        if form_type:
            filing_q = filing_q.filter(Filing.form == form_type)
        if date_from:
            filing_q = filing_q.filter(Filing.filing_date >= date_from)
        if date_to:
            filing_q = filing_q.filter(Filing.filing_date <= date_to)

        subqueries.append(filing_q)

    if "generated_content" in entity_types:
        gc_q = session.query(
            literal("generated_content").label("entity_type"),
            GeneratedContent.id.label("id"),
            func.ts_rank(GeneratedContent.search_vector, ts_query).label("rank"),
            func.ts_headline(
                "english",
                func.concat_ws(" ", GeneratedContent.summary, GeneratedContent.description),
                ts_query,
                "MaxWords=50, MinWords=10, StartSel=<mark>, StopSel=</mark>",
            ).label("headline"),
            GeneratedContent.description.label("title"),
            GeneratedContent.form_type.label("subtitle"),
            GeneratedContent.created_at.label("date_value"),
        ).filter(GeneratedContent.search_vector.op("@@")(ts_query))

        if document_type:
            gc_q = gc_q.filter(
                GeneratedContent.document_type == document_type
            )
        if date_from:
            gc_q = gc_q.filter(GeneratedContent.created_at >= date_from)
        if date_to:
            gc_q = gc_q.filter(GeneratedContent.created_at <= date_to)

        subqueries.append(gc_q)

    if not subqueries:
        return {"results": [], "total": 0}

    combined = union_all(*[q.subquery().select() for q in subqueries]).subquery()

    total = session.query(func.count()).select_from(combined).scalar() or 0

    results = (
        session.query(combined)
        .order_by(combined.c.rank.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "results": [
            {
                "entity_type": r.entity_type,
                "id": str(r.id),
                "rank": float(r.rank),
                "headline": r.headline,
                "title": r.title,
                "subtitle": r.subtitle,
                "date_value": str(r.date_value) if r.date_value else None,
            }
            for r in results
        ],
        "total": total,
    }
