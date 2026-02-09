"""Bulk filing discovery — find new filings across ALL EDGAR companies."""
from datetime import date
from typing import Dict, List, Optional, Set

from symbology.database.base import get_db_session
from symbology.database.companies import Company, create_company, get_company_by_cik, update_company
from symbology.database.filings import Filing
from symbology.utils.logging import get_logger

logger = get_logger(__name__)

# Form types including amendments
BULK_FORM_TYPES = ["10-K", "10-K/A", "10-Q", "10-Q/A"]


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
    """Look up a company by CIK, creating a full record if not found.

    When creating, fetches entity data from EDGAR to populate ticker, SIC,
    exchanges, etc.  Falls back to a minimal record with a CIK{cik}
    placeholder ticker if the EDGAR lookup fails.

    Args:
        cik: Central Index Key from EDGAR.
        company_name: Company name from the filing.

    Returns:
        Existing or newly created Company object.
    """
    existing = get_company_by_cik(cik)
    if existing:
        # Enrich placeholder companies (missing SIC) with full EDGAR entity data
        if not existing.sic:
            enriched = _fetch_edgar_entity_data(cik, company_name)
            if enriched.get("sic"):
                updated = update_company(existing.id, enriched)
                if updated:
                    logger.info("enriched_placeholder_company", cik=cik, ticker=enriched.get("ticker"), sic=enriched.get("sic"))
                    return updated
        return existing

    # Fetch full EDGAR entity data (provides ticker, SIC, exchanges, etc.)
    company_data = _fetch_edgar_entity_data(cik, company_name)

    company = create_company(company_data)
    logger.info(
        "created_company_from_filing",
        cik=cik,
        company_name=company_name,
        ticker=company_data["ticker"],
        sic=company_data.get("sic"),
        company_id=str(company.id),
    )
    return company


def _fetch_edgar_entity_data(cik: str, fallback_name: str) -> Dict:
    """Fetch full entity data from EDGAR by CIK, falling back to minimal record.

    Returns:
        Dict suitable for create_company().
    """
    from datetime import date as date_cls

    try:
        import edgar as edgarlib

        entity = edgarlib.Company(int(cik))
        data = entity.data
        ticker = entity.get_ticker()

        # Truncate ticker to 10 chars (DB column limit)
        if ticker and len(ticker) > 10:
            ticker = f"CIK{cik}"

        company_data: Dict = {
            "name": data.name or fallback_name,
            "display_name": data.display_name,
            "ticker": ticker or f"CIK{cik}",
            "cik": cik,
            "exchanges": entity.get_exchanges() or [],
            "sic": data.sic,
            "sic_description": data.sic_description,
            "former_names": data.former_names if hasattr(data, "former_names") else [],
        }

        # Parse fiscal_year_end from MMDD string
        fye = getattr(entity, "fiscal_year_end", None)
        if isinstance(fye, str) and len(fye) == 4:
            try:
                month, day = int(fye[:2]), int(fye[2:])
                company_data["fiscal_year_end"] = date_cls(date_cls.today().year, month, day)
            except (ValueError, TypeError):
                pass

        return company_data
    except Exception:
        logger.debug("edgar_entity_lookup_failed", cik=cik, exc_info=True)
        return {
            "name": fallback_name,
            "ticker": f"CIK{cik}",
            "cik": cik,
            "exchanges": [],
        }
