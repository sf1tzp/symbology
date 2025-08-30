#!/usr/bin/env python3
"""
Symbology CLI - Administrative tool for managing SEC EDGAR data and AI-generated insights.

This CLI provides a unified interface for:
- Data ingestion from SEC EDGAR filings
- Prompt engineering and model configuration
- Content generation and management
- Database operations

Usage:
    symbology [COMMAND] [OPTIONS]

Examples:
    symbology companies ingest AAPL
    symbology filings ingest AAPL 10-K 2022,2023
    symbology prompts create risk-analysis
    symbology model-configs create qwen3:14b --temperature 0.7 --num-ctx 9000
    symbology generated-content create <prompt-hash> <model-config-hash> <source-hashes...>
    symbology prompts get <hash>
    symbology generated-content get <hash>
    symbology ratings create <content-hash> 5 "Excellent analysis"
"""

import sys
from pathlib import Path

import click

# Add project root to path for imports
# sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.config import settings
from src.utils.logging import configure_logging, get_logger

# Import command modules
from src.cli.companies import companies
from src.cli.documents import documents
from src.cli.filings import filings
from src.cli.financials import financials
from src.cli.generated_content import generated_content
from src.cli.model_configs import model_configs
from src.cli.prompts import prompts
from src.cli.ratings import ratings

# Configure logging
configure_logging(
    log_level=settings.logging.level,
    json_format=settings.logging.json_format
)

logger = get_logger(__name__)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, verbose):
    """Symbology CLI - Administrative tool for SEC EDGAR data and AI insights."""
    ctx.ensure_object(dict)

    if verbose:
        configure_logging(log_level="DEBUG", json_format=False)


# Add command groups
cli.add_command(companies)
cli.add_command(documents)
cli.add_command(filings)
cli.add_command(financials)
cli.add_command(generated_content)
cli.add_command(model_configs)
cli.add_command(prompts)
cli.add_command(ratings)


# Legacy command aliases for backwards compatibility
@cli.group()
def ingest():
    """Legacy ingestion commands (use 'filings ingest' instead)."""
    pass


@ingest.command()
@click.argument('ticker')
@click.argument('form_type', default='10-K')
@click.argument('years', default='2023')
@click.option('--force', is_flag=True, help='Force re-ingestion even if data exists')
def company(ticker: str, form_type: str, years: str, force: bool):
    """
    Ingest SEC filings for a company (legacy command).

    Use 'symbology filings ingest' instead.
    """
    click.echo("[yellow]Warning: 'ingest company' is deprecated. Use 'filings ingest' instead.[/yellow]")

    # Forward to the new command
    ctx = click.get_current_context()
    ctx.invoke(filings.commands['ingest'],
               ticker=ticker,
               form_type=form_type,
               years=years,
               force=force,
               include_documents=True)


@cli.group()
def create():
    """Legacy create commands (use specific command groups instead)."""
    pass


@create.command()
@click.argument('name')
@click.option('--description', '-d', help='Prompt description')
@click.option('--role', type=click.Choice(['system', 'user', 'assistant']), default='system', help='Prompt role')
@click.option('--examples-dir', help='Directory containing example files to append')
def prompt(name: str, description: str, role: str, examples_dir: str):
    """
    Create a new prompt (legacy command).

    Use 'symbology prompts create' instead.
    """
    click.echo("[yellow]Warning: 'create prompt' is deprecated. Use 'prompts create' instead.[/yellow]")

    # Forward to the new command
    ctx = click.get_current_context()
    ctx.invoke(prompts.commands['create'],
               name=name,
               description=description,
               role=role,
               examples_dir=examples_dir)


@create.command('model-config')
@click.argument('model_name')
@click.option('--temperature', type=float, help='Model temperature')
@click.option('--num-ctx', type=int, help='Context window size')
@click.option('--top-k', type=int, help='Top-k sampling')
@click.option('--top-p', type=float, help='Top-p sampling')
@click.option('--num-gpu', type=int, help='Number of GPUs to use')
@click.option('--options', help='JSON string of additional options')
def model_config(model_name: str, temperature: float, num_ctx: int,
                top_k: int, top_p: float, num_gpu: int, options: str):
    """
    Create a new model configuration (legacy command).

    Use 'symbology model-configs create' instead.
    """
    click.echo("[yellow]Warning: 'create model-config' is deprecated. Use 'model-configs create' instead.[/yellow]")

    # Forward to the new command
    ctx = click.get_current_context()
    ctx.invoke(model_configs.commands['create'],
               model_name=model_name,
               temperature=temperature,
               num_ctx=num_ctx,
               top_k=top_k,
               top_p=top_p,
               num_gpu=num_gpu,
               options=options)


@cli.group()
def get():
    """Legacy get commands (use specific command groups instead)."""
    pass


@get.command()
@click.argument('hash_or_name')
def prompt(hash_or_name: str):
    """Get and display a prompt by hash or name (legacy command)."""
    click.echo("[yellow]Warning: 'get prompt' is deprecated. Use 'prompts get' instead.[/yellow]")

    # Forward to the new command
    ctx = click.get_current_context()
    ctx.invoke(prompts.commands['get'], hash_or_name=hash_or_name)


@cli.group()
def list():
    """Legacy list commands (use specific command groups instead)."""
    pass


@list.command()
@click.option('--limit', default=10, help='Maximum number of items to show')
def prompts_legacy(limit: int):
    """List all prompts (legacy command)."""
    click.echo("[yellow]Warning: 'list prompts' is deprecated. Use 'prompts list' instead.[/yellow]")

    # Forward to the new command
    ctx = click.get_current_context()
    ctx.invoke(prompts.commands['list'], limit=limit)


# Legacy rate command
@cli.command()
@click.argument('content_hash')
@click.argument('rating', type=int)
@click.argument('message')
def rate(content_hash: str, rating: int, message: str):
    """
    Rate generated content (legacy command).

    Use 'symbology ratings create' instead.
    """
    click.echo("[yellow]Warning: 'rate' is deprecated. Use 'ratings create' instead.[/yellow]")

    # Forward to the new command
    ctx = click.get_current_context()
    ctx.invoke(ratings.commands['create'],
               content_hash=content_hash,
               rating=rating,
               message=message)


if __name__ == '__main__':
    cli()
