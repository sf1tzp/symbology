"""CLI commands for pipeline monitoring and management."""

import sys

import click
from rich.console import Console
from rich.table import Table
from symbology.database.base import get_db_session, init_db
from symbology.database.companies import get_company, get_company_by_ticker
from symbology.database.jobs import JobType, create_job
from symbology.database.pipeline_runs import (
    PipelineRunStatus,
    count_consecutive_failures,
    get_latest_run_per_company,
    list_pipeline_runs,
)
from symbology.scheduler.config import scheduler_settings
from symbology.utils.config import settings
from symbology.utils.logging import get_logger

logger = get_logger(__name__)
console = Console()


def init_session():
    """Initialize database session."""
    init_db(settings.database.url)
    return get_db_session()


@click.group()
def pipeline():
    """Pipeline monitoring and management."""
    pass


@pipeline.command("status")
def pipeline_status():
    """Show pipeline status dashboard for all companies."""
    from datetime import datetime, timedelta, timezone

    try:
        init_session()
        latest_runs = get_latest_run_per_company()

        if not latest_runs:
            console.print("[yellow]No pipeline runs found[/yellow]")
            return

        table = Table(title="Pipeline Status")
        table.add_column("Ticker", style="cyan")
        table.add_column("Name", style="white", max_width=30)
        table.add_column("Last Run Status")
        table.add_column("Failures", justify="right")
        table.add_column("Started", style="dim")

        stale_count = 0
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=7200)

        for run in latest_runs:
            company = get_company(run.company_id)
            ticker = company.ticker if company else "?"
            name = company.name if company else "Unknown"
            failures = count_consecutive_failures(run.company_id)

            status_style = {
                PipelineRunStatus.COMPLETED: "green",
                PipelineRunStatus.RUNNING: "blue",
                PipelineRunStatus.PENDING: "yellow",
                PipelineRunStatus.FAILED: "red",
                PipelineRunStatus.PARTIAL: "red",
            }.get(run.status, "white")

            if run.status == PipelineRunStatus.RUNNING and run.started_at and run.started_at < cutoff:
                stale_count += 1

            failure_str = str(failures) if failures > 0 else "-"
            started_str = str(run.started_at)[:19] if run.started_at else "-"

            table.add_row(
                ticker,
                name,
                f"[{status_style}]{run.status.value}[/{status_style}]",
                failure_str,
                started_str,
            )

        console.print(table)

        if stale_count:
            console.print(f"\n[yellow]Stale runs (RUNNING > 2h): {stale_count}[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Pipeline status failed")
        sys.exit(1)


@pipeline.command("trigger")
@click.argument("ticker")
@click.option("--forms", "-f", multiple=True, help="SEC form types (default: scheduler config)")
def trigger_pipeline(ticker: str, forms: tuple):
    """Manually trigger a pipeline run for TICKER."""
    try:
        init_session()
        company = get_company_by_ticker(ticker.upper())
        if not company:
            console.print(f"[red]Company not found: {ticker}[/red]")
            sys.exit(1)

        form_list = list(forms) if forms else scheduler_settings.enabled_forms

        job = create_job(
            job_type=JobType.FULL_PIPELINE,
            params={"ticker": company.ticker, "forms": form_list},
            priority=1,
        )

        console.print(f"[green]✓[/green] Pipeline triggered for {company.ticker}")
        console.print(f"  [blue]Job ID:[/blue]  {job.id}")
        console.print(f"  [blue]Forms:[/blue]   {', '.join(form_list)}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Pipeline trigger failed")
        sys.exit(1)


@pipeline.command("backfill")
@click.option("--start-year", default=2021, type=int, help="Start year for backfill (default: 2021)")
@click.option("--end-year", default=None, type=int, help="End year for backfill (default: current year)")
@click.option("--forms", "-f", multiple=True, help="Form types (default: 10-K, 10-K/A, 10-Q, 10-Q/A, 8-K, 8-K/A)")
@click.option("--batch-size", default=50, type=int, help="Filings per job (default: 50)")
@click.option("--dry-run", is_flag=True, help="Show counts without creating jobs")
@click.option("--include-documents/--no-documents", default=True, help="Ingest document text sections")
def backfill(start_year: int, end_year: int, forms: tuple, batch_size: int, dry_run: bool, include_documents: bool):
    """Backfill EDGAR filings for a date range (no LLM)."""
    from datetime import date

    from symbology.ingestion.bulk_discovery import BULK_FORM_TYPES, discover_filings_by_date_range
    from symbology.ingestion.edgar_db.accessors import edgar_login

    try:
        init_session()
        edgar_login(settings.edgar_api.edgar_contact)

        if end_year is None:
            end_year = date.today().year
        form_types = list(forms) if forms else BULK_FORM_TYPES

        console.print(f"Backfill: {start_year} - {end_year}")
        console.print(f"Forms: {', '.join(form_types)}")
        console.print(f"Batch size: {batch_size}")
        if dry_run:
            console.print("[yellow]DRY RUN — no jobs will be created[/yellow]")
        console.print()

        total_filings = 0
        total_jobs = 0

        # Process quarter-by-quarter to manage memory
        for year in range(start_year, end_year + 1):
            quarters = [
                (date(year, 1, 1), date(year, 3, 31)),
                (date(year, 4, 1), date(year, 6, 30)),
                (date(year, 7, 1), date(year, 9, 30)),
                (date(year, 10, 1), date(year, 12, 31)),
            ]
            for q_idx, (q_start, q_end) in enumerate(quarters, 1):
                # Skip future quarters
                if q_start > date.today():
                    break

                # Clamp end date to today
                actual_end = min(q_end, date.today())

                console.print(f"  {year} Q{q_idx} ({q_start} to {actual_end})...", end=" ")
                new_filings = discover_filings_by_date_range(q_start, actual_end, form_types)
                console.print(f"[cyan]{len(new_filings)}[/cyan] new filings")

                if new_filings and not dry_run:
                    for i in range(0, len(new_filings), batch_size):
                        batch = new_filings[i : i + batch_size]
                        create_job(
                            job_type=JobType.BULK_INGEST,
                            params={"filings": batch, "include_documents": include_documents},
                            priority=4,  # lowest — backfill shouldn't block ongoing work
                        )
                        total_jobs += 1

                total_filings += len(new_filings)

        console.print()
        console.print(f"Total new filings: [cyan]{total_filings}[/cyan]")
        if dry_run:
            estimated_jobs = (total_filings + batch_size - 1) // batch_size if total_filings else 0
            console.print(f"Would create: [cyan]{estimated_jobs}[/cyan] BULK_INGEST jobs")
        else:
            console.print(f"Created: [green]{total_jobs}[/green] BULK_INGEST jobs")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Backfill failed")
        sys.exit(1)


@pipeline.command("enrich-companies")
@click.option("--limit", default=100, type=int, help="Max companies to enrich per run")
def enrich_companies(limit: int):
    """Resolve real tickers for companies with CIK placeholder tickers."""
    from edgar import Company as EdgarCompany

    from symbology.database.companies import update_company
    from symbology.ingestion.edgar_db.accessors import edgar_login

    try:
        init_session()
        edgar_login(settings.edgar_api.edgar_contact)

        session = get_db_session()
        from symbology.database.companies import Company
        placeholder_companies = (
            session.query(Company)
            .filter(Company.ticker.like("CIK%"))
            .limit(limit)
            .all()
        )

        if not placeholder_companies:
            console.print("[green]No placeholder companies to enrich[/green]")
            return

        console.print(f"Found [cyan]{len(placeholder_companies)}[/cyan] companies with CIK placeholders")

        enriched = 0
        failed = 0

        for company in placeholder_companies:
            try:
                edgar_company = EdgarCompany(company.cik)
                ticker = edgar_company.get_ticker()
                if ticker and not ticker.startswith("CIK"):
                    update_data = {
                        "ticker": ticker,
                        "display_name": edgar_company.data.display_name if hasattr(edgar_company.data, "display_name") else None,
                        "exchanges": edgar_company.get_exchanges(),
                        "sic": edgar_company.data.sic if hasattr(edgar_company.data, "sic") else None,
                        "sic_description": edgar_company.data.sic_description if hasattr(edgar_company.data, "sic_description") else None,
                    }
                    # Remove None values to avoid overwriting existing data
                    update_data = {k: v for k, v in update_data.items() if v is not None}
                    update_company(company.id, update_data)
                    enriched += 1
                    console.print(f"  [green]{company.name}[/green]: CIK{company.cik} -> {ticker}")
                else:
                    console.print(f"  [yellow]{company.name}[/yellow]: no ticker resolved")
            except Exception as e:
                failed += 1
                console.print(f"  [red]{company.name}[/red]: {e}")

        console.print(f"\nEnriched: [green]{enriched}[/green], Failed: [red]{failed}[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Enrich companies failed")
        sys.exit(1)


@pipeline.command("runs")
@click.option("--status", "status_filter",
              type=click.Choice([s.value for s in PipelineRunStatus], case_sensitive=False),
              help="Filter by status")
@click.option("--ticker", help="Filter by company ticker")
@click.option("--limit", default=20, help="Maximum number of runs to show")
def list_runs(status_filter: str, ticker: str, limit: int):
    """List recent pipeline runs."""
    try:
        init_session()

        company_id = None
        if ticker:
            company = get_company_by_ticker(ticker.upper())
            if not company:
                console.print(f"[red]Company not found: {ticker}[/red]")
                sys.exit(1)
            company_id = company.id

        ps = PipelineRunStatus(status_filter) if status_filter else None
        runs = list_pipeline_runs(company_id=company_id, status=ps, limit=limit)

        if not runs:
            console.print("[yellow]No pipeline runs found[/yellow]")
            return

        table = Table(title="Pipeline Runs")
        table.add_column("ID", style="dim", max_width=12)
        table.add_column("Ticker", style="cyan")
        table.add_column("Status")
        table.add_column("Trigger")
        table.add_column("Jobs", justify="right")
        table.add_column("Started", style="dim")
        table.add_column("Duration", justify="right")

        for run in runs:
            company = get_company(run.company_id)
            run_ticker = company.ticker if company else "?"

            status_style = {
                PipelineRunStatus.COMPLETED: "green",
                PipelineRunStatus.RUNNING: "blue",
                PipelineRunStatus.PENDING: "yellow",
                PipelineRunStatus.FAILED: "red",
                PipelineRunStatus.PARTIAL: "red",
            }.get(run.status, "white")

            jobs_str = f"{run.jobs_completed}/{run.jobs_created}"
            started_str = str(run.started_at)[:19] if run.started_at else "-"

            duration_str = "-"
            if run.started_at and run.completed_at:
                delta = run.completed_at - run.started_at
                duration_str = f"{delta.total_seconds():.1f}s"

            table.add_row(
                str(run.id)[:12] + "…",
                run_ticker,
                f"[{status_style}]{run.status.value}[/{status_style}]",
                run.trigger.value,
                jobs_str,
                started_str,
                duration_str,
            )

        console.print(table)

        if len(runs) == limit:
            console.print(f"\n[yellow]Showing first {limit} results. Use --limit to see more.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error listing runs: {e}[/red]")
        logger.exception("Failed to list pipeline runs")
        sys.exit(1)
