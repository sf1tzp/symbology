"""CLI commands for background job management."""

import json
import sys
from datetime import datetime, timedelta, timezone

import click
from rich.console import Console
from rich.table import Table
from symbology.database.base import get_db_session, init_db
from symbology.database.jobs import (
    JobStatus,
    JobType,
    cancel_job,
    cancel_jobs_by_status,
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
    elif jt == JobType.FILING_INGESTION:
        parts = pick("ticker", "form", "count")
    elif jt == JobType.FILING_PAGE_CONTENT:
        parts = pick("ticker", "form", "year")
    elif jt == JobType.COMPANY_PAGE_CONTENT:
        parts = pick("ticker", "form", "lookback")
    elif jt == JobType.EMBED_FILING:
        parts = pick("filing_id", "accession_number")
    elif jt == JobType.FILING_DIFF:
        left = params.get("from") or params.get("left_filing_id")
        right = params.get("to") or params.get("right_filing_id")
        if left and right:
            parts.append(f"{left} -> {right}")
        parts += pick("form")
    elif jt == JobType.COMPANY_DIFF:
        parts = pick("ticker", "form")
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


@jobs.command("start")
@click.argument("job_type", type=click.Choice([jt.value for jt in JobType], case_sensitive=False))
@click.option(
    "--set",
    "set_kvs",
    multiple=True,
    metavar="KEY=VALUE",
    help="Set a param (repeatable). Auto-typed: 5->int, 1.5->float, true/false->bool, JSON for lists/objects, else string.",
)
@click.option("--params", "-p", "params_json", default=None, help="Job parameters as a JSON object (merged after --set pairs)")
@click.option("--priority", type=int, default=2, help="Priority (0=critical, 4=backlog)")
@click.option("--max-retries", type=int, default=3, help="Maximum retry attempts")
@click.option(
    "--delay",
    "delay_seconds",
    type=float,
    default=None,
    help="Defer the job by N seconds (sets scheduled_at = now + N, naive UTC).",
)
@click.option(
    "--scheduled-at",
    "scheduled_at_iso",
    default=None,
    help="Defer until an ISO-8601 timestamp (UTC). Mutually exclusive with --delay.",
)
def start_job(job_type: str, set_kvs, params_json, priority: int, max_retries: int,
              delay_seconds, scheduled_at_iso):
    """Enqueue a new job of JOB_TYPE.

    Params are assembled from repeatable --set KEY=VALUE pairs (auto-typed, same
    rules as `jobs edit`) and/or a --params JSON object. Both may be combined;
    --params is merged last so it wins on key conflicts.

    \b
    Examples:
      jobs start filing_page_content --set ticker=AAPL --set year=2023
      jobs start company_page_content --set ticker=MSFT --set lookback=5 --set form=10-Q
      jobs start bulk_ingest --params '{"filings": []}'
    """
    params = {}
    for kv in set_kvs:
        if "=" not in kv:
            console.print(f"[red]Invalid --set '{kv}', expected KEY=VALUE[/red]")
            sys.exit(1)
        key, _, raw = kv.partition("=")
        params[key.strip()] = coerce_param_value(raw)

    if params_json is not None:
        try:
            parsed = json.loads(params_json)
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid JSON params: {e}[/red]")
            sys.exit(1)
        if not isinstance(parsed, dict):
            console.print("[red]--params must be a JSON object[/red]")
            sys.exit(1)
        params.update(parsed)

    if delay_seconds is not None and scheduled_at_iso is not None:
        console.print("[red]Pass only one of --delay / --scheduled-at[/red]")
        sys.exit(1)

    scheduled_at = None
    if delay_seconds is not None:
        scheduled_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            seconds=delay_seconds
        )
    elif scheduled_at_iso is not None:
        try:
            dt = datetime.fromisoformat(scheduled_at_iso)
        except ValueError as e:
            console.print(f"[red]Invalid --scheduled-at: {e}[/red]")
            sys.exit(1)
        # Normalize to naive UTC to match the scheduled_at storage convention.
        scheduled_at = dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt

    try:
        init_session()
        jt = JobType(job_type)
        job = create_job(
            jt,
            params=params,
            priority=priority,
            max_retries=max_retries,
            scheduled_at=scheduled_at,
        )
        console.print(f"[green]✓[/green] Job started: {job.id}")
        console.print(f"  [blue]Type:[/blue]     {job.job_type.value}")
        console.print(f"  [blue]Context:[/blue]  {format_job_context(job)}")
        console.print(f"  [blue]Priority:[/blue] {job.priority}")
        console.print(f"  [blue]Status:[/blue]   {job.status.value}")
        if scheduled_at is not None:
            console.print(f"  [blue]Scheduled:[/blue] {scheduled_at.isoformat()}")
    except Exception as e:
        console.print(f"[red]Error starting job: {e}[/red]")
        logger.exception("Job start failed")
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
        if job.scheduled_at is not None:
            table.add_row("[bold blue]Scheduled:[/bold blue]", str(job.scheduled_at))
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
@click.option("--backoff", "shortcut_backoff", is_flag=True, help="Show only backoff jobs")
@click.option("--failed", "shortcut_failed", is_flag=True, help="Show only failed jobs")
@click.option("--completed", "shortcut_completed", is_flag=True, help="Show only completed jobs")
@click.option("--cancelled", "--canceled", "shortcut_cancelled", is_flag=True, help="Show only cancelled jobs")
@click.option("--type", "type_filter", type=click.Choice([jt.value for jt in JobType], case_sensitive=False), help="Filter by job type")
@click.option("--ticker", "ticker_filter", default=None, help="Filter by company ticker referenced in job params")
@click.option("--limit", default=20, help="Maximum number of jobs to show")
def list_jobs_cmd(status_filter: str, type_filter: str, ticker_filter: str, limit: int, shortcut_running: bool, shortcut_pending: bool, shortcut_backoff: bool, shortcut_failed: bool, shortcut_completed: bool, shortcut_cancelled: bool):
    """List jobs in the queue."""
    try:
        # Collect statuses from --status plus any shortcut flags; jobs matching
        # any of them are shown (e.g. --running --pending).
        statuses: list[JobStatus] = []
        if status_filter:
            statuses.append(JobStatus(status_filter))
        if shortcut_running:
            statuses.append(JobStatus.IN_PROGRESS)
        if shortcut_pending:
            statuses.append(JobStatus.PENDING)
        if shortcut_backoff:
            statuses.append(JobStatus.BACKOFF)
        if shortcut_failed:
            statuses.append(JobStatus.FAILED)
        if shortcut_completed:
            statuses.append(JobStatus.COMPLETED)
        if shortcut_cancelled:
            statuses.append(JobStatus.CANCELLED)
        # De-dupe while preserving order.
        statuses = list(dict.fromkeys(statuses))

        init_session()
        jt = JobType(type_filter) if type_filter else None
        job_list = list_jobs(status=statuses or None, job_type=jt, ticker=ticker_filter, limit=limit)

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
        table.add_column("Worker", style="dim")
        table.add_column("Created")
        table.add_column("Scheduled")
        table.add_column("Started")
        table.add_column("Completed")

        for job in job_list:
            status_style = {
                JobStatus.PENDING: "yellow",
                JobStatus.IN_PROGRESS: "blue",
                JobStatus.BACKOFF: "cyan",
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
                job.worker_id or "-",
                fmt_ts(job.created_at),
                fmt_ts(job.scheduled_at),
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
    """Requeue FAILED, CANCELLED, or BACKOFF jobs for retry.

    A FAILED or CANCELLED job is reset to PENDING with its retry budget cleared.
    A BACKOFF job (deferred while waiting on a dependency) is requeued
    immediately by pulling its scheduled_at forward to now.

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

        requeuable = (JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.BACKOFF)
        if dry_run:
            job = get_job(job_id)
            if not job or job.status not in requeuable:
                console.print(f"[red]Job not found or not in FAILED/CANCELLED/BACKOFF status: {job_id}[/red]")
                sys.exit(1)
            console.print(f"Would requeue: [cyan]{job.id}[/cyan]")
            return

        job = requeue_job(job_id)
        if not job:
            console.print(f"[red]Job not found or not in FAILED/CANCELLED/BACKOFF status: {job_id}[/red]")
            sys.exit(1)
        # A BACKOFF job stays BACKOFF (now immediately eligible); a FAILED or
        # CANCELLED job is reset to PENDING.
        console.print(f"[green]✓[/green] Requeued job ({job.status.value}): {job.id}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Failed to retry jobs")
        sys.exit(1)


# Statuses that can be cleared (cancelled) from the queue. COMPLETED/CANCELLED
# are terminal and excluded.
_CLEARABLE_STATUSES = [
    JobStatus.PENDING,
    JobStatus.IN_PROGRESS,
    JobStatus.BACKOFF,
    JobStatus.FAILED,
]


@jobs.command("clear")
@click.option("--pending", is_flag=True, help="Clear PENDING jobs")
@click.option("--in-progress", "in_progress", is_flag=True, help="Clear IN_PROGRESS jobs")
@click.option("--backoff", is_flag=True, help="Clear BACKOFF jobs")
@click.option("--failed", is_flag=True, help="Clear FAILED jobs")
@click.option("--type", "type_filter", type=click.Choice([jt.value for jt in JobType], case_sensitive=False), help="Filter by job type")
@click.option("--dry-run", is_flag=True, help="Show counts without making changes")
def clear_cmd(pending: bool, in_progress: bool, backoff: bool, failed: bool, type_filter: str, dry_run: bool):
    """Mark jobs in the selected status(es) as CANCELLED (clear them from the queue).

    Defaults to FAILED when no status flag is given. Combine flags to clear
    multiple statuses, e.g. `jobs clear --pending --backoff`.
    """
    try:
        init_session()
        jt = JobType(type_filter) if type_filter else None

        selected = [
            status
            for flag, status in (
                (pending, JobStatus.PENDING),
                (in_progress, JobStatus.IN_PROGRESS),
                (backoff, JobStatus.BACKOFF),
                (failed, JobStatus.FAILED),
            )
            if flag
        ]
        # Preserve the old `clear-failed` behaviour when no status is specified.
        if not selected:
            selected = [JobStatus.FAILED]

        counts = {s: count_jobs_by_status(s, job_type=jt) for s in selected}
        total = sum(counts.values())

        label = ", ".join(s.value for s in selected)
        if total == 0:
            console.print(f"[yellow]No jobs found in status: {label}[/yellow]")
            return

        breakdown = ", ".join(f"{counts[s]} {s.value}" for s in selected if counts[s])
        if dry_run:
            console.print(f"Would cancel: [cyan]{total}[/cyan] jobs ({breakdown})")
            return

        cancelled = cancel_jobs_by_status(selected, job_type=jt)
        console.print(f"[green]✓[/green] Cancelled {cancelled} jobs ({breakdown})")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Failed to clear jobs")
        sys.exit(1)
