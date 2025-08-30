"""CLI commands for model configuration management."""

import json
import logging
import sys
from typing import Optional
from uuid import UUID

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from src.database.base import get_db_session
import src.database.model_configs as db
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
def model_configs():
    """Model configuration management commands."""
    pass


@model_configs.command('create')
@click.argument('model_name')
@click.option('--temperature', type=float, help='Model temperature')
@click.option('--num-ctx', type=int, help='Context window size')
@click.option('--top-k', type=int, help='Top-k sampling')
@click.option('--top-p', type=float, help='Top-p sampling')
@click.option('--num-predict', type=int, help='Maximum number of tokens to predict')
@click.option('--num-gpu', type=int, help='Number of GPUs to use')
@click.option('--options', help='JSON string of additional options')
@click.option('-o', '--output', type=click.Choice(['table', 'json']), default='table', help='Output format')
def create_model_config(model_name: str, temperature: Optional[float], num_ctx: Optional[int],
                       top_k: Optional[int], top_p: Optional[float],
                       num_predict: Optional[int], num_gpu: Optional[int], options: Optional[str], output: str):
    """
    Create a new model configuration.

    MODEL_NAME: Name of the model (e.g., qwen3:14b, gpt-4o)
    """
    # For JSON output, temporarily suppress INFO level logs to avoid interference with JSON parsing
    if output == 'json':
        # Get all loggers and set their level to WARNING temporarily
        original_levels = {}
        for logger_name in ['src.database.model_configs']:
            db_logger = logging.getLogger(logger_name)
            original_levels[logger_name] = db_logger.level
            db_logger.setLevel(logging.WARNING)

    try:
        init_session()

        # Start with default model config
        model_config_obj = db.ModelConfig.create_default(model_name)
        config_options = json.loads(model_config_obj.options_json)

        # Override with CLI-provided options
        if temperature is not None:
            config_options['temperature'] = temperature
        if num_ctx is not None:
            config_options['num_ctx'] = num_ctx
        if top_k is not None:
            config_options['top_k'] = top_k
        if top_p is not None:
            config_options['top_p'] = top_p
        if num_predict is not None:
            config_options['num_predict'] = num_predict
        if num_gpu is not None:
            config_options['num_gpu'] = num_gpu

        # Parse and merge additional options if provided
        if options:
            try:
                additional_options = json.loads(options)
                config_options.update(additional_options)
            except json.JSONDecodeError as e:
                if output == 'json':
                    error_data = {"error": f"Error parsing options JSON: {e}"}
                    click.echo(json.dumps(error_data))
                else:
                    console.print(f"[red]Error parsing options JSON: {e}[/red]")
                sys.exit(1)

        model_config_data = {
            'model': model_name,
            'options_json': json.dumps(config_options, sort_keys=True)
        }
        model_config_obj = db.create_model_config(model_config_data)

        if output == 'json':
            # Prepare data for JSON output
            config_data = {
                "id": str(model_config_obj.id),
                "model": model_config_obj.model,
                "content_hash": model_config_obj.content_hash,
                "short_hash": model_config_obj.get_short_hash(),
                "created_at": model_config_obj.created_at.isoformat() if model_config_obj.created_at else None,
                "options": config_options
            }
            click.echo(json.dumps(config_data, indent=2))
        else:
            console.print(f"[green]✓[/green] Model config created: {model_name}")
            console.print(f"[blue]Hash:[/blue] {model_config_obj.get_short_hash()}")
            console.print(f"[blue]ID:[/blue] {model_config_obj.id}")
            console.print(f"[blue]Options:[/blue] {json.dumps(config_options, indent=2)}")

    except Exception as e:
        if output == 'json':
            error_data = {"error": str(e)}
            click.echo(json.dumps(error_data))
        else:
            console.print(f"[red]Error creating model config: {e}[/red]")
        logger.exception("Failed to create model config")
        sys.exit(1)
    finally:
        # Restore original log levels
        if output == 'json':
            for logger_name, original_level in original_levels.items():
                db_logger = logging.getLogger(logger_name)
                db_logger.setLevel(original_level)


@model_configs.command('get')
@click.argument('hash_or_id')
@click.option('-o', '--output', type=click.Choice(['table', 'json']), default='table', help='Output format')
def get_model_config(hash_or_id: str, output: str):
    """Get and display a model configuration by hash or ID."""

    # For JSON output, temporarily suppress INFO level logs to avoid interference with JSON parsing
    if output == 'json':
        # Get all loggers and set their level to WARNING temporarily
        original_levels = {}
        for logger_name in ['src.database.model_configs']:
            db_logger = logging.getLogger(logger_name)
            original_levels[logger_name] = db_logger.level
            db_logger.setLevel(logging.WARNING)

    try:
        init_session()
        # Try to get by hash first, then by ID
        model_config_obj = db.get_model_config_by_content_hash(hash_or_id)
        if not model_config_obj:
            # Try by ID
            session = init_session()
            try:
                uuid_obj = UUID(hash_or_id)
                model_config_obj = session.query(db.ModelConfig).filter(db.ModelConfig.id == uuid_obj).first()
            except ValueError:
                pass

        if not model_config_obj:
            if output == 'json':
                error_data = {"error": f"Model config '{hash_or_id}' not found"}
                click.echo(json.dumps(error_data))
            else:
                console.print(f"[red]Error: Model config '{hash_or_id}' not found[/red]")
            sys.exit(1)

        if output == 'json':
            # Prepare data for JSON output
            options = json.loads(model_config_obj.options_json)
            config_data = {
                "id": str(model_config_obj.id),
                "model": model_config_obj.model,
                "content_hash": model_config_obj.content_hash,
                "short_hash": model_config_obj.get_short_hash(),
                "created_at": model_config_obj.created_at.isoformat() if model_config_obj.created_at else None,
                "options": options
            }
            click.echo(json.dumps(config_data, indent=2))
        else:
            # Display model config info
            panel_title = f"Model Config: {model_config_obj.model}"

            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_row("[bold blue]ID:[/bold blue]", str(model_config_obj.id))
            table.add_row("[bold blue]Name:[/bold blue]", model_config_obj.model)
            table.add_row("[bold blue]Hash:[/bold blue]", model_config_obj.get_short_hash())
            table.add_row("[bold blue]Created:[/bold blue]", model_config_obj.created_at.isoformat() if model_config_obj.created_at else "Unknown")

            console.print(Panel(table, title=panel_title))
            console.print("\n[bold]Options:[/bold]")
            options = json.loads(model_config_obj.options_json)
            console.print(Panel(json.dumps(options, indent=2), title="Model Options"))

    except Exception as e:
        if output == 'json':
            error_data = {"error": str(e)}
            click.echo(json.dumps(error_data))
        else:
            console.print(f"[red]Error retrieving model config: {e}[/red]")
        logger.exception("Failed to get model config")
        sys.exit(1)
    finally:
        # Restore original log levels
        if output == 'json':
            for logger_name, original_level in original_levels.items():
                db_logger = logging.getLogger(logger_name)
                db_logger.setLevel(original_level)


@model_configs.command('list')
@click.option('--limit', default=10, help='Maximum number of items to show')
@click.option('-o', '--output', type=click.Choice(['table', 'json']), default='table', help='Output format')
def list_model_configs(limit: int, output: str):
    """List all model configurations."""

    # For JSON output, temporarily suppress INFO level logs to avoid interference with JSON parsing
    if output == 'json':
        # Get all loggers and set their level to WARNING temporarily
        original_levels = {}
        for logger_name in ['src.database.model_configs']:
            db_logger = logging.getLogger(logger_name)
            original_levels[logger_name] = db_logger.level
            db_logger.setLevel(logging.WARNING)

    try:
        session = init_session()
        configs = session.query(db.ModelConfig).limit(limit).all()

        if not configs:
            if output == 'json':
                click.echo(json.dumps([]))
            else:
                console.print("[yellow]No model configs found[/yellow]")
            return

        if output == 'json':
            # Prepare data for JSON output
            configs_data = []
            for config in configs:
                options = json.loads(config.options_json)
                config_data = {
                    "id": str(config.id),
                    "model": config.model,
                    "content_hash": config.content_hash,
                    "short_hash": config.get_short_hash(),
                    "created_at": config.created_at.isoformat() if config.created_at else None,
                    "options": options
                }
                configs_data.append(config_data)

            click.echo(json.dumps(configs_data, indent=2))
        else:
            table = Table(title="Model Configurations")
            table.add_column("Name", style="cyan")
            table.add_column("Hash", style="green")
            table.add_column("Created", style="white")
            table.add_column("Options", style="yellow")

            for config in configs:
                options = json.loads(config.options_json)
                options_str = ", ".join([f"{k}={v}" for k, v in list(options.items())[:3]])
                if len(options) > 3:
                    options_str += "..."

                table.add_row(
                    config.model,
                    config.get_short_hash()[:8],
                    config.created_at.strftime("%Y-%m-%d") if config.created_at else "Unknown",
                    options_str
                )

            console.print(table)

    except Exception as e:
        if output == 'json':
            error_data = {"error": str(e)}
            click.echo(json.dumps(error_data))
        else:
            console.print(f"[red]Error listing model configs: {e}[/red]")
        logger.exception("Failed to list model configs")
        sys.exit(1)
    finally:
        # Restore original log levels
        if output == 'json':
            for logger_name, original_level in original_levels.items():
                db_logger = logging.getLogger(logger_name)
                db_logger.setLevel(original_level)
