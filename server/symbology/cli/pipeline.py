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
@click.option("--forms", "-f", multiple=True, help="Form types (default: 10-K, 10-K/A, 10-Q, 10-Q/A)")
@click.option("--batch-size", default=50, type=int, help="Filings per job (default: 50)")
@click.option("--dry-run", is_flag=True, help="Show counts without creating jobs")
@click.option("--include-documents/--no-documents", default=True, help="Ingest document text sections")
@click.option("--sp500", is_flag=True, help="Limit to S&P 500 companies")
@click.option("--ciks-file", type=click.Path(exists=True), help="CSV file with Cik column to filter by")
@click.option("--group", "group_slug", default=None, help="Company group slug to filter by")
def backfill(start_year: int, end_year: int, forms: tuple, batch_size: int, dry_run: bool, include_documents: bool, sp500: bool, ciks_file: str, group_slug: str):
    """Backfill EDGAR filings for a date range (no LLM)."""
    from datetime import date

    from symbology.ingestion.bulk_discovery import BULK_FORM_TYPES, discover_filings_by_date_range, get_sp500_ciks, load_ciks_from_csv
    from symbology.ingestion.edgar_db.accessors import edgar_login

    try:
        init_session()
        edgar_login(settings.edgar_api.edgar_contact)

        # Resolve CIK filter (mutually exclusive)
        filter_flags = sum([sp500, bool(ciks_file), bool(group_slug)])
        if filter_flags > 1:
            console.print("[red]Error: --sp500, --ciks-file, and --group are mutually exclusive[/red]")
            sys.exit(1)

        allowed_ciks = None
        if sp500:
            allowed_ciks = get_sp500_ciks()
            console.print(f"Filter: [green]S&P 500[/green] ({len(allowed_ciks)} CIKs)")
        elif ciks_file:
            allowed_ciks = load_ciks_from_csv(ciks_file)
            console.print(f"Filter: [green]{ciks_file}[/green] ({len(allowed_ciks)} CIKs)")
        elif group_slug:
            from symbology.database.company_groups import get_company_group_by_slug
            grp = get_company_group_by_slug(group_slug)
            if not grp:
                console.print(f"[red]Group not found: {group_slug}[/red]")
                sys.exit(1)
            allowed_ciks = {c.cik for c in grp.companies if c.cik}
            console.print(f"Filter: [green]{grp.name}[/green] ({len(allowed_ciks)} CIKs)")

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
                new_filings = discover_filings_by_date_range(q_start, actual_end, form_types, allowed_ciks=allowed_ciks)
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

@pipeline.command("trigger-group")
@click.argument("tickers", nargs=-1, required=False)
@click.option("--group", "group_slug", default=None, help="Company group slug")
def trigger_company_group_pipeline(tickers: tuple, group_slug: str):
    """Trigger sector analysis. Pass tickers directly or use --group."""
    try:
        init_session()

        ticker_list = list(tickers)

        # If group slug is provided, resolve tickers from the group
        if group_slug:
            from symbology.database.company_groups import get_company_group_by_slug
            grp = get_company_group_by_slug(group_slug)
            if not grp:
                console.print(f"[red]Group not found: {group_slug}[/red]")
                sys.exit(1)
            if not ticker_list:
                ticker_list = [c.ticker for c in grp.companies]
            if not ticker_list:
                console.print(f"[red]No companies in group '{group_slug}'[/red]")
                sys.exit(1)

        if not ticker_list:
            console.print("[red]Provide tickers as arguments or use --group[/red]")
            sys.exit(1)

        params = {"tickers": [t.upper() for t in ticker_list]}
        if group_slug:
            params["group_slug"] = group_slug

        job = create_job(
            job_type=JobType.COMPANY_GROUP_PIPELINE,
            params=params,
            priority=1,
        )

        console.print("[green]✓[/green] Company group pipeline triggered")
        console.print(f"  [blue]Job ID:[/blue]   {job.id}")
        console.print(f"  [blue]Tickers:[/blue]  {', '.join(params['tickers'])}")
        if group_slug:
            console.print(f"  [blue]Group:[/blue]    {group_slug}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Company group pipeline trigger failed")
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


@pipeline.command("regenerate")
@click.argument("ticker")
@click.option("--form", "-f", default="10-K", help="SEC form type (default: 10-K)")
@click.option("--doc-type", "-d", required=True, help="Document type (e.g. risk_factors, business_description)")
@click.option("--stage", "-s", default="all",
              type=click.Choice(["single", "aggregate", "frontpage", "all"], case_sensitive=False),
              help="Pipeline stage to regenerate (default: all)")
@click.option("--force/--no-force", default=True, help="Bypass dedup checks (default: True)")
def regenerate(ticker: str, form: str, doc_type: str, stage: str, force: bool):
    """Regenerate content for a specific ticker/form/doc-type.

    Calls composable pipeline functions directly (not via job queue)
    for immediate execution.

    Examples:

      just cli pipeline regenerate AAPL --doc-type risk_factors --stage aggregate

      just cli pipeline regenerate MSFT -f 10-Q -d management_discussion --stage all
    """
    from symbology.database.filings import Filing
    from symbology.worker.pipeline import (
        PIPELINE_MODEL_CONFIGS,
        PIPELINE_PROMPTS,
        ensure_model_config,
        ensure_prompt,
        generate_aggregate_summary,
        generate_frontpage_summary,
        generate_single_summaries,
    )

    try:
        session = init_session()
        company = get_company_by_ticker(ticker.upper())
        if not company:
            console.print(f"[red]Company not found: {ticker}[/red]")
            sys.exit(1)

        company_id = str(company.id)

        console.print(f"Regenerate: [cyan]{ticker.upper()}[/cyan] / {form} / {doc_type} / stage={stage}")
        console.print(f"Force: {'yes' if force else 'no'}")

        # Set up model configs and prompts
        mc_single = ensure_model_config(**PIPELINE_MODEL_CONFIGS["single_summary"])
        mc_aggregate = ensure_model_config(**PIPELINE_MODEL_CONFIGS["aggregate_summary"])
        mc_frontpage = ensure_model_config(**PIPELINE_MODEL_CONFIGS["frontpage_summary"])
        single_prompt = ensure_prompt(doc_type)
        aggregate_prompt = ensure_prompt(PIPELINE_PROMPTS["aggregate_summary"])
        frontpage_prompt = ensure_prompt(PIPELINE_PROMPTS["frontpage_summary"])

        total_generated = 0

        if stage in ("single", "all"):
            # Get filings
            filings = (
                session.query(Filing)
                .filter(Filing.company_id == company.id, Filing.form == form)
                .all()
            )
            if not filings:
                console.print(f"[yellow]No {form} filings found for {ticker.upper()}[/yellow]")
                sys.exit(0)

            console.print(f"Found [cyan]{len(filings)}[/cyan] {form} filings")

            hashes, new, reused, failed = generate_single_summaries(
                company_id, ticker.upper(), form, doc_type,
                filings, single_prompt, mc_single, force=force,
            )
            console.print(f"  Singles: [green]{new} new[/green], {reused} reused, [red]{failed} failed[/red]")
            total_generated += new

            if stage == "all" and hashes:
                # Continue to aggregate
                agg_hash, agg_ok = generate_aggregate_summary(
                    company_id, ticker.upper(), form, doc_type,
                    hashes, aggregate_prompt, mc_aggregate, force=force,
                )
                if agg_ok:
                    console.print("  Aggregate: [green]generated[/green]")
                    total_generated += 1

                    fp_hash, fp_ok = generate_frontpage_summary(
                        company_id, ticker.upper(), form, doc_type,
                        agg_hash, frontpage_prompt, mc_frontpage, force=force,
                    )
                    if fp_ok:
                        console.print("  Frontpage: [green]generated[/green]")
                        total_generated += 1
                    else:
                        console.print("  Frontpage: [red]failed[/red]")
                else:
                    console.print("  Aggregate: [red]failed[/red]")

        elif stage == "aggregate":
            # Find existing single summary hashes for this form/doc_type
            from symbology.database.generated_content import ContentStage, GeneratedContent
            from sqlalchemy import or_

            single_hashes = (
                session.query(GeneratedContent.content_hash)
                .filter(
                    GeneratedContent.company_id == company.id,
                    or_(
                        (GeneratedContent.content_stage == ContentStage.SINGLE_SUMMARY) &
                        (GeneratedContent.form_type == form) &
                        (GeneratedContent.description.contains(doc_type)),
                        GeneratedContent.description == f"{doc_type}_single_summary",
                    ),
                )
                .all()
            )
            hashes = [h for (h,) in single_hashes if h]

            if not hashes:
                console.print(f"[yellow]No single summaries found for {doc_type}/{form}[/yellow]")
                sys.exit(0)

            console.print(f"Found [cyan]{len(hashes)}[/cyan] single summaries")

            agg_hash, agg_ok = generate_aggregate_summary(
                company_id, ticker.upper(), form, doc_type,
                hashes, aggregate_prompt, mc_aggregate, force=force,
            )
            if agg_ok:
                console.print("  Aggregate: [green]generated[/green]")
                total_generated += 1

                fp_hash, fp_ok = generate_frontpage_summary(
                    company_id, ticker.upper(), form, doc_type,
                    agg_hash, frontpage_prompt, mc_frontpage, force=force,
                )
                if fp_ok:
                    console.print("  Frontpage: [green]generated[/green]")
                    total_generated += 1
                else:
                    console.print("  Frontpage: [red]failed[/red]")
            else:
                console.print("  Aggregate: [red]failed[/red]")

        elif stage == "frontpage":
            # Find latest aggregate hash
            from symbology.database.generated_content import ContentStage, GeneratedContent
            from sqlalchemy import or_

            agg = (
                session.query(GeneratedContent)
                .filter(
                    GeneratedContent.company_id == company.id,
                    or_(
                        (GeneratedContent.content_stage == ContentStage.AGGREGATE_SUMMARY) &
                        (GeneratedContent.form_type == form) &
                        (GeneratedContent.description.contains(doc_type)),
                        GeneratedContent.description == f"{doc_type}_aggregate_summary",
                    ),
                )
                .order_by(GeneratedContent.created_at.desc())
                .first()
            )
            if not agg or not agg.content_hash:
                console.print(f"[yellow]No aggregate summary found for {doc_type}/{form}[/yellow]")
                sys.exit(0)

            fp_hash, fp_ok = generate_frontpage_summary(
                company_id, ticker.upper(), form, doc_type,
                agg.content_hash, frontpage_prompt, mc_frontpage, force=force,
            )
            if fp_ok:
                console.print("  Frontpage: [green]generated[/green]")
                total_generated += 1
            else:
                console.print("  Frontpage: [red]failed[/red]")

        console.print(f"\nTotal generated: [green]{total_generated}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Pipeline regenerate failed")
        sys.exit(1)


@pipeline.command("backfill-metadata")
@click.option("--dry-run", is_flag=True, help="Show what would be updated without making changes")
@click.option("--limit", default=1000, type=int, help="Max rows to process (default: 1000)")
def backfill_metadata(dry_run: bool, limit: int):
    """Backfill content_stage, document_type, and form_type on existing rows.

    Parses the description string (e.g. 'risk_factors_aggregate_summary')
    to populate structured metadata fields. Infers form_type from source
    document chain where possible.

    Examples:

      just cli pipeline backfill-metadata --dry-run

      just cli pipeline backfill-metadata --limit 500
    """
    from symbology.database.documents import DocumentType
    from symbology.database.generated_content import ContentStage, GeneratedContent

    STAGE_SUFFIXES = {
        "_single_summary": ContentStage.SINGLE_SUMMARY,
        "_aggregate_summary": ContentStage.AGGREGATE_SUMMARY,
        "_frontpage_summary": ContentStage.FRONTPAGE_SUMMARY,
    }

    DOC_TYPE_MAP = {dt.value: dt for dt in DocumentType}

    try:
        session = init_session()

        # Find rows with description but no content_stage
        rows = (
            session.query(GeneratedContent)
            .filter(
                GeneratedContent.description.is_not(None),
                GeneratedContent.content_stage.is_(None),
            )
            .limit(limit)
            .all()
        )

        if not rows:
            console.print("[green]No rows need backfilling[/green]")
            return

        console.print(f"Found [cyan]{len(rows)}[/cyan] rows to backfill")
        if dry_run:
            console.print("[yellow]DRY RUN — no changes will be made[/yellow]")

        updated = 0
        skipped = 0

        for row in rows:
            desc = row.description or ""

            # Detect stage from description suffix
            detected_stage = None
            doc_type_prefix = desc
            for suffix, stage in STAGE_SUFFIXES.items():
                if desc.endswith(suffix):
                    detected_stage = stage
                    doc_type_prefix = desc[: -len(suffix)]
                    break

            if desc == "company_group_analysis":
                detected_stage = ContentStage.COMPANY_GROUP_ANALYSIS
                doc_type_prefix = None

            if not detected_stage:
                skipped += 1
                continue

            # Detect document_type from prefix
            detected_doc_type = DOC_TYPE_MAP.get(doc_type_prefix) if doc_type_prefix else None

            # Infer form_type from source documents
            detected_form_type = None
            if row.source_documents:
                for src_doc in row.source_documents:
                    if src_doc.filing and src_doc.filing.form:
                        detected_form_type = src_doc.filing.form
                        break

            if dry_run:
                console.print(
                    f"  {row.content_hash[:12] if row.content_hash else '?'}: "
                    f"[dim]{desc}[/dim] -> "
                    f"stage={detected_stage.value}, "
                    f"doc_type={detected_doc_type.value if detected_doc_type else 'None'}, "
                    f"form_type={detected_form_type or 'None'}"
                )
            else:
                row.content_stage = detected_stage
                if detected_doc_type and not row.document_type:
                    row.document_type = detected_doc_type
                if detected_form_type and not row.form_type:
                    row.form_type = detected_form_type

            updated += 1

        if not dry_run:
            session.commit()

        console.print(f"\n{'Would update' if dry_run else 'Updated'}: [green]{updated}[/green]")
        if skipped:
            console.print(f"Skipped (unrecognized description): [yellow]{skipped}[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Backfill metadata failed")
        sys.exit(1)
