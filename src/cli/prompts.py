"""CLI commands for prompt management."""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.database.base import get_db_session
import src.database.prompts as db
from src.utils.logging import get_logger

logger = get_logger(__name__)
console = Console()


def init_session():
    """Initialize database session."""
    from src.database.base import init_db
    from src.utils.config import settings
    init_db(settings.database.url)
    return get_db_session()


@click.group()
def prompts():
    """Prompt management commands."""
    pass


@prompts.command('create')
@click.argument('name')
@click.option('--description', '-d', help='Prompt description')
@click.option('--role', type=click.Choice(['system', 'user', 'assistant']), default='system', help='Prompt role')
@click.option('--examples-dir', help='Directory containing example files to append')
def create_prompt(name: str, description: Optional[str], role: str, examples_dir: Optional[str]):
    """
    Create a new prompt from prompts/{name}/prompt.md.

    Automatically appends examples from prompts/{name}/examples/ if they exist.
    """
    prompts_dir = Path("prompts")
    prompt_dir = prompts_dir / name
    prompt_file = prompt_dir / "prompt.md"
    examples_dir_path = prompt_dir / "examples"

    if not prompt_file.exists():
        console.print(f"[red]Error: {prompt_file} does not exist[/red]")
        sys.exit(1)

    # Read main prompt content
    content = prompt_file.read_text().strip()

    # Append examples if they exist
    if examples_dir_path.exists() and examples_dir_path.is_dir():
        example_files = sorted(examples_dir_path.glob("*.md"))
        if example_files:
            for example_file in example_files:
                content += "\n\n"
                content += example_file.read_text().strip()

    # Create prompt in database
    try:
        init_session()
        prompt_data = {
            'name': name,
            'description': description or f"Prompt: {name}",
            'role': role,
            'content': content
        }

        prompt_obj, was_created = db.create_prompt(prompt_data)

        if was_created:
            console.print(f"[green]✓[/green] Prompt created: {name}")
        else:
            console.print(f"[yellow]⚡[/yellow] Found existing prompt with same content: {prompt_obj.get_short_hash()}")

        console.print(f"[blue]Hash:[/blue] {prompt_obj.get_short_hash()}")
        console.print(f"[blue]ID:[/blue] {prompt_obj.id}")

    except Exception as e:
        console.print(f"[red]Error creating prompt: {e}[/red]")
        logger.exception("Failed to create prompt")
        sys.exit(1)


@prompts.command('get')
@click.argument('hash_or_name')
def get_prompt(hash_or_name: str):
    """Get and display a prompt by hash or name."""

    try:
        init_session()
        # Try to get by hash first, then by name
        prompt_obj = db.get_prompt_by_content_hash(hash_or_name)
        if not prompt_obj:
            # Try by name
            session = init_session()
            prompt_obj = session.query(db.Prompt).filter(db.Prompt.name == hash_or_name).first()

        if not prompt_obj:
            console.print(f"[red]Error: Prompt '{hash_or_name}' not found[/red]")
            sys.exit(1)

        # Display prompt info
        panel_title = f"Prompt: {prompt_obj.name}"

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_row("[bold blue]ID:[/bold blue]", str(prompt_obj.id))
        table.add_row("[bold blue]Name:[/bold blue]", prompt_obj.name)
        table.add_row("[bold blue]Role:[/bold blue]", prompt_obj.role.value)
        table.add_row("[bold blue]Hash:[/bold blue]", prompt_obj.get_short_hash())
        table.add_row("[bold blue]Description:[/bold blue]", prompt_obj.description or "None")

        console.print(Panel(table, title=panel_title))
        console.print("\n[bold]Content:[/bold]")
        console.print(Panel(prompt_obj.content, title="Prompt Content"))

    except Exception as e:
        console.print(f"[red]Error retrieving prompt: {e}[/red]")
        logger.exception("Failed to get prompt")
        sys.exit(1)


@prompts.command('list')
@click.option('--limit', default=10, help='Maximum number of items to show')
def list_prompts(limit: int):
    """List all prompts."""

    try:
        session = init_session()
        prompts_list = session.query(db.Prompt).limit(limit).all()

        if not prompts_list:
            console.print("[yellow]No prompts found[/yellow]")
            return

        table = Table(title="Prompts")
        table.add_column("Name", style="cyan")
        table.add_column("Role", style="magenta")
        table.add_column("Hash", style="green")
        table.add_column("Description", style="white")

        for prompt in prompts_list:
            description = (prompt.description[:50] + "...") if prompt.description and len(prompt.description) > 50 else (prompt.description or "")
            table.add_row(
                prompt.name,
                prompt.role.value,
                prompt.get_short_hash()[:8],
                description
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error listing prompts: {e}[/red]")
        logger.exception("Failed to list prompts")
