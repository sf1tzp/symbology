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
