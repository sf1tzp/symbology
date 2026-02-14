"""CLI commands for database dump and load operations."""

import os
import subprocess
import sys
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
    """Database dump and load commands."""
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
