"""CLI commands for company management."""

import sys
from datetime import date

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


def _fye_on(year: int, fye: date) -> date:
    """The fiscal-year-end falling in ``year`` (clamps a 02-29 FYE on non-leap years)."""
    day = fye.day
    while True:
        try:
            return date(year, fye.month, day)
        except ValueError:
            day -= 1  # e.g. Feb 29 -> Feb 28 in a non-leap year


def current_fiscal_quarter_label(fye: date, today: date) -> str:
    """Where a company is in its fiscal year *right now*, e.g. "FY2026 Q3".

    Derived from the fiscal-year-end day and today: the fiscal year is named for
    the calendar year it ends in, and the quarter is the count of (whole) three-
    month blocks elapsed since the fiscal year began (the day after the prior
    year-end). Day-accurate so a company mid-quarter isn't bumped to the next one.
    """
    # End of the fiscal year we're currently in: the first FYE on or after today.
    fye_end = _fye_on(today.year, fye)
    if fye_end < today:
        fye_end = _fye_on(today.year + 1, fye)
    # Fiscal year started the day after the previous year-end.
    fy_start = _fye_on(fye_end.year - 1, fye)
    months = (today.year - fy_start.year) * 12 + (today.month - fy_start.month)
    if today.day <= fy_start.day:  # not yet a full month past the year-end day
        months -= 1
    quarter = min(max(months // 3 + 1, 1), 4)
    return f"FY{fye_end.year} Q{quarter}"


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
        table.add_column("Fiscal Year End", style="green")
        table.add_column("Current Quarter", style="green")

        today = date.today()
        for company in companies_list:
            fye = company.fiscal_year_end
            table.add_row(
                company.ticker,
                company.name[:40] + "..." if len(company.name) > 40 else company.name,
                company.sic or "Unknown",
                company.sic_description[:30] + "..." if company.sic_description and len(company.sic_description) > 30 else (company.sic_description or "Unknown"),
                fye.strftime("%m-%d") if fye else "—",
                current_fiscal_quarter_label(fye, today) if fye else "—",
            )

        console.print(table)

        if len(companies_list) == limit:
            console.print(f"\n[yellow]Showing first {limit} results. Use --limit to see more.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error listing companies: {e}[/red]")
        logger.exception("Failed to list companies")
