"""EDGAR polling — detect new filings and enqueue pipeline jobs."""
from datetime import date, timedelta
from typing import List, Set
from uuid import UUID

from symbology.database.base import get_db_session
from symbology.database.companies import Company, get_all_company_tickers
from symbology.database.filings import Filing
from symbology.database.jobs import JobType, create_job
from symbology.utils.logging import get_logger

logger = get_logger(__name__)


def _known_accession_numbers(company_id: UUID, forms: List[str]) -> Set[str]:
    """Return the set of accession numbers already in the DB for the given company and forms."""
    session = get_db_session()
    rows = (
        session.query(Filing.accession_number)
        .filter(Filing.company_id == company_id, Filing.form.in_(forms))
        .all()
    )
    return {r[0] for r in rows}


def _fetch_recent_edgar_filings(ticker: str, form: str, count: int = 10) -> list:
    """Fetch recent filings from EDGAR for a ticker/form. Isolated for testability."""
    from edgar import Company as EdgarCompany

    edgar_company = EdgarCompany(ticker)
    edgar_filings = edgar_company.get_filings(form=form).latest(count)
    if edgar_filings is None:
        return []
    try:
        return list(edgar_filings)
    except TypeError:
        return [edgar_filings]


def check_company_for_new_filings(
    ticker: str,
    forms: List[str],
    lookback_days: int = 30,
) -> List[str]:
    """Query EDGAR for recent filings and return accession numbers not yet in the DB.

    Args:
        ticker: Company ticker symbol.
        forms: Form types to check (e.g. ["10-K", "10-Q"]).
        lookback_days: Only consider filings filed within this many days.

    Returns:
        List of new accession numbers found on EDGAR but missing from the DB.
    """
    session = get_db_session()
    company = session.query(Company).filter(Company.ticker == ticker).first()
    if not company:
        logger.warning("poll_company_not_found", ticker=ticker)
        return []

    known = _known_accession_numbers(company.id, forms)
    cutoff = date.today() - timedelta(days=lookback_days)

    new_accessions: List[str] = []

    for form in forms:
        try:
            filings_iter = _fetch_recent_edgar_filings(ticker, form)

            for filing in filings_iter:
                if filing.filing_date < cutoff:
                    continue
                if filing.accession_number not in known:
                    new_accessions.append(filing.accession_number)
                    logger.info(
                        "new_filing_detected",
                        ticker=ticker,
                        form=form,
                        accession=filing.accession_number,
                        filing_date=str(filing.filing_date),
                    )
        except Exception:
            logger.exception("edgar_poll_error", ticker=ticker, form=form)

    return new_accessions


def _init_edgar() -> None:
    """Authenticate with EDGAR. Isolated for testability."""
    from symbology.ingestion.edgar_db.accessors import edgar_login
    from symbology.utils.config import settings

    edgar_login(settings.edgar_api.edgar_contact)


def poll_all_companies(
    forms: List[str],
    lookback_days: int = 30,
) -> int:
    """Poll EDGAR for every tracked company and enqueue FULL_PIPELINE jobs for those with new filings.

    Returns:
        Number of pipeline jobs enqueued.
    """
    _init_edgar()
    tickers = get_all_company_tickers()
    logger.info("poll_cycle_start", company_count=len(tickers), forms=forms)

    jobs_enqueued = 0

    for ticker in tickers:
        try:
            new = check_company_for_new_filings(ticker, forms, lookback_days)
            if new:
                create_job(
                    job_type=JobType.FULL_PIPELINE,
                    params={
                        "ticker": ticker,
                        "forms": forms,
                        "trigger": "scheduled",
                    },
                    priority=2,
                )
                jobs_enqueued += 1
                logger.info(
                    "enqueued_pipeline_job",
                    ticker=ticker,
                    new_filings=len(new),
                )
        except Exception:
            logger.exception("poll_company_error", ticker=ticker)

    logger.info("poll_cycle_done", jobs_enqueued=jobs_enqueued)
    return jobs_enqueued


def poll_all_filings(
    forms: List[str],
    batch_size: int = 50,
) -> int:
    """Poll EDGAR's current filings feed for ALL new filings and enqueue BULK_INGEST jobs.

    Unlike poll_all_companies() which only checks tracked companies, this discovers
    filings from any company on EDGAR.

    Args:
        forms: Form types to discover.
        batch_size: Number of filings per BULK_INGEST job.

    Returns:
        Number of new filings discovered.
    """
    from symbology.ingestion.bulk_discovery import discover_current_filings

    _init_edgar()

    logger.info("bulk_poll_cycle_start", forms=forms)
    new_filings = discover_current_filings(form_types=forms)

    if not new_filings:
        logger.info("bulk_poll_cycle_done", new_filings=0, jobs_enqueued=0)
        return 0

    # Batch filings into BULK_INGEST jobs
    jobs_enqueued = 0
    for i in range(0, len(new_filings), batch_size):
        batch = new_filings[i : i + batch_size]
        create_job(
            job_type=JobType.BULK_INGEST,
            params={"filings": batch},
            priority=3,  # lower priority than tracked-company jobs (priority 2)
        )
        jobs_enqueued += 1

    logger.info(
        "bulk_poll_cycle_done",
        new_filings=len(new_filings),
        jobs_enqueued=jobs_enqueued,
    )
    return len(new_filings)
