"""Bulk filing discovery — find new filings across ALL EDGAR companies."""
from datetime import date
from typing import Dict, List, Optional, Set

from symbology.database.base import get_db_session
from symbology.database.companies import Company, create_company, get_company_by_cik
from symbology.database.filings import Filing
from symbology.utils.logging import get_logger

logger = get_logger(__name__)

# Form types including amendments
BULK_FORM_TYPES = ["10-K", "10-K/A", "10-Q", "10-Q/A", "8-K", "8-K/A"]


def get_known_accession_numbers(form_types: Optional[List[str]] = None) -> Set[str]:
    """Return all accession numbers already in the DB, optionally filtered by form type.

    Args:
        form_types: Optional list of form types to filter by.

    Returns:
        Set of known accession numbers.
    """
    session = get_db_session()
    query = session.query(Filing.accession_number)
    if form_types:
        query = query.filter(Filing.form.in_(form_types))
    rows = query.all()
    return {r[0] for r in rows}


def discover_filings_by_date_range(
    start_date: date,
    end_date: date,
    form_types: Optional[List[str]] = None,
) -> List[Dict]:
    """Discover filings from EDGAR's quarterly index for a date range.

    Uses edgar.get_filings() which queries the full EDGAR index across all companies.

    Args:
        start_date: Start of date range.
        end_date: End of date range.
        form_types: Form types to discover (default: BULK_FORM_TYPES).

    Returns:
        List of filing dicts not yet in the DB: {cik, company_name, accession_number, filing_date, form}
    """
    import edgar

    if form_types is None:
        form_types = BULK_FORM_TYPES

    known = get_known_accession_numbers(form_types)
    new_filings: List[Dict] = []

    for form in form_types:
        try:
            filings = edgar.get_filings(
                form=form,
                filing_date=f"{start_date.isoformat()}:{end_date.isoformat()}",
            )
            if filings is None:
                continue

            for filing in filings:
                if filing.accession_number in known:
                    continue
                new_filings.append({
                    "cik": str(filing.cik),
                    "company_name": filing.company,
                    "accession_number": filing.accession_number,
                    "filing_date": str(filing.filing_date),
                    "form": filing.form,
                })
        except Exception:
            logger.exception("discover_filings_by_date_range_error", form=form)

    logger.info(
        "discover_filings_by_date_range_done",
        start_date=str(start_date),
        end_date=str(end_date),
        forms=form_types,
        total_new=len(new_filings),
    )
    return new_filings


def discover_current_filings(
    form_types: Optional[List[str]] = None,
) -> List[Dict]:
    """Discover filings from EDGAR's near-real-time current feed (~last 24h).

    Uses edgar.get_current_filings() for ongoing scheduled polling.

    Args:
        form_types: Form types to discover (default: BULK_FORM_TYPES).

    Returns:
        List of filing dicts not yet in the DB.
    """
    import edgar

    if form_types is None:
        form_types = BULK_FORM_TYPES

    known = get_known_accession_numbers(form_types)
    new_filings: List[Dict] = []

    for form in form_types:
        try:
            filings = edgar.get_current_filings(form=form)
            if filings is None:
                continue

            for filing in filings:
                if filing.accession_number in known:
                    continue
                new_filings.append({
                    "cik": str(filing.cik),
                    "company_name": filing.company,
                    "accession_number": filing.accession_number,
                    "filing_date": str(filing.filing_date),
                    "form": filing.form,
                })
        except Exception:
            logger.exception("discover_current_filings_error", form=form)

    logger.info(
        "discover_current_filings_done",
        forms=form_types,
        total_new=len(new_filings),
    )
    return new_filings


def get_or_create_company_from_filing(cik: str, company_name: str) -> Company:
    """Look up a company by CIK, creating a minimal record if not found.

    New companies get a placeholder ticker of CIK{cik_padded} (e.g. CIK0000012345)
    which can be enriched later with the real ticker.

    Args:
        cik: Central Index Key from EDGAR.
        company_name: Company name from the filing.

    Returns:
        Existing or newly created Company object.
    """
    existing = get_company_by_cik(cik)
    if existing:
        return existing

    # Create minimal company record with placeholder ticker
    padded_cik = cik.zfill(10)
    placeholder_ticker = f"CIK{padded_cik}"

    company = create_company({
        "name": company_name,
        "ticker": placeholder_ticker,
        "cik": cik,
        "exchanges": [],
    })
    logger.info(
        "created_placeholder_company",
        cik=cik,
        company_name=company_name,
        placeholder_ticker=placeholder_ticker,
        company_id=str(company.id),
    )
    return company
