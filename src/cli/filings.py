"""CLI commands for filing management."""

import sys

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.database.base import get_db_session
from src.database.companies import get_company_by_ticker
from src.database.filings import Filing, get_filings_by_company, get_filing_by_accession_number
from src.ingestion.edgar_db.accessors import edgar_login
import src.ingestion.ingestion_helpers as ih
from src.utils.logging import get_logger
from src.utils.config import settings

logger = get_logger(__name__)
console = Console()


def init_session():
    """Initialize database session."""
    from src.database.base import init_db
    from src.utils.config import settings
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
def list_filings(ticker: str, form: str):
    """List filings for a company."""

    ticker = ticker.upper()

    try:
        init_session()

        # Get company
        company_obj = get_company_by_ticker(ticker)
        if not company_obj:
            console.print(f"[red]Error: Company {ticker} not found[/red]")
            sys.exit(1)

        # Get filings
        filings_list = get_filings_by_company(
            company_obj.id,
        )

        if not filings_list:
            console.print(f"[yellow]No filings found for {ticker}[/yellow]")
            return

        table = Table(title=f"Filings for {company_obj.name} ({ticker})")
        table.add_column("Form Type", style="cyan")
        table.add_column("Filing Date", style="white")
        table.add_column("Period End", style="yellow")
        table.add_column("Accession Number", style="green")
        table.add_column("Documents", style="magenta")

        for filing in filings_list:
            if form is not None and filing.form != form:
                continue

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
        console.print(f"[red]Error listing filings: {e}[/red]")
        logger.exception("Failed to list filings")
        sys.exit(1)


@filings.command('get')
@click.argument('accession_number')
def get_filing(accession_number: str):
    """Get detailed information about a specific filing."""

    try:
        session = init_session()
        filing = get_filing_by_accession_number(accession_number)

        if not filing:
            console.print(f"[red]Error: Filing with accession number '{accession_number}' not found[/red]")
            sys.exit(1)

        # Display filing info
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
        console.print(f"[red]Error retrieving filing: {e}[/red]")
        logger.exception("Failed to get filing")
        sys.exit(1)
