"""CLI commands for background job management."""

import json
import sys

import click
from rich.console import Console
from rich.table import Table
from symbology.database.base import get_db_session, init_db
from symbology.database.jobs import (
    JobStatus,
    JobType,
    cancel_failed_jobs,
    cancel_job,
    count_jobs_by_status,
    create_job,
    get_job,
    list_jobs,
    requeue_failed_jobs,
    requeue_job,
    stop_job,
    update_job,
)
from symbology.utils.config import settings
from symbology.utils.logging import get_logger

logger = get_logger(__name__)
console = Console()


def init_session():
    """Initialize database session."""
    init_db(settings.database.url)
    return get_db_session()


def format_job_context(job) -> str:
    """Build a compact, human-readable context string from a job's params.

    Job types carry heterogeneous payloads, so we curate the most meaningful
    fields per type (ticker / form / year / etc.) rather than dumping raw JSON.
    Falls back to the first couple of scalar params for unknown types.
    """
    params = job.params or {}

    def pick(*keys):
        return [f"{k}={params[k]}" for k in keys if params.get(k) not in (None, "", [])]

    jt = job.job_type
    parts: list = []

    if jt == JobType.COMPANY_INGESTION:
        parts = pick("ticker")
    elif jt in (JobType.FILING_INGESTION, JobType.INGEST_PIPELINE):
        parts = pick("ticker", "form", "count")
    elif jt == JobType.FILING_PAGE_CONTENT:
        parts = pick("ticker", "form", "year")
    elif jt == JobType.COMPANY_PAGE_CONTENT:
        parts = pick("ticker", "form", "lookback")
    elif jt == JobType.FULL_PIPELINE:
        parts = pick("ticker")
        forms = params.get("forms")
        if forms:
            parts.append(f"forms={','.join(forms)}")
        if params.get("force"):
            parts.append("force")
    elif jt == JobType.CONTENT_GENERATION:
        parts = pick("company_ticker", "form_type", "document_type", "content_stage", "description")
    elif jt == JobType.COMPANY_GROUP_PIPELINE:
        tickers = params.get("tickers")
        if tickers:
            parts.append(f"tickers={','.join(tickers)}")
        parts += pick("group_slug")
    elif jt == JobType.BULK_INGEST:
        filings = params.get("filings") or []
        parts = [f"{len(filings)} filings"]
    elif jt == JobType.TEST:
        parts = pick("sleep")

    # Fallback: surface the first few scalar params for any unhandled type.
    if not parts:
        parts = [
            f"{k}={v}"
            for k, v in list(params.items())[:3]
            if isinstance(v, (str, int, float, bool))
        ]

    return ", ".join(parts) if parts else "-"


def coerce_param_value(raw: str):
    """Best-effort typing for a ``--set KEY=VALUE`` value.

    Params are an untyped JSON blob, but ``lookback=5`` should land as the int 5,
    not the string "5", so handlers see what they expect. Order matters: try
    bool/null, then int, then float, then JSON (lists/objects/quoted strings),
    and finally fall back to the raw string (e.g. ``form=10-K``).
    """
    low = raw.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "none"):
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw


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
        table.add_row("[bold blue]Context:[/bold blue]", format_job_context(job))
        table.add_row("[bold blue]Status:[/bold blue]", job.status.value)
        table.add_row("[bold blue]Priority:[/bold blue]", str(job.priority))
        table.add_row("[bold blue]Worker:[/bold blue]", job.worker_id or "-")
        table.add_row("[bold blue]Created:[/bold blue]", str(job.created_at))
        # "Attempt N/total" — matches the status page convention. retry_count is
        # the number of *completed* attempts, so the current one is +1.
        table.add_row("[bold blue]Attempt:[/bold blue]", f"{job.retry_count + 1}/{job.max_retries}")
        if job.error:
            table.add_row("[bold red]Error:[/bold red]", job.error)
        if job.duration is not None:
            table.add_row("[bold blue]Duration:[/bold blue]", f"{job.duration:.2f}s")
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Failed to get job status")
        sys.exit(1)


@jobs.command("edit")
@click.argument("job_id")
@click.option(
    "--set",
    "set_kvs",
    multiple=True,
    metavar="KEY=VALUE",
    help="Set a param (repeatable). Auto-typed: 5->int, 1.5->float, true/false->bool, JSON for lists/objects, else string.",
)
@click.option("--params", "params_json", default=None, help="Merge a JSON object into params")
@click.option("--replace-params", is_flag=True, help="Replace params wholesale instead of merging")
@click.option("--priority", type=int, default=None, help="New priority (0=critical, 4=backlog)")
@click.option("--max-retries", type=int, default=None, help="New maximum retry attempts")
def edit_job(job_id, set_kvs, params_json, replace_params, priority, max_retries):
    """Edit an editable job's params, priority, or max-retries.

    JOB_ID: UUID of the job. Only PENDING or FAILED jobs can be edited.

    \b
    Examples:
      jobs edit <id> --set lookback=10
      jobs edit <id> --set form=10-Q --set lookback=3
      jobs edit <id> --priority 0
      jobs edit <id> --params '{"lookback": 8}'
    """
    # Build the params delta from --set pairs and/or --params JSON.
    params_delta = {}
    for kv in set_kvs:
        if "=" not in kv:
            console.print(f"[red]Invalid --set '{kv}', expected KEY=VALUE[/red]")
            sys.exit(1)
        key, _, raw = kv.partition("=")
        params_delta[key.strip()] = coerce_param_value(raw)

    if params_json is not None:
        try:
            parsed = json.loads(params_json)
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid JSON params: {e}[/red]")
            sys.exit(1)
        if not isinstance(parsed, dict):
            console.print("[red]--params must be a JSON object[/red]")
            sys.exit(1)
        params_delta.update(parsed)

    if not params_delta and priority is None and max_retries is None:
        console.print("[yellow]Nothing to edit. Pass --set, --params, --priority, or --max-retries.[/yellow]")
        sys.exit(1)

    try:
        init_session()
        job = update_job(
            job_id,
            params=params_delta or None,
            priority=priority,
            max_retries=max_retries,
            replace_params=replace_params,
        )
        if not job:
            console.print(
                f"[red]Job not found or not editable (must be PENDING or FAILED): {job_id}[/red]"
            )
            sys.exit(1)
        console.print(f"[green]✓[/green] Job updated: {job.id}")
        console.print(f"  [blue]Type:[/blue]     {job.job_type.value}")
        console.print(f"  [blue]Context:[/blue]  {format_job_context(job)}")
        console.print(f"  [blue]Priority:[/blue] {job.priority}")
        console.print(f"  [blue]Status:[/blue]   {job.status.value}")
    except Exception as e:
        console.print(f"[red]Error editing job: {e}[/red]")
        logger.exception("Failed to edit job")
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
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Type", style="cyan")
        table.add_column("Context", style="magenta")
        table.add_column("Status", style="white")
        table.add_column("Priority")
        table.add_column("Attempt")
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
                str(job.id),
                job.job_type.value,
                format_job_context(job),
                f"[{status_style}]{job.status.value}[/{status_style}]",
                str(job.priority),
                f"{job.retry_count + 1}/{job.max_retries}",
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


@jobs.command("stop")
@click.argument("job_id")
def stop_job_cmd(job_id: str):
    """Stop an active job (PENDING or IN_PROGRESS) by marking it CANCELLED.

    JOB_ID: UUID of the job to stop.

    Note: this updates DB state only. A worker already executing the job keeps
    running its current task until it finishes; the CANCELLED status prevents it
    from being retried or re-picked up.
    """
    try:
        init_session()
        job = stop_job(job_id)
        if not job:
            console.print(
                f"[red]Job not found or not stoppable (already terminal): {job_id}[/red]"
            )
            sys.exit(1)
        console.print(f"[green]✓[/green] Job stopped: {job.id}")
    except Exception as e:
        console.print(f"[red]Error stopping job: {e}[/red]")
        logger.exception("Failed to stop job")
        sys.exit(1)


@jobs.command("retry")
@click.argument("job_id", required=False)
@click.option("--all", "retry_all", is_flag=True, help="Retry all FAILED jobs")
@click.option("--type", "type_filter", type=click.Choice([jt.value for jt in JobType], case_sensitive=False), help="With --all, filter by job type")
@click.option("--dry-run", is_flag=True, help="Show counts without making changes")
def retry_cmd(job_id: str, retry_all: bool, type_filter: str, dry_run: bool):
    """Reset FAILED jobs back to PENDING for retry.

    JOB_ID: UUID of the job to retry. Read from stdin if not given as an
    argument. Ignored when --all is set, which retries every failed job.
    """
    try:
        init_session()

        if retry_all:
            jt = JobType(type_filter) if type_filter else None
            count = count_jobs_by_status(JobStatus.FAILED, job_type=jt)

            if count == 0:
                console.print("[yellow]No failed jobs found[/yellow]")
                return

            if dry_run:
                console.print(f"Would requeue: [cyan]{count}[/cyan] failed jobs")
                return

            requeued = requeue_failed_jobs(job_type=jt)
            console.print(f"[green]✓[/green] Requeued {len(requeued)} failed jobs to PENDING")
            return

        # Single-job mode: read the id from the argument or stdin.
        if not job_id:
            job_id = sys.stdin.readline().strip()
        if not job_id:
            console.print("[red]No job id provided (pass an argument, pipe via stdin, or use --all)[/red]")
            sys.exit(1)

        if dry_run:
            job = get_job(job_id)
            if not job or job.status != JobStatus.FAILED:
                console.print(f"[red]Job not found or not in FAILED status: {job_id}[/red]")
                sys.exit(1)
            console.print(f"Would requeue: [cyan]{job.id}[/cyan]")
            return

        job = requeue_job(job_id)
        if not job:
            console.print(f"[red]Job not found or not in FAILED status: {job_id}[/red]")
            sys.exit(1)
        console.print(f"[green]✓[/green] Requeued job to PENDING: {job.id}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Failed to retry jobs")
        sys.exit(1)


@jobs.command("clear-failed")
@click.option("--type", "type_filter", type=click.Choice([jt.value for jt in JobType], case_sensitive=False), help="Filter by job type")
@click.option("--dry-run", is_flag=True, help="Show counts without making changes")
def clear_failed_cmd(type_filter: str, dry_run: bool):
    """Mark FAILED jobs as CANCELLED (clear them from the queue)."""
    try:
        init_session()
        jt = JobType(type_filter) if type_filter else None
        count = count_jobs_by_status(JobStatus.FAILED, job_type=jt)

        if count == 0:
            console.print("[yellow]No failed jobs found[/yellow]")
            return

        if dry_run:
            console.print(f"Would cancel: [cyan]{count}[/cyan] failed jobs")
            return

        cancelled = cancel_failed_jobs(job_type=jt)
        console.print(f"[green]✓[/green] Cancelled {cancelled} failed jobs")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Failed to clear failed jobs")
        sys.exit(1)
