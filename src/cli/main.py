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
    symbology ingest AAPL 10-K 2022,2023
    symbology create prompt risk-analysis
    symbology create model-config qwen3:14b --temperature 0.7 --num-ctx 9000
    symbology create generated-content <prompt-hash> <model-config-hash> <source-hashes...>
    symbology get prompt <hash>
    symbology get content <hash>
    symbology rate <content-hash> 5 "Excellent analysis"
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple
from uuid import UUID

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.base import init_db, get_db_session
from src.database.companies import Company, create_company, get_company_by_ticker
from src.database.documents import Document, DocumentType, get_documents_by_filing
from src.database.filings import Filing, get_filings_by_company
from src.database.financial_concepts import FinancialConcept
from src.database.financial_values import FinancialValue
from src.database.generated_content import GeneratedContent, get_generated_content_by_hash
from src.database.model_configs import ModelConfig, create_model_config, get_model_config_by_content_hash
from src.database.prompts import Prompt, create_prompt, get_prompt_by_content_hash
from src.database.ratings import Rating, create_rating
from src.ingestion.edgar_db.accessors import edgar_login
from src.ingestion.ingestion_helpers import ingest_company, ingest_filing, ingest_filing_documents
from src.llm.client import ModelConfig as LLMModelConfig, init_client, get_generate_response
from src.utils.config import settings
from src.utils.logging import configure_logging, get_logger

# Configure logging
configure_logging(
    log_level=settings.logging.level,
    json_format=settings.logging.json_format
)

logger = get_logger(__name__)
console = Console()

# Global database session
session = None

def init_session():
    """Initialize database session."""
    global session
    if session is None:
        init_db(settings.database.url)
        session = get_db_session()
    return session


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, verbose):
    """Symbology CLI - Administrative tool for SEC EDGAR data and AI insights."""
    ctx.ensure_object(dict)

    if verbose:
        configure_logging(log_level="DEBUG", json_format=False)

    # Don't initialize database here - do it lazily when needed
# ==================== INGESTION COMMANDS ====================

@cli.group()
def ingest():
    """Data ingestion commands for SEC EDGAR filings."""
    pass


@ingest.command()
@click.argument('ticker')
@click.argument('form_type', default='10-K')
@click.argument('years', default='2023')
@click.option('--force', is_flag=True, help='Force re-ingestion even if data exists')
def company(ticker: str, form_type: str, years: str, force: bool):
    """
    Ingest SEC filings for a company.

    TICKER: Company ticker symbol (e.g., AAPL)
    FORM_TYPE: SEC form type (10-K, 10-Q, 8-K)
    YEARS: Comma-separated years (e.g., 2022,2023) or single year
    """
    ticker = ticker.upper()
    years_list = [int(y.strip()) for y in years.split(',')]

    console.print(f"[bold blue]Ingesting {form_type} filings for {ticker}[/bold blue]")
    console.print(f"Years: {', '.join(map(str, years_list))}")

    try:
        # Initialize EDGAR connection
        edgar_login()

        # Create or get company
        company_obj = get_company_by_ticker(ticker)
        if not company_obj:
            console.print(f"[yellow]Creating new company record for {ticker}[/yellow]")
            company_obj = ingest_company(ticker)
        else:
            console.print(f"[green]Found existing company: {company_obj.name}[/green]")

        # Ingest filings for each year
        for year in years_list:
            console.print(f"\n[bold]Processing {year}[/bold]")

            # Check if filing already exists
            existing_filings = get_filings_by_company(company_obj.id, form_type=form_type, year=year)
            if existing_filings and not force:
                console.print(f"[yellow]Filing for {year} already exists. Use --force to re-ingest.[/yellow]")
                continue

            # Ingest filing
            filing = ingest_filing(company_obj.id, form_type, year)
            if filing:
                console.print(f"[green]✓[/green] Filing ingested: {filing.accession_number}")

                # Ingest documents
                documents = ingest_filing_documents(filing.id)
                console.print(f"[green]✓[/green] {len(documents)} documents ingested")
            else:
                console.print(f"[red]✗[/red] Failed to ingest filing for {year}")

    except Exception as e:
        console.print(f"[red]Error during ingestion: {e}[/red]")
        logger.exception("Ingestion failed")
        sys.exit(1)


# ==================== PROMPT COMMANDS ====================

@cli.group()
def create():
    """Create new resources (prompts, model configs, content)."""
    pass


@create.command()
@click.argument('name')
@click.option('--description', '-d', help='Prompt description')
@click.option('--role', type=click.Choice(['system', 'user', 'assistant']), default='system', help='Prompt role')
@click.option('--examples-dir', help='Directory containing example files to append')
def prompt(name: str, description: Optional[str], role: str, examples_dir: Optional[str]):
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
            content += "\n\n# Examples\n"
            for example_file in example_files:
                console.print(f"[blue]Adding example: {example_file.name}[/blue]")
                content += f"\n## {example_file.stem}\n"
                content += example_file.read_text().strip() + "\n"

    # Create prompt in database
    try:
        prompt_data = {
            'name': name,
            'description': description or f"Prompt: {name}",
            'role': role,
            'content': content
        }
        prompt_obj = create_prompt(prompt_data)

        console.print(f"[green]✓[/green] Prompt created: {name}")
        console.print(f"[blue]Hash:[/blue] {prompt_obj.get_short_hash()}")
        console.print(f"[blue]ID:[/blue] {prompt_obj.id}")

    except Exception as e:
        console.print(f"[red]Error creating prompt: {e}[/red]")
        logger.exception("Failed to create prompt")
        sys.exit(1)


@create.command('model-config')
@click.argument('model_name')
@click.option('--temperature', type=float, help='Model temperature')
@click.option('--num-ctx', type=int, help='Context window size')
@click.option('--top-k', type=int, help='Top-k sampling')
@click.option('--top-p', type=float, help='Top-p sampling')
@click.option('--num-gpu', type=int, help='Number of GPUs to use')
@click.option('--options', help='JSON string of additional options')
def model_config(model_name: str, temperature: Optional[float], num_ctx: Optional[int],
                top_k: Optional[int], top_p: Optional[float], num_gpu: Optional[int],
                options: Optional[str]):
    """
    Create a new model configuration.

    MODEL_NAME: Name of the model (e.g., qwen3:14b, gpt-4o)
    """

    # Build options dictionary
    config_options = {}

    if temperature is not None:
        config_options['temperature'] = temperature
    if num_ctx is not None:
        config_options['num_ctx'] = num_ctx
    if top_k is not None:
        config_options['top_k'] = top_k
    if top_p is not None:
        config_options['top_p'] = top_p
    if num_gpu is not None:
        config_options['num_gpu'] = num_gpu

    # Parse additional options if provided
    if options:
        try:
            additional_options = json.loads(options)
            config_options.update(additional_options)
        except json.JSONDecodeError as e:
            console.print(f"[red]Error parsing options JSON: {e}[/red]")
            sys.exit(1)

    # Use default options if none provided
    if not config_options:
        config_options = {
            'temperature': 0.7,
            'num_ctx': 4096,
            'top_k': 40
        }
        console.print("[yellow]No options provided, using defaults[/yellow]")

    try:
        model_config_data = {
            'name': model_name,
            'options_json': json.dumps(config_options)
        }
        model_config_obj = create_model_config(model_config_data)

        console.print(f"[green]✓[/green] Model config created: {model_name}")
        console.print(f"[blue]Hash:[/blue] {model_config_obj.get_short_hash()}")
        console.print(f"[blue]ID:[/blue] {model_config_obj.id}")
        console.print(f"[blue]Options:[/blue] {json.dumps(config_options, indent=2)}")

    except Exception as e:
        console.print(f"[red]Error creating model config: {e}[/red]")
        logger.exception("Failed to create model config")
        sys.exit(1)


@create.command('generated-content')
@click.argument('prompt_hash')
@click.argument('model_config_hash')
@click.argument('source_hashes', nargs=-1)
@click.option('--company', help='Company ticker (optional)')
@click.option('--document-type', type=click.Choice(['MDA', 'RISK_FACTORS', 'BUSINESS', 'FINANCIALS']),
              help='Document type for aggregations')
def generated_content(prompt_hash: str, model_config_hash: str, source_hashes: Tuple[str],
                     company: Optional[str], document_type: Optional[str]):
    """
    Generate AI content from prompt, model config, and source materials.

    PROMPT_HASH: Hash of the system prompt to use
    MODEL_CONFIG_HASH: Hash of the model configuration
    SOURCE_HASHES: One or more hashes of source documents or content
    """

    try:
        # Get prompt
        prompt_obj = get_prompt_by_content_hash(prompt_hash)
        if not prompt_obj:
            console.print(f"[red]Error: Prompt with hash {prompt_hash} not found[/red]")
            sys.exit(1)

        # Get model config
        model_config_obj = get_model_config_by_content_hash(model_config_hash)
        if not model_config_obj:
            console.print(f"[red]Error: Model config with hash {model_config_hash} not found[/red]")
            sys.exit(1)

        # TODO: Implement source content retrieval and LLM generation
        # This would involve:
        # 1. Retrieving source documents/content by their hashes
        # 2. Building the user prompt from source materials
        # 3. Calling the LLM with system prompt + user prompt
        # 4. Creating GeneratedContent record with results

        console.print("[yellow]Generated content creation not yet implemented[/yellow]")
        console.print(f"Would generate content using:")
        console.print(f"  Prompt: {prompt_obj.name}")
        console.print(f"  Model: {model_config_obj.name}")
        console.print(f"  Sources: {', '.join(source_hashes)}")

    except Exception as e:
        console.print(f"[red]Error creating generated content: {e}[/red]")
        logger.exception("Failed to create generated content")
        sys.exit(1)


# ==================== GET COMMANDS ====================

@cli.group()
def get():
    """Retrieve and display resources."""
    pass


@get.command()
@click.argument('hash_or_name')
def prompt(hash_or_name: str):
    """Get and display a prompt by hash or name."""

    try:
        # Try to get by hash first, then by name
        prompt_obj = get_prompt_by_content_hash(hash_or_name)
        if not prompt_obj:
            # Try by name
            session = init_session()
            prompt_obj = session.query(Prompt).filter(Prompt.name == hash_or_name).first()

        if not prompt_obj:
            console.print(f"[red]Error: Prompt '{hash_or_name}' not found[/red]")
            sys.exit(1)

        # Display prompt info
        panel_title = f"Prompt: {prompt_obj.name}"
        content_preview = prompt_obj.content[:200] + "..." if len(prompt_obj.content) > 200 else prompt_obj.content

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


@get.command('model-config')
@click.argument('hash_or_id')
def model_config_get(hash_or_id: str):
    """Get and display a model configuration by hash or ID."""

    try:
        # Try to get by hash first, then by ID
        model_config_obj = get_model_config_by_content_hash(hash_or_id)
        if not model_config_obj:
            # Try by ID
            session = init_session()
            try:
                uuid_obj = UUID(hash_or_id)
                model_config_obj = session.query(ModelConfig).filter(ModelConfig.id == uuid_obj).first()
            except ValueError:
                pass

        if not model_config_obj:
            console.print(f"[red]Error: Model config '{hash_or_id}' not found[/red]")
            sys.exit(1)

        # Display model config info
        panel_title = f"Model Config: {model_config_obj.name}"

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_row("[bold blue]ID:[/bold blue]", str(model_config_obj.id))
        table.add_row("[bold blue]Name:[/bold blue]", model_config_obj.name)
        table.add_row("[bold blue]Hash:[/bold blue]", model_config_obj.get_short_hash())
        table.add_row("[bold blue]Created:[/bold blue]", model_config_obj.created_at.isoformat() if model_config_obj.created_at else "Unknown")

        console.print(Panel(table, title=panel_title))
        console.print("\n[bold]Options:[/bold]")
        options = json.loads(model_config_obj.options_json)
        console.print(Panel(json.dumps(options, indent=2), title="Model Options"))

    except Exception as e:
        console.print(f"[red]Error retrieving model config: {e}[/red]")
        logger.exception("Failed to get model config")
        sys.exit(1)


@get.command()
@click.argument('hash')
def content(hash: str):
    """Get and display generated content by hash."""

    try:
        content_obj = get_generated_content_by_hash(hash)
        if not content_obj:
            console.print(f"[red]Error: Generated content with hash {hash} not found[/red]")
            sys.exit(1)

        # Display content info
        panel_title = f"Generated Content"

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_row("[bold blue]ID:[/bold blue]", str(content_obj.id))
        table.add_row("[bold blue]Hash:[/bold blue]", content_obj.get_short_hash())
        table.add_row("[bold blue]Company:[/bold blue]", content_obj.company.ticker if content_obj.company else "None")
        table.add_row("[bold blue]Document Type:[/bold blue]", content_obj.document_type.value if content_obj.document_type else "None")
        table.add_row("[bold blue]Source Type:[/bold blue]", content_obj.source_type.value)
        table.add_row("[bold blue]Created:[/bold blue]", content_obj.created_at.isoformat() if content_obj.created_at else "Unknown")

        console.print(Panel(table, title=panel_title))
        console.print("\n[bold]Content:[/bold]")
        console.print(Panel(content_obj.content, title="Generated Content"))

    except Exception as e:
        console.print(f"[red]Error retrieving content: {e}[/red]")
        logger.exception("Failed to get content")
        sys.exit(1)


# ==================== RATING COMMANDS ====================

@cli.command()
@click.argument('content_hash')
@click.argument('rating', type=int)
@click.argument('message')
def rate(content_hash: str, rating: int, message: str):
    """
    Rate generated content.

    CONTENT_HASH: Hash of the generated content to rate
    RATING: Rating value (1-5)
    MESSAGE: Rating message/feedback
    """

    if not (1 <= rating <= 5):
        console.print("[red]Error: Rating must be between 1 and 5[/red]")
        sys.exit(1)

    try:
        # Get the content to rate
        content_obj = get_generated_content_by_hash(content_hash)
        if not content_obj:
            console.print(f"[red]Error: Generated content with hash {content_hash} not found[/red]")
            sys.exit(1)

        # Create rating
        rating_data = {
            'generated_content_id': content_obj.id,
            'content_score': rating,  # Using content_score instead of rating
            'comment': message
        }
        rating_obj = create_rating(rating_data)

        console.print(f"[green]✓[/green] Rating created for content {content_hash[:8]}...")
        console.print(f"[blue]Rating:[/blue] {rating}/5")
        console.print(f"[blue]Message:[/blue] {message}")

    except Exception as e:
        console.print(f"[red]Error creating rating: {e}[/red]")
        logger.exception("Failed to create rating")
        sys.exit(1)


# ==================== LIST COMMANDS ====================

@cli.group()
def list():
    """List resources."""
    pass


@list.command()
@click.option('--limit', default=10, help='Maximum number of items to show')
def prompts(limit: int):
    """List all prompts."""

    try:
        session = init_session()
        prompts = session.query(Prompt).limit(limit).all()

        if not prompts:
            console.print("[yellow]No prompts found[/yellow]")
            return

        table = Table(title="Prompts")
        table.add_column("Name", style="cyan")
        table.add_column("Role", style="magenta")
        table.add_column("Hash", style="green")
        table.add_column("Description", style="white")

        for prompt in prompts:
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


@list.command('model-configs')
@click.option('--limit', default=10, help='Maximum number of items to show')
def model_configs(limit: int):
    """List all model configurations."""

    try:
        session = init_session()
        configs = session.query(ModelConfig).limit(limit).all()

        if not configs:
            console.print("[yellow]No model configs found[/yellow]")
            return

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
                config.name,
                config.get_short_hash()[:8],
                config.created_at.strftime("%Y-%m-%d") if config.created_at else "Unknown",
                options_str
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error listing model configs: {e}[/red]")
        logger.exception("Failed to list model configs")


if __name__ == '__main__':
    cli()
