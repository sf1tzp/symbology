"""CLI commands for prompt management."""

import json
import logging
from pathlib import Path
import sys
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from collector.database.base import get_db_session
import collector.database.prompts as db
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
def prompts():
    """Prompt management commands."""
    pass


@prompts.command('create')
@click.argument('name')
@click.option('--description', '-d', help='Prompt description')
@click.option('--role', type=click.Choice(['system', 'user', 'assistant']), default='system', help='Prompt role')
@click.option('--examples-dir', help='Directory containing example files to append')
@click.option('-o', '--output', type=click.Choice(['table', 'json']), default='table', help='Output format')
def create_prompt(name: str, description: Optional[str], role: str, examples_dir: Optional[str], output: str):
    """
    Create a new prompt from prompts/{name}/prompt.md.

    Automatically appends examples from prompts/{name}/examples/ if they exist.
    """
    # For JSON output, temporarily suppress INFO level logs to avoid interference with JSON parsing
    if output == 'json':
        # Get all loggers and set their level to WARNING temporarily
        original_levels = {}
        for logger_name in ['src.database.prompts']:
            db_logger = logging.getLogger(logger_name)
            original_levels[logger_name] = db_logger.level
            db_logger.setLevel(logging.WARNING)

    try:
        prompts_dir = Path("prompts")
        prompt_dir = prompts_dir / name
        prompt_file = prompt_dir / "prompt.md"
        examples_dir_path = prompt_dir / "examples"

        if not prompt_file.exists():
            if output == 'json':
                error_data = {"error": f"{prompt_file} does not exist"}
                click.echo(json.dumps(error_data))
            else:
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
        init_session()
        prompt_data = {
            'name': name,
            'description': description or f"Prompt: {name}",
            'role': role,
            'content': content
        }

        prompt_obj, was_created = db.create_prompt(prompt_data)

        if output == 'json':
            # Prepare data for JSON output
            prompt_data = {
                "id": str(prompt_obj.id),
                "name": prompt_obj.name,
                "description": prompt_obj.description,
                "role": prompt_obj.role.value,
                "content_hash": prompt_obj.content_hash,
                "short_hash": prompt_obj.get_short_hash(),
                "was_created": was_created,
                "content_size": len(prompt_obj.content) if prompt_obj.content else 0
            }
            click.echo(json.dumps(prompt_data, indent=2))
        else:
            if was_created:
                console.print(f"[green]✓[/green] Prompt created: {name}")
            else:
                console.print(f"[yellow]⚡[/yellow] Found existing prompt with same content: {prompt_obj.get_short_hash()}")

            console.print(f"[blue]Hash:[/blue] {prompt_obj.get_short_hash()}")
            console.print(f"[blue]ID:[/blue] {prompt_obj.id}")

    except Exception as e:
        if output == 'json':
            error_data = {"error": str(e)}
            click.echo(json.dumps(error_data))
        else:
            console.print(f"[red]Error creating prompt: {e}[/red]")
        logger.exception("Failed to create prompt")
        sys.exit(1)
    finally:
        # Restore original log levels
        if output == 'json':
            for logger_name, original_level in original_levels.items():
                db_logger = logging.getLogger(logger_name)
                db_logger.setLevel(original_level)


@prompts.command('get')
@click.argument('hash_or_name')
@click.option('-o', '--output', type=click.Choice(['table', 'json']), default='table', help='Output format')
def get_prompt(hash_or_name: str, output: str):
    """Get and display a prompt by hash or name."""

    # For JSON output, temporarily suppress INFO level logs to avoid interference with JSON parsing
    if output == 'json':
        # Get all loggers and set their level to WARNING temporarily
        original_levels = {}
        for logger_name in ['src.database.prompts']:
            db_logger = logging.getLogger(logger_name)
            original_levels[logger_name] = db_logger.level
            db_logger.setLevel(logging.WARNING)

    try:
        init_session()
        # Try to get by hash first, then by name
        prompt_obj = db.get_prompt_by_content_hash(hash_or_name)
        if not prompt_obj:
            # Try by name
            session = init_session()
            prompt_obj = session.query(db.Prompt).filter(db.Prompt.name == hash_or_name).first()

        if not prompt_obj:
            if output == 'json':
                error_data = {"error": f"Prompt '{hash_or_name}' not found"}
                click.echo(json.dumps(error_data))
            else:
                console.print(f"[red]Error: Prompt '{hash_or_name}' not found[/red]")
            sys.exit(1)

        if output == 'json':
            # Prepare data for JSON output
            prompt_data = {
                "id": str(prompt_obj.id),
                "name": prompt_obj.name,
                "description": prompt_obj.description,
                "role": prompt_obj.role.value,
                "content_hash": prompt_obj.content_hash,
                "short_hash": prompt_obj.get_short_hash(),
                "content": prompt_obj.content,
                "content_size": len(prompt_obj.content) if prompt_obj.content else 0
            }
            click.echo(json.dumps(prompt_data, indent=2))
        else:
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
        if output == 'json':
            error_data = {"error": str(e)}
            click.echo(json.dumps(error_data))
        else:
            console.print(f"[red]Error retrieving prompt: {e}[/red]")
        logger.exception("Failed to get prompt")
        sys.exit(1)
    finally:
        # Restore original log levels
        if output == 'json':
            for logger_name, original_level in original_levels.items():
                db_logger = logging.getLogger(logger_name)
                db_logger.setLevel(original_level)


@prompts.command('list')
@click.option('--limit', default=10, help='Maximum number of items to show')
@click.option('-o', '--output', type=click.Choice(['table', 'json']), default='table', help='Output format')
def list_prompts(limit: int, output: str):
    """List all prompts."""

    # For JSON output, temporarily suppress INFO level logs to avoid interference with JSON parsing
    if output == 'json':
        # Get all loggers and set their level to WARNING temporarily
        original_levels = {}
        for logger_name in ['src.database.prompts']:
            db_logger = logging.getLogger(logger_name)
            original_levels[logger_name] = db_logger.level
            db_logger.setLevel(logging.WARNING)

    try:
        session = init_session()
        prompts_list = session.query(db.Prompt).limit(limit).all()

        if not prompts_list:
            if output == 'json':
                click.echo(json.dumps([]))
            else:
                console.print("[yellow]No prompts found[/yellow]")
            return

        if output == 'json':
            # Prepare data for JSON output
            prompts_data = []
            for prompt in prompts_list:
                content_size = len(prompt.content) if prompt.content else 0
                prompt_data = {
                    "id": str(prompt.id),
                    "name": prompt.name,
                    "description": prompt.description,
                    "role": prompt.role.value,
                    "content_hash": prompt.content_hash,
                    "short_hash": prompt.get_short_hash(),
                    "content_size": content_size
                }
                prompts_data.append(prompt_data)

            click.echo(json.dumps(prompts_data, indent=2))
        else:
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
        if output == 'json':
            error_data = {"error": str(e)}
            click.echo(json.dumps(error_data))
        else:
            console.print(f"[red]Error listing prompts: {e}[/red]")
        logger.exception("Failed to list prompts")
        sys.exit(1)
    finally:
        # Restore original log levels
        if output == 'json':
            for logger_name, original_level in original_levels.items():
                db_logger = logging.getLogger(logger_name)
                db_logger.setLevel(original_level)
