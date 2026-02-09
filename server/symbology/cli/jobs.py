"""CLI commands for background job management."""

import sys

import click
from rich.console import Console
from rich.table import Table
from symbology.database.base import get_db_session, init_db
from symbology.database.jobs import (
    JobStatus,
    JobType,
    cancel_job,
    create_job,
    get_job,
    list_jobs,
)
from symbology.utils.config import settings
from symbology.utils.logging import get_logger

logger = get_logger(__name__)
console = Console()


def init_session():
    """Initialize database session."""
    init_db(settings.database.url)
    return get_db_session()


@click.group()
def jobs():
    """Background job queue management."""
    pass


@jobs.command("submit")
@click.argument("job_type", type=click.Choice([jt.value for jt in JobType], case_sensitive=False))
@click.option("--params", "-p", default="{}", help="Job parameters as JSON string")
@click.option("--priority", type=int, default=2, help="Priority (0=critical, 4=backlog)")
@click.option("--max-retries", type=int, default=3, help="Maximum retry attempts")
def submit_job(job_type: str, params: str, priority: int, max_retries: int):
    """Submit a new job to the queue.

    JOB_TYPE: One of the registered job types.
    """
    import json
    try:
        parsed_params = json.loads(params)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON params: {e}[/red]")
        sys.exit(1)

    try:
        init_session()
        jt = JobType(job_type)
        job = create_job(jt, params=parsed_params, priority=priority, max_retries=max_retries)
        console.print(f"[green]✓[/green] Job submitted: {job.id}")
        console.print(f"  [blue]Type:[/blue]     {job.job_type.value}")
        console.print(f"  [blue]Priority:[/blue] {job.priority}")
        console.print(f"  [blue]Status:[/blue]   {job.status.value}")
    except Exception as e:
        console.print(f"[red]Error submitting job: {e}[/red]")
        logger.exception("Job submission failed")
        sys.exit(1)


@jobs.command("status")
@click.argument("job_id")
def job_status(job_id: str):
    """Show the status of a specific job.

    JOB_ID: UUID of the job.
    """
    try:
        init_session()
        job = get_job(job_id)
        if not job:
            console.print(f"[red]Job not found: {job_id}[/red]")
            sys.exit(1)

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_row("[bold blue]ID:[/bold blue]", str(job.id))
        table.add_row("[bold blue]Type:[/bold blue]", job.job_type.value)
        table.add_row("[bold blue]Status:[/bold blue]", job.status.value)
        table.add_row("[bold blue]Priority:[/bold blue]", str(job.priority))
        table.add_row("[bold blue]Worker:[/bold blue]", job.worker_id or "-")
        table.add_row("[bold blue]Created:[/bold blue]", str(job.created_at))
        table.add_row("[bold blue]Retries:[/bold blue]", f"{job.retry_count}/{job.max_retries}")
        if job.error:
            table.add_row("[bold red]Error:[/bold red]", job.error)
        if job.duration is not None:
            table.add_row("[bold blue]Duration:[/bold blue]", f"{job.duration:.2f}s")
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Failed to get job status")
        sys.exit(1)


@jobs.command("list")
@click.option("--status", "status_filter", type=click.Choice([s.value for s in JobStatus], case_sensitive=False), help="Filter by status")
@click.option("--running", "shortcut_running", is_flag=True, help="Show only in-progress jobs")
@click.option("--pending", "shortcut_pending", is_flag=True, help="Show only pending jobs")
@click.option("--failed", "shortcut_failed", is_flag=True, help="Show only failed jobs")
@click.option("--completed", "shortcut_completed", is_flag=True, help="Show only completed jobs")
@click.option("--type", "type_filter", type=click.Choice([jt.value for jt in JobType], case_sensitive=False), help="Filter by job type")
@click.option("--limit", default=20, help="Maximum number of jobs to show")
def list_jobs_cmd(status_filter: str, type_filter: str, limit: int, shortcut_running: bool, shortcut_pending: bool, shortcut_failed: bool, shortcut_completed: bool):
    """List jobs in the queue."""
    try:
        # Resolve status from shortcut flags (last one wins if multiple given)
        if shortcut_running:
            status_filter = JobStatus.IN_PROGRESS.value
        elif shortcut_pending:
            status_filter = JobStatus.PENDING.value
        elif shortcut_failed:
            status_filter = JobStatus.FAILED.value
        elif shortcut_completed:
            status_filter = JobStatus.COMPLETED.value

        init_session()
        js = JobStatus(status_filter) if status_filter else None
        jt = JobType(type_filter) if type_filter else None
        job_list = list_jobs(status=js, job_type=jt, limit=limit)

        if not job_list:
            console.print("[yellow]No jobs found[/yellow]")
            return

        def fmt_ts(ts):
            return str(ts)[:19] if ts else "-"

        table = Table(title="Jobs")
        table.add_column("ID", style="dim", max_width=12)
        table.add_column("Type", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("Priority")
        table.add_column("Retries")
        table.add_column("Created")
        table.add_column("Started")
        table.add_column("Completed")

        for job in job_list:
            status_style = {
                JobStatus.PENDING: "yellow",
                JobStatus.IN_PROGRESS: "blue",
                JobStatus.COMPLETED: "green",
                JobStatus.FAILED: "red",
                JobStatus.CANCELLED: "dim",
            }.get(job.status, "white")

            table.add_row(
                str(job.id)[:12] + "…",
                job.job_type.value,
                f"[{status_style}]{job.status.value}[/{status_style}]",
                str(job.priority),
                f"{job.retry_count}/{job.max_retries}",
                fmt_ts(job.created_at),
                fmt_ts(job.started_at),
                fmt_ts(job.completed_at),
            )

        console.print(table)

        if len(job_list) == limit:
            console.print(f"\n[yellow]Showing first {limit} results. Use --limit to see more.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error listing jobs: {e}[/red]")
        logger.exception("Failed to list jobs")
        sys.exit(1)


@jobs.command("cancel")
@click.argument("job_id")
def cancel_job_cmd(job_id: str):
    """Cancel a pending job.

    JOB_ID: UUID of the job to cancel.
    """
    try:
        init_session()
        job = cancel_job(job_id)
        if not job:
            console.print(f"[red]Job not found or not in PENDING status: {job_id}[/red]")
            sys.exit(1)
        console.print(f"[green]✓[/green] Job cancelled: {job.id}")
    except Exception as e:
        console.print(f"[red]Error cancelling job: {e}[/red]")
        logger.exception("Failed to cancel job")
        sys.exit(1)
