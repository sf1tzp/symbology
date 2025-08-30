"""CLI commands for generated content management."""

import sys
from typing import Optional, Tuple

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.database.base import get_db_session
from src.database.generated_content import GeneratedContent, get_generated_content_by_hash
from src.database.model_configs import get_model_config_by_content_hash
from src.database.prompts import get_prompt_by_content_hash
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
def generated_content():
    """Generated content management commands."""
    pass


@generated_content.command('create')
@click.argument('prompt_hash')
@click.argument('model_config_hash')
@click.argument('source_hashes', nargs=-1)
@click.option('--company', help='Company ticker (optional)')
@click.option('--document-type', type=click.Choice(['MDA', 'RISK_FACTORS', 'BUSINESS', 'FINANCIALS']),
              help='Document type for aggregations')
def create_generated_content(prompt_hash: str, model_config_hash: str, source_hashes: Tuple[str],
                           company: Optional[str], document_type: Optional[str]):
    """
    Generate AI content from prompt, model config, and source materials.

    PROMPT_HASH: Hash of the system prompt to use
    MODEL_CONFIG_HASH: Hash of the model configuration
    SOURCE_HASHES: One or more hashes of source documents or content
    """

    try:
        init_session()

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


@generated_content.command('get')
@click.argument('hash')
@click.option('--show-full', is_flag=True, help='Show full content instead of preview')
def get_generated_content(hash: str, show_full: bool):
    """Get and display generated content by hash."""

    try:
        init_session()
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

        if content_obj.content:
            console.print("\n[bold]Content:[/bold]")
            if show_full or len(content_obj.content) <= 1000:
                console.print(Panel(content_obj.content, title="Generated Content"))
            else:
                preview = content_obj.content[:1000] + "..."
                console.print(Panel(preview, title="Generated Content (Preview)"))
                console.print(f"\n[yellow]Content truncated. Use --show-full to see complete content ({len(content_obj.content):,} characters)[/yellow]")
        else:
            console.print("\n[yellow]No content available[/yellow]")

    except Exception as e:
        console.print(f"[red]Error retrieving content: {e}[/red]")
        logger.exception("Failed to get content")
        sys.exit(1)


@generated_content.command('list')
@click.option('--company', help='Filter by company ticker')
@click.option('--document-type', type=click.Choice(['MDA', 'RISK_FACTORS', 'BUSINESS', 'FINANCIALS']),
              help='Filter by document type')
@click.option('--limit', default=10, help='Maximum number of items to show')
def list_generated_content(company: str, document_type: str, limit: int):
    """List generated content in the database."""

    try:
        session = init_session()

        query = session.query(GeneratedContent)

        # Apply filters
        if company:
            company_upper = company.upper()
            query = query.join(GeneratedContent.company).filter(
                GeneratedContent.company.has(ticker=company_upper)
            )

        if document_type:
            from src.database.documents import DocumentType
            doc_type_enum = DocumentType(document_type)
            query = query.filter(GeneratedContent.document_type == doc_type_enum)

        content_list = query.limit(limit).all()

        if not content_list:
            console.print("[yellow]No generated content found[/yellow]")
            return

        table = Table(title=f"Generated Content ({len(content_list)} found)")
        table.add_column("Hash", style="green")
        table.add_column("Company", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Source Type", style="yellow")
        table.add_column("Created", style="white")
        table.add_column("Content Size", style="blue")

        for content in content_list:
            content_size = f"{len(content.content):,} chars" if content.content else "No content"
            company_ticker = content.company.ticker if content.company else "None"
            doc_type = content.document_type.value if content.document_type else "None"

            table.add_row(
                content.get_short_hash()[:8],
                company_ticker,
                doc_type,
                content.source_type.value,
                content.created_at.strftime("%Y-%m-%d") if content.created_at else "Unknown",
                content_size
            )

        console.print(table)

        if len(content_list) == limit:
            console.print(f"\n[yellow]Showing first {limit} results. Use --limit to see more.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error listing generated content: {e}[/red]")
        logger.exception("Failed to list generated content")
        sys.exit(1)


@generated_content.command('search')
@click.argument('query')
@click.option('--company', help='Filter by company ticker')
@click.option('--limit', default=10, help='Maximum number of results to show')
def search_generated_content(query: str, company: str, limit: int):
    """Search generated content by text content."""

    try:
        session = init_session()

        search_query = session.query(GeneratedContent).filter(
            GeneratedContent.content.ilike(f"%{query}%")
        )

        # Apply company filter if specified
        if company:
            company_upper = company.upper()
            search_query = search_query.join(GeneratedContent.company).filter(
                GeneratedContent.company.has(ticker=company_upper)
            )

        content_list = search_query.limit(limit).all()

        if not content_list:
            console.print(f"[yellow]No generated content found matching '{query}'[/yellow]")
            return

        table = Table(title=f"Search Results for '{query}' ({len(content_list)} found)")
        table.add_column("Hash", style="green")
        table.add_column("Company", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Preview", style="white")
        table.add_column("Created", style="yellow")

        for content in content_list:
            company_ticker = content.company.ticker if content.company else "None"
            doc_type = content.document_type.value if content.document_type else "None"

            # Create a preview that shows context around the search term
            if content.content:
                lower_content = content.content.lower()
                lower_query = query.lower()
                match_pos = lower_content.find(lower_query)
                if match_pos != -1:
                    start = max(0, match_pos - 50)
                    end = min(len(content.content), match_pos + len(query) + 50)
                    preview = "..." + content.content[start:end] + "..."
                    preview = preview.replace(query, f"[bold yellow]{query}[/bold yellow]")
                else:
                    preview = content.content[:100] + "..."
            else:
                preview = "No content"

            table.add_row(
                content.get_short_hash()[:8],
                company_ticker,
                doc_type,
                preview[:80] + "..." if len(preview) > 80 else preview,
                content.created_at.strftime("%Y-%m-%d") if content.created_at else "Unknown"
            )

        console.print(table)

        if len(content_list) == limit:
            console.print(f"\n[yellow]Showing first {limit} results. Use --limit to see more.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error searching generated content: {e}[/red]")
        logger.exception("Failed to search generated content")
        sys.exit(1)
