"""CLI commands for financial data management."""

import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from collector.database.base import get_db_session
from collector.database.companies import get_company_by_ticker
from collector.database.filings import Filing
from collector.database.financial_concepts import FinancialConcept
from collector.database.financial_values import FinancialValue
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
def financials():
    """Financial data management commands."""
    pass


@financials.command('list-concepts')
@click.option('--search', help='Search concepts by name or label')
@click.option('--limit', default=20, help='Maximum number of concepts to show')
def list_concepts(search: str, limit: int):
    """List financial concepts in the database."""

    try:
        session = init_session()

        query = session.query(FinancialConcept)

        # Apply search filter if provided
        if search:
            query = query.filter(
                FinancialConcept.name.ilike(f"%{search}%") |
                FinancialConcept.label.ilike(f"%{search}%")
            )

        concepts = query.limit(limit).all()

        if not concepts:
            console.print("[yellow]No financial concepts found[/yellow]")
            return

        table = Table(title=f"Financial Concepts ({len(concepts)} found)")
        table.add_column("Name", style="cyan")
        table.add_column("Label", style="white")
        table.add_column("Type", style="magenta")
        table.add_column("Abstract", style="yellow")

        for concept in concepts:
            name = concept.name[:30] + "..." if concept.name and len(concept.name) > 30 else (concept.name or "Unknown")
            label = concept.label[:40] + "..." if concept.label and len(concept.label) > 40 else (concept.label or "Unknown")

            table.add_row(
                name,
                label,
                concept.type or "Unknown",
                "Yes" if concept.abstract else "No"
            )

        console.print(table)

        if len(concepts) == limit:
            console.print(f"\n[yellow]Showing first {limit} results. Use --limit to see more.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error listing financial concepts: {e}[/red]")
        logger.exception("Failed to list financial concepts")
        sys.exit(1)


@financials.command('list-values')
@click.argument('ticker')
@click.option('--concept', help='Filter by financial concept name')
@click.option('--year', type=int, help='Filter by year')
@click.option('--limit', default=20, help='Maximum number of values to show')
def list_values(ticker: str, concept: str, year: int, limit: int):
    """List financial values for a company."""

    ticker = ticker.upper()

    try:
        session = init_session()

        # Get company
        company_obj = get_company_by_ticker(ticker)
        if not company_obj:
            console.print(f"[red]Error: Company {ticker} not found[/red]")
            sys.exit(1)

        # Build query
        query = session.query(FinancialValue).filter(FinancialValue.company_id == company_obj.id)

        # Apply filters
        if concept:
            query = query.join(FinancialConcept).filter(FinancialConcept.name.ilike(f"%{concept}%"))

        if year:
            # Filter by filing year (approximate)
            query = query.join(FinancialValue.filing).filter(
                FinancialValue.filing.has(Filing.filing_date.between(f"{year}-01-01", f"{year}-12-31"))
            )

        values = query.limit(limit).all()

        if not values:
            console.print(f"[yellow]No financial values found for {ticker}[/yellow]")
            return

        console.print(f"[blue]Company:[/blue] {company_obj.name} ({ticker})")

        table = Table(title=f"Financial Values ({len(values)} found)")
        table.add_column("Concept", style="cyan")
        table.add_column("Value", style="white")
        table.add_column("Unit", style="yellow")
        table.add_column("Period", style="magenta")
        table.add_column("Filing", style="green")

        for value in values:
            concept_name = value.financial_concept.name[:30] + "..." if value.financial_concept and len(value.financial_concept.name) > 30 else (value.financial_concept.name if value.financial_concept else "Unknown")

            # Format the value based on its type
            if value.value is not None:
                try:
                    # Try to format as number
                    numeric_value = float(value.value)
                    if abs(numeric_value) >= 1000000000:
                        formatted_value = f"{numeric_value/1000000000:.1f}B"
                    elif abs(numeric_value) >= 1000000:
                        formatted_value = f"{numeric_value/1000000:.1f}M"
                    elif abs(numeric_value) >= 1000:
                        formatted_value = f"{numeric_value/1000:.1f}K"
                    else:
                        formatted_value = f"{numeric_value:.2f}"
                except (ValueError, TypeError):
                    formatted_value = str(value.value)[:20]
            else:
                formatted_value = "N/A"

            table.add_row(
                concept_name,
                formatted_value,
                value.unit_ref or "Unknown",
                value.context_ref or "Unknown",
                value.filing.accession_number[:15] + "..." if value.filing and len(value.filing.accession_number) > 15 else (value.filing.accession_number if value.filing else "Unknown")
            )

        console.print(table)

        if len(values) == limit:
            console.print(f"\n[yellow]Showing first {limit} results. Use --limit to see more.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error listing financial values: {e}[/red]")
        logger.exception("Failed to list financial values")
        sys.exit(1)


@financials.command('get-concept')
@click.argument('concept_name')
def get_concept(concept_name: str):
    """Get detailed information about a financial concept."""

    try:
        session = init_session()

        # Try exact match first, then partial match
        concept = session.query(FinancialConcept).filter(FinancialConcept.name == concept_name).first()

        if not concept:
            concept = session.query(FinancialConcept).filter(
                FinancialConcept.name.ilike(f"%{concept_name}%")
            ).first()

        if not concept:
            console.print(f"[red]Error: Financial concept '{concept_name}' not found[/red]")
            sys.exit(1)

        # Display concept info
        panel_title = f"Financial Concept: {concept.name}"

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_row("[bold blue]ID:[/bold blue]", str(concept.id))
        table.add_row("[bold blue]Name:[/bold blue]", concept.name)
        table.add_row("[bold blue]Label:[/bold blue]", concept.label or "Unknown")
        table.add_row("[bold blue]Type:[/bold blue]", concept.type or "Unknown")
        table.add_row("[bold blue]Abstract:[/bold blue]", "Yes" if concept.abstract else "No")
        table.add_row("[bold blue]Nillable:[/bold blue]", "Yes" if concept.nillable else "No")
        table.add_row("[bold blue]Period Type:[/bold blue]", concept.period_type or "Unknown")
        table.add_row("[bold blue]Balance:[/bold blue]", concept.balance or "Unknown")

        console.print(Panel(table, title=panel_title))

        # Show some example values
        values = session.query(FinancialValue).filter(
            FinancialValue.financial_concept_id == concept.id
        ).limit(5).all()

        if values:
            console.print(f"\n[bold]Recent Values ({len(values)} shown):[/bold]")
            value_table = Table()
            value_table.add_column("Company", style="cyan")
            value_table.add_column("Value", style="white")
            value_table.add_column("Unit", style="yellow")
            value_table.add_column("Period", style="magenta")

            for value in values:
                company_name = value.company.ticker if value.company else "Unknown"
                formatted_value = str(value.value)[:20] if value.value is not None else "N/A"

                value_table.add_row(
                    company_name,
                    formatted_value,
                    value.unit_ref or "Unknown",
                    value.context_ref or "Unknown"
                )

            console.print(value_table)

    except Exception as e:
        console.print(f"[red]Error retrieving financial concept: {e}[/red]")
        logger.exception("Failed to get financial concept")
        sys.exit(1)
