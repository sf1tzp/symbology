"""CLI commands for database dump, load, sync, and backfill operations."""

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import click
from rich.console import Console

from symbology.utils.config import settings
from symbology.utils.logging import get_logger

logger = get_logger(__name__)
console = Console()


def _format_size(size_bytes: int) -> str:
    """Format byte count as human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _upload_to_s3(local_path: Path, s3_uri: str):
    """Upload a file to S3 using boto3."""
    try:
        import boto3
    except ImportError:
        console.print("[red]boto3 is not installed. Install it with: pip install boto3[/red]")
        sys.exit(1)

    parsed = urlparse(s3_uri)
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")

    if s3_uri.endswith("/"):
        key = key + local_path.name

    console.print(f"[blue]Uploading to s3://{bucket}/{key}...[/blue]")
    s3 = boto3.client("s3")
    s3.upload_file(str(local_path), bucket, key)
    console.print(f"[green]✓[/green] Uploaded to s3://{bucket}/{key}")


def _download_from_s3(s3_uri: str, dest_path: Path):
    """Download a file from S3 using boto3."""
    try:
        import boto3
    except ImportError:
        console.print("[red]boto3 is not installed. Install it with: pip install boto3[/red]")
        sys.exit(1)

    parsed = urlparse(s3_uri)
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")

    console.print(f"[blue]Downloading from s3://{bucket}/{key}...[/blue]")
    s3 = boto3.client("s3")
    s3.download_file(bucket, key, str(dest_path))
    console.print(f"[green]✓[/green] Downloaded to {dest_path}")


@click.group()
def db():
    """Database dump, load, sync, and backfill commands."""
    pass


@db.command("dump")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output filename (default: timestamped)")
@click.option("--upload-s3", "s3_uri", default=None, help="Upload dump to S3 URI (e.g. s3://bucket/backups/)")
def dump_cmd(output: str | None, s3_uri: str | None):
    """Dump the database to a file using pg_dump (custom format)."""
    db_settings = settings.database

    if output:
        out_path = Path(output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = Path(f"symbology_{timestamp}.dump")

    console.print(f"[bold blue]Dumping database: {db_settings.host}:{db_settings.port}/{db_settings.database_name}[/bold blue]")

    try:
        env = os.environ.copy()
        env["PGPASSWORD"] = db_settings.password

        cmd = [
            "pg_dump",
            "-Fc",
            "-h", db_settings.host,
            "-p", str(db_settings.port),
            "-U", db_settings.user,
            "-d", db_settings.database_name,
            "-f", str(out_path),
        ]

        subprocess.run(cmd, check=True, capture_output=True, env=env)

        size = out_path.stat().st_size
        console.print(f"[green]✓[/green] Dump created: {out_path} ({_format_size(size)})")

        if s3_uri:
            _upload_to_s3(out_path, s3_uri)

    except FileNotFoundError:
        console.print("[red]pg_dump not found. Ensure PostgreSQL client tools are on your PATH.[/red]")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]pg_dump failed: {e.stderr.decode().strip()}[/red]")
        logger.exception("pg_dump failed")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error during dump: {e}[/red]")
        logger.exception("Database dump failed")
        sys.exit(1)


@db.command("load")
@click.argument("file")
@click.option("--database-url", required=True, help="PostgreSQL connection string for the target database")
@click.option("--clean", is_flag=True, default=False, help="Drop existing objects before restore")
@click.option("--no-owner/--owner", default=True, help="Skip restoration of object ownership (default: skip)")
def load_cmd(file: str, database_url: str, clean: bool, no_owner: bool):
    """Load a database dump using pg_restore.

    FILE: Local path or s3:// URI to a .dump file.
    """
    import tempfile

    parsed = urlparse(database_url)
    target_host = parsed.hostname or "localhost"
    target_port = str(parsed.port or 5432)
    target_user = parsed.username or "postgres"
    target_password = parsed.password or ""
    target_dbname = parsed.path.lstrip("/")

    # Resolve file — download from S3 if needed
    if file.startswith("s3://"):
        tmp = tempfile.NamedTemporaryFile(suffix=".dump", delete=False)
        tmp.close()
        local_path = Path(tmp.name)
        try:
            _download_from_s3(file, local_path)
        except Exception:
            local_path.unlink(missing_ok=True)
            raise
    else:
        local_path = Path(file)
        if not local_path.exists():
            console.print(f"[red]File not found: {file}[/red]")
            sys.exit(1)

    size = local_path.stat().st_size

    # Confirmation prompt
    console.print(f"\n[bold yellow]Target:[/bold yellow] {target_host}:{target_port}/{target_dbname}")
    console.print(f"[bold yellow]File:[/bold yellow]   {local_path} ({_format_size(size)})")
    if clean:
        console.print("[bold red]Mode:   --clean (existing objects will be dropped)[/bold red]")
    if not click.confirm("\nProceed with restore?"):
        console.print("[yellow]Aborted.[/yellow]")
        sys.exit(0)

    try:
        env = os.environ.copy()
        env["PGPASSWORD"] = target_password

        cmd = [
            "pg_restore",
            "-h", target_host,
            "-p", target_port,
            "-U", target_user,
            "-d", target_dbname,
        ]

        if clean:
            cmd.append("--clean")
        if no_owner:
            cmd.append("--no-owner")

        cmd.append(str(local_path))

        subprocess.run(cmd, check=True, capture_output=True, env=env)
        console.print(f"[green]✓[/green] Database restored to {target_host}:{target_port}/{target_dbname}")

    except FileNotFoundError:
        console.print("[red]pg_restore not found. Ensure PostgreSQL client tools are on your PATH.[/red]")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]pg_restore failed: {e.stderr.decode().strip()}[/red]")
        logger.exception("pg_restore failed")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error during restore: {e}[/red]")
        logger.exception("Database restore failed")
        sys.exit(1)
    finally:
        # Clean up S3 temp file
        if file.startswith("s3://"):
            local_path.unlink(missing_ok=True)


@db.command("sync")
@click.option("--source", required=True, help="Source environment name (e.g. staging-web)")
@click.option("--target", required=True, help="Target environment name (e.g. web2.streetfortress.cloud)")
@click.option("--dry-run", is_flag=True, help="Show what would be synced without writing")
@click.option("--batch-size", default=500, type=int, help="Rows per commit batch (default: 500)")
def sync_cmd(source: str, target: str, dry_run: bool, batch_size: int):
    """Sync data from source to target database using environment names.

    Resolves connections via sops-encrypted secrets/<name>.env files.
    Deduplicates by natural keys (ticker, content_hash, accession_number, etc.).

    Examples:

      just cli db sync --source staging-web --target web2.streetfortress.cloud --dry-run

      just cli db sync --source staging-web --target local
    """
    from symbology.cli.db_sync import resolve_db_url, run_sync

    if source == target:
        console.print("[red]Source and target environments must be different.[/red]")
        sys.exit(1)

    console.print(f"[bold blue]Source:[/bold blue] {source}")
    console.print(f"[bold blue]Target:[/bold blue] {target}")

    source_url = resolve_db_url(source)
    target_url = resolve_db_url(target)

    run_sync(source_url, target_url, dry_run=dry_run, batch_size=batch_size)


# ---------------------------------------------------------------------------
# Backfill subgroup
# ---------------------------------------------------------------------------

@db.group("backfill")
def backfill():
    """Backfill null columns on existing data."""
    pass


@backfill.command("content-stage")
@click.option("--target", required=True, help="Target environment name (e.g. web2.streetfortress.cloud)")
@click.option("--dry-run", is_flag=True, help="Show what would be updated without making changes")
@click.option("--limit", default=1000, type=int, help="Max rows to process (default: 1000)")
def backfill_content_stage(target: str, dry_run: bool, limit: int):
    """Backfill content_stage from the description field on generated_content rows.

    Parses description strings (e.g. 'risk_factors_aggregate_summary') to
    populate the structured content_stage, document_type, and form_type fields.

    Examples:

      just cli db backfill content-stage --target staging-web --dry-run

      just cli db backfill content-stage --target web2.streetfortress.cloud --limit 500
    """
    from symbology.cli.db_sync import create_session, resolve_db_url
    from symbology.database.documents import DocumentType
    from symbology.database.generated_content import ContentStage, GeneratedContent

    STAGE_SUFFIXES = {
        "_single_summary": ContentStage.SINGLE_SUMMARY,
        "_aggregate_summary": ContentStage.AGGREGATE_SUMMARY,
        "_frontpage_summary": ContentStage.FRONTPAGE_SUMMARY,
    }
    EXACT_MATCHES = {
        "company_group_analysis": ContentStage.COMPANY_GROUP_ANALYSIS,
        "company_group_frontpage": ContentStage.COMPANY_GROUP_FRONTPAGE,
        "business_description_frontpage_summary": ContentStage.FRONTPAGE_SUMMARY,
    }
    DOC_TYPE_MAP = {dt.value: dt for dt in DocumentType}

    try:
        console.print(f"[bold blue]Target:[/bold blue] {target}")
        target_url = resolve_db_url(target)
        session = create_session(target_url)

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

            # Check exact matches first
            detected_stage = EXACT_MATCHES.get(desc)
            doc_type_prefix = None if detected_stage else desc

            # Check suffix matches
            if not detected_stage:
                for suffix, stage in STAGE_SUFFIXES.items():
                    if desc.endswith(suffix):
                        detected_stage = stage
                        doc_type_prefix = desc[: -len(suffix)]
                        break

            if not detected_stage:
                skipped += 1
                continue

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
        logger.exception("Backfill content-stage failed")
        sys.exit(1)


@backfill.command("cik")
@click.option("--target", required=True, help="Target environment name (e.g. web2.streetfortress.cloud)")
@click.option("--dry-run", is_flag=True, help="Show what would be updated without making changes")
@click.option("--limit", default=100, type=int, help="Max companies to process (default: 100)")
def backfill_cik(target: str, dry_run: bool, limit: int):
    """Backfill CIK numbers for companies using the SEC EDGAR API.

    Looks up each company's CIK by ticker symbol.

    Examples:

      just cli db backfill cik --target staging-web --dry-run

      just cli db backfill cik --target web2.streetfortress.cloud --limit 50
    """
    from symbology.cli.db_sync import create_session, resolve_db_url
    from symbology.database.companies import Company
    from symbology.ingestion.edgar_db.accessors import edgar_login

    try:
        console.print(f"[bold blue]Target:[/bold blue] {target}")
        target_url = resolve_db_url(target)
        session = create_session(target_url)
        edgar_login(settings.edgar_api.edgar_contact)

        from edgar import Company as EdgarCompany

        rows = (
            session.query(Company)
            .filter(Company.cik.is_(None))
            .limit(limit)
            .all()
        )

        if not rows:
            console.print("[green]All companies already have CIK values[/green]")
            return

        console.print(f"Found [cyan]{len(rows)}[/cyan] companies without CIK")
        if dry_run:
            console.print("[yellow]DRY RUN — no changes will be made[/yellow]")

        updated = 0
        skipped = 0

        for row in rows:
            try:
                edgar_company = EdgarCompany(row.ticker)
                cik = str(edgar_company.cik).zfill(10)

                # Check for duplicate CIK
                existing = session.query(Company).filter(Company.cik == cik, Company.id != row.id).first()
                if existing:
                    console.print(f"  [yellow]{row.ticker}: CIK {cik} already belongs to {existing.ticker}, skipping[/yellow]")
                    skipped += 1
                    continue

                if dry_run:
                    console.print(f"  {row.ticker} -> CIK {cik}")
                else:
                    row.cik = cik

                updated += 1
            except Exception as e:
                console.print(f"  [yellow]{row.ticker}: not found in EDGAR ({e})[/yellow]")
                skipped += 1

            time.sleep(0.15)  # Rate limit

        if not dry_run:
            session.commit()

        console.print(f"\n{'Would update' if dry_run else 'Updated'}: [green]{updated}[/green]")
        if skipped:
            console.print(f"Skipped: [yellow]{skipped}[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Backfill CIK failed")
        sys.exit(1)
