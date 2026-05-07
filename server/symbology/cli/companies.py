"""CLI commands for company management."""

import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from symbology.database.base import get_db_session, init_db
from symbology.database.companies import Company, get_company_by_ticker
from symbology.ingestion.edgar_db.accessors import edgar_login
from symbology.ingestion.ingestion_helpers import ingest_company
from symbology.utils.config import settings
from symbology.utils.logging import get_logger

logger = get_logger(__name__)
console = Console()

def init_session():
    """Initialize database session."""
    init_db(settings.database.url)
    return get_db_session()


@click.group()
def companies():
    """Company management commands."""
    pass


@companies.command('ingest')
@click.argument('ticker')
@click.option('--force', is_flag=True, help='Force re-ingestion even if company exists')
def ingest_company_cmd(ticker: str, force: bool):
    """
    Ingest basic company information.

    TICKER: Company ticker symbol (e.g., AAPL)
    """
    ticker = ticker.upper()

    console.print(f"[bold blue]Ingesting company: {ticker}[/bold blue]")

    try:
        init_session()
        edgar_login(settings.edgar_api.edgar_contact)

        # Check if company already exists
        existing_company = get_company_by_ticker(ticker)
        if existing_company and not force:
            console.print(f"[yellow]Company {ticker} already exists. Use --force to re-ingest.[/yellow]")
            console.print(f"[green]Existing company: {existing_company.name}[/green]")
            return

        # Ingest company
        edgar_company, db_id = ingest_company(ticker)
        if edgar_company:
            console.print(f"[green]✓[/green] Company ingested: {edgar_company.name}")
            console.print(f"[blue]ID:[/blue] {db_id}")
            console.print(f"[blue]Ticker:[/blue] {edgar_company.get_ticker()}")
        else:
            console.print(f"[red]✗[/red] Failed to ingest company {ticker}")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error during company ingestion: {e}[/red]")
        logger.exception("Company ingestion failed")
        sys.exit(1)


@companies.command('get')
@click.argument('ticker')
def get_company(ticker: str):
    """Get and display company information by ticker."""

    ticker = ticker.upper()

    try:
        init_session()
        company_obj = get_company_by_ticker(ticker)

        if not company_obj:
            console.print(f"[red]Error: Company with ticker '{ticker}' not found[/red]")
            sys.exit(1)

        # Display company info
        panel_title = f"Company: {company_obj.name}"

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_row("[bold blue]ID:[/bold blue]", str(company_obj.id))
        table.add_row("[bold blue]Name:[/bold blue]", company_obj.name)
        table.add_row("[bold blue]Ticker:[/bold blue]", company_obj.ticker)
        table.add_row("[bold blue]Industry:[/bold blue]", company_obj.sic_description or "Unknown")

        console.print(Panel(table, title=panel_title))

    except Exception as e:
        console.print(f"[red]Error retrieving company: {e}[/red]")
        logger.exception("Failed to get company")
        sys.exit(1)


@companies.command('list')
@click.option('--limit', default=20, help='Maximum number of companies to show')
@click.option('--sector', help='Filter by sector')
@click.option('--industry', help='Filter by industry')
def list_companies(limit: int, sector: str, industry: str):
    """List companies in the database."""

    try:
        session = init_session()
        query = session.query(Company)

        # Apply filters
        if sector:
            query = query.filter(Company.sector.ilike(f"%{sector}%"))
        if industry:
            query = query.filter(Company.industry.ilike(f"%{industry}%"))

        companies_list = query.limit(limit).all()

        if not companies_list:
            console.print("[yellow]No companies found[/yellow]")
            return

        table = Table(title="Companies")
        table.add_column("Ticker", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Sector", style="magenta")
        table.add_column("Industry", style="yellow")

        for company in companies_list:
            table.add_row(
                company.ticker,
                company.name[:40] + "..." if len(company.name) > 40 else company.name,
                company.sic or "Unknown",
                company.sic_description[:30] + "..." if company.sic_description and len(company.sic_description) > 30 else (company.sic_description or "Unknown"),
            )

        console.print(table)

        if len(companies_list) == limit:
            console.print(f"\n[yellow]Showing first {limit} results. Use --limit to see more.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error listing companies: {e}[/red]")
        logger.exception("Failed to list companies")
