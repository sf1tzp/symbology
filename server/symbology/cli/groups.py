"""CLI commands for company group management."""

import sys

import click
from rich.console import Console
from rich.table import Table
from symbology.database.base import get_db_session, init_db
from symbology.database.companies import get_company_by_ticker
from symbology.database.company_groups import (
    add_company_to_group,
    create_company_group,
    get_company_group_by_slug,
    list_company_groups,
    populate_group_from_sic_codes,
)
from symbology.utils.config import settings
from symbology.utils.logging import get_logger

logger = get_logger(__name__)
console = Console()


def init_session():
    """Initialize database session."""
    init_db(settings.database.url)
    return get_db_session()


@click.group()
def group():
    """Company group management."""
    pass


@group.command("create")
@click.option("--name", required=True, help="Display name for the group")
@click.option("--slug", required=True, help="URL-friendly identifier")
@click.option("--sic-codes", default=None, help="Comma-separated SIC code prefixes (e.g. 35,73)")
@click.option("--description", default=None, help="Group description")
def create_group(name: str, slug: str, sic_codes: str, description: str):
    """Create a new company group."""
    try:
        init_session()

        data = {
            "name": name,
            "slug": slug,
            "sic_codes": [s.strip() for s in sic_codes.split(",")] if sic_codes else [],
        }
        if description:
            data["description"] = description

        grp = create_company_group(data)

        console.print(f"[green]✓[/green] Created group '{grp.name}' (slug: {grp.slug})")
        console.print(f"  [blue]ID:[/blue]        {grp.id}")
        if grp.sic_codes:
            console.print(f"  [blue]SIC codes:[/blue] {', '.join(grp.sic_codes)}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Group create failed")
        sys.exit(1)


@group.command("list")
def list_groups():
    """List all company groups."""
    try:
        init_session()

        groups = list_company_groups()

        if not groups:
            console.print("[yellow]No company groups found[/yellow]")
            return

        table = Table(title="Company Groups")
        table.add_column("Slug", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("SIC Codes", style="dim")
        table.add_column("Members", justify="right")

        for grp in groups:
            table.add_row(
                grp.slug,
                grp.name,
                ", ".join(grp.sic_codes) if grp.sic_codes else "-",
                str(len(grp.companies)),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Group list failed")
        sys.exit(1)


@group.command("show")
@click.option("--slug", required=True, help="Group slug to show")
def show_group(slug: str):
    """Show group details and member companies."""
    try:
        init_session()

        grp = get_company_group_by_slug(slug)
        if not grp:
            console.print(f"[red]Group not found: {slug}[/red]")
            sys.exit(1)

        console.print(f"\n[bold]{grp.name}[/bold] ({grp.slug})")
        console.print(f"  [blue]Description:[/blue] {grp.description or 'N/A'}")
        console.print(f"  [blue]SIC codes:[/blue]   {', '.join(grp.sic_codes) if grp.sic_codes else 'N/A'}")
        console.print(f"  [blue]Members:[/blue]     {len(grp.companies)}")

        if grp.companies:
            console.print()
            table = Table(title="Member Companies")
            table.add_column("Ticker", style="cyan")
            table.add_column("Name", style="white")
            table.add_column("SIC", style="dim")

            for company in grp.companies:
                table.add_row(company.ticker, company.name, company.sic or "-")

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Group show failed")
        sys.exit(1)


@group.command("add-company")
@click.option("--slug", required=True, help="Group slug")
@click.option("--ticker", required=True, help="Company ticker to add")
def add_company(slug: str, ticker: str):
    """Add a company to a group."""
    try:
        init_session()

        company = get_company_by_ticker(ticker.upper())
        if not company:
            console.print(f"[red]Company not found: {ticker}[/red]")
            sys.exit(1)

        added = add_company_to_group(slug, company.id)
        if added:
            console.print(f"[green]✓[/green] Added {ticker.upper()} to group '{slug}'")
        else:
            console.print(f"[yellow]{ticker.upper()} is already in group '{slug}'[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Add company to group failed")
        sys.exit(1)


@group.command("populate")
@click.option("--slug", required=True, help="Group slug to populate")
def populate(slug: str):
    """Auto-populate group members from SIC codes."""
    try:
        init_session()

        added = populate_group_from_sic_codes(slug)
        console.print(f"[green]✓[/green] Added {added} companies to group '{slug}' from SIC codes")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Group populate failed")
        sys.exit(1)
