"""CLI commands for filing management."""

import json
import logging
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from collector.database.base import get_db_session
from collector.database.companies import get_company_by_ticker
from collector.database.filings import get_filing_by_accession_number, get_filings_by_company
from collector.ingestion.edgar_db.accessors import edgar_login
import collector.ingestion.ingestion_helpers as ih
from collector.utils.config import settings
from collector.utils.logging import get_logger

logger = get_logger(__name__)
console = Console()


def init_session():
    """Initialize database session."""
    from collector.database.base import init_db
    from collector.utils.config import settings
    init_db(settings.database.url)
    return get_db_session()


@click.group()
def filings():
    """Filing management commands."""
    pass


@filings.command('ingest')
@click.argument('ticker')
@click.argument('form', default='10-K')
@click.argument('count', default='1')
@click.option('--force', is_flag=True, help='Force re-ingestion even if data exists')
@click.option('--include-documents', is_flag=True, default=True, help='Also ingest filing documents')
def ingest_filings(ticker: str, form: str, count: int, force: bool, include_documents: bool):
    """
    Ingest SEC filings for a company.

    TICKER: Company ticker symbol (e.g., AAPL)
    FORM_TYPE: SEC form type (10-K, 10-Q, 8-K)
    YEARS: Comma-separated years (e.g., 2022,2023) or single year
    """
    ticker = ticker.upper()
    count = int(count)

    console.print(f"[bold blue]Ingesting {count} of the latest {form} filings for {ticker}[/bold blue]")

    try:
        init_session()
        edgar_login(settings.edgar_api.edgar_contact)

        # Get company
        db_company = get_company_by_ticker(ticker)
        if not db_company:
            console.print(f"[red]Error: Company {ticker} not found. Ingest company first.[/red]")
            sys.exit(1)

        console.print(f"[green]Found company: {db_company.name}[/green]")

        filing_info = ih.ingest_filings(
            db_company.id,
            ticker=ticker,
            form=form,
            count=count,
            include_documents=include_documents
        )

        # Display results
        if include_documents:
            console.print(f"[green]Successfully ingested {len(filing_info)} {form} filings with documents[/green]")
        else:
            console.print(f"[green]Successfully ingested {len(filing_info)} {form} filings (documents skipped)[/green]")

        for f in filing_info:
            console.print(f"  {f[0]} {f[1]} {f[2]} {f[3]}")

    except Exception as e:
        console.print(f"[red]Error during filing ingestion: {e}[/red]")
        logger.exception("Filing ingestion failed")
        sys.exit(1)


@filings.command('list')
@click.argument('ticker')
@click.option('--form', help='Filter by form type (10-K, 10-Q, 8-K)')
@click.option('-o', '--output', type=click.Choice(['table', 'json']), default='table', help='Output format')
def list_filings(ticker: str, form: str, output: str):
    """List filings for a company."""

    ticker = ticker.upper()

    # For JSON output, temporarily suppress INFO level logs to avoid interference with JSON parsing
    if output == 'json':
        # Get all loggers and set their level to WARNING temporarily
        original_levels = {}
        for logger_name in ['src.database.companies', 'src.database.filings']:
            db_logger = logging.getLogger(logger_name)
            original_levels[logger_name] = db_logger.level
            db_logger.setLevel(logging.WARNING)

    try:
        init_session()

        # Get company
        company_obj = get_company_by_ticker(ticker)
        if not company_obj:
            if output == 'json':
                error_data = {"error": f"Company {ticker} not found"}
                click.echo(json.dumps(error_data))
            else:
                console.print(f"[red]Error: Company {ticker} not found[/red]")
            sys.exit(1)

        # Get filings
        filings_list = get_filings_by_company(
            company_obj.id,
        )

        if not filings_list:
            if output == 'json':
                click.echo(json.dumps([]))
            else:
                console.print(f"[yellow]No filings found for {ticker}[/yellow]")
            return

        # Filter by form type if specified
        filtered_filings = []
        for filing in filings_list:
            if form is None or filing.form == form:
                filtered_filings.append(filing)

        if output == 'json':
            # Prepare data for JSON output
            filings_data = []
            for filing in filtered_filings:
                doc_count = len(filing.documents) if hasattr(filing, 'documents') else 0
                filing_data = {
                    "form": filing.form,
                    "filing_date": filing.filing_date.strftime("%Y-%m-%d") if filing.filing_date else None,
                    "period_of_report": filing.period_of_report.strftime("%Y-%m-%d") if filing.period_of_report else None,
                    "accession_number": filing.accession_number,
                    "document_count": doc_count
                }
                filings_data.append(filing_data)

            click.echo(json.dumps(filings_data, indent=2))
        else:
            # Original table output
            table = Table(title=f"Filings for {company_obj.name} ({ticker})")
            table.add_column("Form Type", style="cyan")
            table.add_column("Filing Date", style="white")
            table.add_column("Period End", style="yellow")
            table.add_column("Accession Number", style="green")
            table.add_column("Documents", style="magenta")

            for filing in filtered_filings:
                # Count documents for this filing
                doc_count = len(filing.documents) if hasattr(filing, 'documents') else 0

                table.add_row(
                    filing.form,
                    filing.filing_date.strftime("%Y-%m-%d") if filing.filing_date else "Unknown",
                    filing.period_of_report.strftime("%Y-%m-%d") if filing.period_of_report else "Unknown",
                    filing.accession_number,
                    str(doc_count)
                )

            console.print(table)

    except Exception as e:
        if output == 'json':
            error_data = {"error": str(e)}
            click.echo(json.dumps(error_data))
        else:
            console.print(f"[red]Error listing filings: {e}[/red]")
        logger.exception("Failed to list filings")
        sys.exit(1)
    finally:
        # Restore original log levels
        if output == 'json':
            for logger_name, original_level in original_levels.items():
                db_logger = logging.getLogger(logger_name)
                db_logger.setLevel(original_level)


@filings.command('get')
@click.argument('accession_number')
@click.option('-o', '--output', type=click.Choice(['table', 'json']), default='table', help='Output format')
def get_filing(accession_number: str, output: str):
    """Get detailed information about a specific filing."""

    # For JSON output, temporarily suppress INFO level logs to avoid interference with JSON parsing
    if output == 'json':
        # Get all loggers and set their level to WARNING temporarily
        original_levels = {}
        for logger_name in ['src.database.filings']:
            db_logger = logging.getLogger(logger_name)
            original_levels[logger_name] = db_logger.level
            db_logger.setLevel(logging.WARNING)

    try:
        _ = init_session()
        filing = get_filing_by_accession_number(accession_number)

        if not filing:
            if output == 'json':
                error_data = {"error": f"Filing with accession number '{accession_number}' not found"}
                click.echo(json.dumps(error_data))
            else:
                console.print(f"[red]Error: Filing with accession number '{accession_number}' not found[/red]")
            sys.exit(1)

        if output == 'json':
            # Prepare data for JSON output
            filing_data = {
                "accession_number": filing.accession_number,
                "form": filing.form,
                "company_name": filing.company.name if filing.company else None,
                "filing_date": filing.filing_date.strftime("%Y-%m-%d") if filing.filing_date else None,
                "period_of_report": filing.period_of_report.strftime("%Y-%m-%d") if filing.period_of_report else None,
                "document_count": len(filing.documents) if hasattr(filing, 'documents') else 0
            }
            click.echo(json.dumps(filing_data, indent=2))
        else:
            # Original table output
            panel_title = f"Filing: {filing.form}"

            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_row("[bold blue]Accession Number:[/bold blue]", filing.accession_number)
            table.add_row("[bold blue]Form Type:[/bold blue]", filing.form)
            table.add_row("[bold blue]Company:[/bold blue]", filing.company.name if filing.company else "Unknown")
            table.add_row("[bold blue]Filing Date:[/bold blue]", filing.filing_date.strftime("%Y-%m-%d") if filing.filing_date else "Unknown")
            table.add_row("[bold blue]Period End:[/bold blue]", filing.period_of_report.strftime("%Y-%m-%d") if filing.period_of_report else "Unknown")
            table.add_row("[bold blue]Documents:[/bold blue]", str(len(filing.documents)) if hasattr(filing, 'documents') else "0")

            console.print(Panel(table, title=panel_title))

    except Exception as e:
        if output == 'json':
            error_data = {"error": str(e)}
            click.echo(json.dumps(error_data))
        else:
            console.print(f"[red]Error retrieving filing: {e}[/red]")
        logger.exception("Failed to get filing")
        sys.exit(1)
    finally:
        # Restore original log levels
        if output == 'json':
            for logger_name, original_level in original_levels.items():
                db_logger = logging.getLogger(logger_name)
                db_logger.setLevel(original_level)
