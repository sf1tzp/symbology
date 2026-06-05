"""Enqueue COMPANY_DIFF jobs for every company that has a CompanyPageContent.

Dry run by default; pass --execute to actually create jobs.

    uv run python scripts/enqueue_company_diffs.py            # dry run
    uv run python scripts/enqueue_company_diffs.py --execute  # enqueue
"""

import sys

from symbology.database.base import get_db_session, init_db
from symbology.database.companies import Company
from symbology.database.jobs import JobType, create_job
from symbology.database.page_content import CompanyPageContent
from symbology.utils.config import settings

LOOKBACK = 5
FORM = "10-K"


def main(execute: bool) -> None:
    init_db(settings.database.url)
    session = get_db_session()

    # Distinct companies that have at least one published CompanyPageContent.
    rows = (
        session.query(Company.ticker)
        .join(CompanyPageContent, CompanyPageContent.company_id == Company.id)
        .filter(Company.ticker.isnot(None), Company.ticker != "")
        .distinct()
        .order_by(Company.ticker.asc())
        .all()
    )
    tickers = [t for (t,) in rows]

    print(f"{len(tickers)} companies with a CompanyPageContent:")
    for t in tickers:
        print(f"  {t}")

    if not execute:
        print(f"\n[dry run] would enqueue {len(tickers)} COMPANY_DIFF jobs "
              f"(lookback={LOOKBACK}, form={FORM}). Re-run with --execute.")
        return

    for t in tickers:
        job = create_job(
            job_type=JobType.COMPANY_DIFF,
            params={"ticker": t, "lookback": LOOKBACK, "form": FORM},
            priority=2,
        )
        print(f"  enqueued {t} -> {job.id}")
    print(f"\nEnqueued {len(tickers)} COMPANY_DIFF jobs.")


if __name__ == "__main__":
    main(execute="--execute" in sys.argv)
