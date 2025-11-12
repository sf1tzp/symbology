"""CLI commands for generated content management."""

import json
import logging
import sys
from typing import List, Optional, Tuple

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from src.database.base import get_db_session
from src.database.companies import get_company_by_ticker
from src.database.documents import Document, get_document_by_content_hash
import src.database.generated_content as db
from src.database.model_configs import get_model_config_by_content_hash
from src.database.prompts import create_prompt, get_prompt_by_content_hash, PromptRole
from src.llm.client import get_generate_response, remove_thinking_tags
from src.llm.prompts import format_user_prompt_content
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
@click.option('--prompt', required=True, help='Hash of the system prompt to use')
@click.option('--model-config', required=True, help='Hash of the model configuration')
@click.option('--source-documents', multiple=True, help='Content hashes of source documents')
@click.option('--source-content', multiple=True, help='Content hashes of other generated content to use as source')
@click.option('--additional-content', help='Additional text content to include (or "-" to read from stdin)')
@click.option('--company', help='Company ticker (optional)')
@click.option('--description', help='Optional description of the generated content')
@click.option('-o', '--output', type=click.Choice(['table', 'json']), default='table', help='Output format')
def create_generated_content(prompt: str, model_config: str, source_documents: Tuple[str],
                           source_content: Tuple[str], additional_content: Optional[str],
                           company: Optional[str], description: Optional[str], output: str):
    """
    Generate AI content from prompt, model config, and source materials.
    """
    # For JSON output, temporarily suppress INFO level logs to avoid interference with JSON parsing
    if output == 'json':
        # Get all loggers and set their level to WARNING temporarily
        original_levels = {}
        logger_names = [
            'src.database.generated_content',
            'src.database.prompts',
            'src.database.model_configs',
            'src.database.documents',
            'src.database.companies',
            'src.llm.client',
            'httpcore',
            'httpx',
            'ollama',
            'transformers',
            'huggingface_hub',
            'urllib3.connectionpool'
        ]
        for logger_name in logger_names:
            db_logger = logging.getLogger(logger_name)
            original_levels[logger_name] = db_logger.level
            db_logger.setLevel(logging.ERROR)

    try:
        init_session()

        # Validate that we have at least one source
        total_sources = len(source_documents) + len(source_content) + (1 if additional_content else 0)
        if total_sources == 0:
            if output == 'json':
                error_data = {"error": "At least one source must be provided (--source-documents, --source-content, or --additional-content)"}
                click.echo(json.dumps(error_data))
            else:
                console.print("[red]Error: At least one source must be provided (--source-documents, --source-content, or --additional-content)[/red]")
            sys.exit(1)

        # Get prompt
        prompt_obj = get_prompt_by_content_hash(prompt)
        if not prompt_obj:
            if output == 'json':
                error_data = {"error": f"Prompt with hash {prompt} not found"}
                click.echo(json.dumps(error_data))
            else:
                console.print(f"[red]Error: Prompt with hash {prompt} not found[/red]")
            sys.exit(1)

        # Get model config
        model_config_obj = get_model_config_by_content_hash(model_config)
        if not model_config_obj:
            if output == 'json':
                error_data = {"error": f"Model config with hash {model_config} not found"}
                click.echo(json.dumps(error_data))
            else:
                console.print(f"[red]Error: Model config with hash {model_config} not found[/red]")
            sys.exit(1)

        # Validate source documents exist
        source_docs: List[Document] = []
        seen_doc_hashes = set()
        for doc_hash in source_documents:
            if doc_hash in seen_doc_hashes:
                continue  # Skip duplicates
            seen_doc_hashes.add(doc_hash)

            doc = get_document_by_content_hash(doc_hash)
            if not doc:
                if output == 'json':
                    error_data = {"error": f"Source document with hash {doc_hash} not found"}
                    click.echo(json.dumps(error_data))
                else:
                    console.print(f"[red]Error: Source document with hash {doc_hash} not found[/red]")
                sys.exit(1)
            source_docs.append(doc)

        # Validate source content exists (similar to documents, but for generated content)
        source_contents: List[db.GeneratedContent] = []
        seen_content_hashes = set()
        for content_hash in source_content:
            if content_hash in seen_content_hashes:
                continue  # Skip duplicates
            seen_content_hashes.add(content_hash)

            content_obj = db.get_generated_content_by_hash(content_hash)
            if not content_obj:
                if output == 'json':
                    error_data = {"error": f"Source content with hash {content_hash} not found"}
                    click.echo(json.dumps(error_data))
                else:
                    console.print(f"[red]Error: Source content with hash {content_hash} not found[/red]")
                sys.exit(1)
            source_contents.append(content_obj)

        # Handle additional content
        additional_text = None
        if additional_content:
            if additional_content == "-":
                # Read from stdin
                additional_text = sys.stdin.read().strip()
                if not additional_text:
                    if output == 'json':
                        error_data = {"error": "No content provided via stdin"}
                        click.echo(json.dumps(error_data))
                    else:
                        console.print("[red]Error: No content provided via stdin[/red]")
                    sys.exit(1)
            else:
                additional_text = additional_content

        # Build the user prompt from source materials
        if output != 'json':
            console.print("[blue]Building user prompt from source materials...[/blue]")
        user_prompt = format_user_prompt_content(
            source_documents=source_docs if source_docs else None,
            source_content=source_contents if source_contents else None,
            additional_text=additional_text
        )

        if output != 'json':
            console.print(f"[blue]User prompt assembled: {len(user_prompt):,} characters[/blue]")
        # todo: save the user prompt to the database

        # Call the LLM with system prompt + user prompt
        if output != 'json':
            console.print(f"[blue]Generating content using model {model_config_obj.model}...[/blue]")
        try:
            response, warning = get_generate_response(
                model_config=model_config_obj,
                system_prompt=prompt_obj.content,
                user_prompt=user_prompt
            )

            if output != 'json':
                console.print("[green]✓ Content generated successfully[/green]")
                console.print(f"[blue]Response length: {len(response.response):,} characters[/blue]")

            # Save user prompt to database
            if output != 'json':
                console.print("[blue]Saving user prompt to database...[/blue]")
            user_prompt_obj, was_created = create_prompt({
                'name': f"User prompt for {prompt_obj.name}",
                'description': f"Generated user prompt combining {len(source_docs)} documents, {len(source_contents)} content items" + (", and additional text" if additional_text else ""),
                'role': PromptRole.USER,
                'content': user_prompt
            })

            if output != 'json':
                if was_created:
                    console.print(f"[green]✓ User prompt saved with hash {user_prompt_obj.get_short_hash()}[/green]")
                else:
                    console.print(f"[yellow]User prompt already exists with hash {user_prompt_obj.get_short_hash()}[/yellow]")

            # Get company object if specified
            company_obj = None
            if company:
                company_obj = get_company_by_ticker(company.upper())
                if not company_obj and output != 'json':
                    console.print(f"[yellow]Warning: Company '{company}' not found in database[/yellow]")

            # Determine source type and document type
            if source_docs and source_contents:
                source_type = db.ContentSourceType.BOTH
            elif source_contents:
                source_type = db.ContentSourceType.GENERATED_CONTENT
            else:
                source_type = db.ContentSourceType.DOCUMENTS

            # No enum conversion needed anymore - description is just a string

            # Create GeneratedContent record
            if output != 'json':
                console.print("[blue]Saving generated content to database...[/blue]")
            generated_content_data = {
                'content': response.response,
                'company_id': company_obj.id if company_obj else None,
                'description': description,
                'source_type': source_type,
                'total_duration': response.total_duration / 1e9 if hasattr(response, 'total_duration') else None,
                'warning': warning,
                'model_config_id': model_config_obj.id,
                'system_prompt_id': prompt_obj.id,
                'user_prompt_id': user_prompt_obj.id
            }

            generated_content_obj, was_created = db.create_generated_content(generated_content_data)

            if output != 'json':
                if was_created:
                    console.print(f"[green]✓ Generated content saved with hash {generated_content_obj.get_short_hash()}[/green]")
                else:
                    console.print(f"[yellow]Generated content already exists with hash {generated_content_obj.get_short_hash()}[/yellow]")

            # Associate source documents and content with the generated content (only if newly created)
            if was_created:
                session = get_db_session()
                if source_docs:
                    generated_content_obj.source_documents.extend(source_docs)
                if source_contents:
                    generated_content_obj.source_content.extend(source_contents)
                session.commit()

            if output == 'json':
                # Prepare data for JSON output
                content_data = {
                    "id": str(generated_content_obj.id),
                    "content_hash": generated_content_obj.content_hash,
                    "short_hash": generated_content_obj.get_short_hash(),
                    "company": company_obj.ticker if company_obj else None,
                    "description": description,
                    "source_type": source_type.value,
                    "created_at": generated_content_obj.created_at.isoformat() if generated_content_obj.created_at else None,
                    "content_size": len(response.response),
                    "total_duration": response.total_duration / 1e9 if hasattr(response, 'total_duration') else None,
                    "warning": warning,
                    "model_config_hash": model_config_obj.get_short_hash(),
                    "system_prompt_hash": prompt_obj.get_short_hash(),
                    "user_prompt_hash": user_prompt_obj.get_short_hash(),
                    "source_document_hashes": [doc.get_short_hash() for doc in source_docs],
                    "source_content_hashes": [content.get_short_hash() for content in source_contents],
                    "additional_content_length": len(additional_text) if additional_text else 0
                }
                click.echo(json.dumps(content_data, indent=2))
            else:
                console.print(f"[green]✓ Generated content saved with hash {generated_content_obj.get_short_hash()}[/green]")
                console.print("\n[bold]Generated Content:[/bold]")
                console.print(Panel(response.response[:1000] + ("..." if len(response.response) > 1000 else ""),
                                   title="Generated Content Preview"))

        except Exception as e:
            if output == 'json':
                error_data = {"error": f"Error generating content: {e}"}
                click.echo(json.dumps(error_data))
            else:
                console.print(f"[red]Error generating content: {e}[/red]")
            logger.exception("Failed to generate content")
            sys.exit(1)

        if output != 'json':
            console.print("\nGeneration details:")
            console.print(f"  Prompt: {prompt_obj.name}")
            console.print(f"  Model: {model_config_obj.model}")
            console.print(f"  Source Documents: {[doc.get_short_hash() for doc in source_docs]}")
            console.print(f"  Source Content: {[content.get_short_hash() for content in source_contents]}")
            if additional_text:
                console.print(f"  Additional Content: {len(additional_text)} characters")
            if company:
                console.print(f"  Company: {company}")
            if description:
                console.print(f"  Description: {description}")

    except Exception as e:
        if output == 'json':
            error_data = {"error": str(e)}
            click.echo(json.dumps(error_data))
        else:
            console.print(f"[red]Error creating generated content: {e}[/red]")
        logger.exception("Failed to create generated content")
        sys.exit(1)
    finally:
        # Restore original log levels
        if output == 'json':
            for logger_name, original_level in original_levels.items():
                db_logger = logging.getLogger(logger_name)
                db_logger.setLevel(original_level)


@generated_content.command('get')
@click.argument('hash')
@click.option('--show-full', is_flag=True, help='Show full content instead of preview')
@click.option('-o', '--output', type=click.Choice(['table', 'json']), default='table', help='Output format')
def get_generated_content(hash: str, show_full: bool, output: str):
    """Get and display generated content by hash."""

    # For JSON output, temporarily suppress INFO level logs to avoid interference with JSON parsing
    if output == 'json':
        # Get all loggers and set their level to WARNING temporarily
        original_levels = {}
        for logger_name in ['src.database.generated_content']:
            db_logger = logging.getLogger(logger_name)
            original_levels[logger_name] = db_logger.level
            db_logger.setLevel(logging.WARNING)

    try:
        init_session()
        content_obj = db.get_generated_content_by_hash(hash)
        if not content_obj:
            if output == 'json':
                error_data = {"error": f"Generated content with hash {hash} not found"}
                click.echo(json.dumps(error_data))
            else:
                console.print(f"[red]Error: Generated content with hash {hash} not found[/red]")
            sys.exit(1)

        if output == 'json':
            # Prepare data for JSON output
            content_data = {
                "id": str(content_obj.id),
                "content_hash": content_obj.content_hash,
                "short_hash": content_obj.get_short_hash(),
                "company": content_obj.company.ticker if content_obj.company else None,
                "description": content_obj.description,
                "source_type": content_obj.source_type.value,
                "created_at": content_obj.created_at.isoformat() if content_obj.created_at else None,
                "content_size": len(content_obj.content) if content_obj.content else 0,
                "total_duration": content_obj.total_duration,
                "system_prompt": content_obj.system_prompt.get_short_hash(),
                "user_prompt": content_obj.user_prompt.get_short_hash(),
                "source_documents": [d.get_short_hash() for d in content_obj.source_documents],
                "source_content": [c.get_short_hash() for c in content_obj.source_content],
            }
            click.echo(json.dumps(content_data, indent=2))
        else:
            # Display content info
            panel_title = "Generated Content"

            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_row("[bold blue]ID:[/bold blue]", str(content_obj.id))
            table.add_row("[bold blue]Hash:[/bold blue]", content_obj.get_short_hash())
            table.add_row("[bold blue]Company:[/bold blue]", content_obj.company.ticker if content_obj.company else "None")
            table.add_row("[bold blue]Description:[/bold blue]", content_obj.description or "None")
            table.add_row("[bold blue]Source Type:[/bold blue]", content_obj.source_type.value)
            table.add_row("[bold blue]Created:[/bold blue]", content_obj.created_at.isoformat() if content_obj.created_at else "Unknown")

            console.print(Panel(table, title=panel_title))

            if content_obj.content:
                console.print("\n[bold]Content:[/bold]")
                if show_full or len(content_obj.content) <= 1000:
                    console.print(Panel(remove_thinking_tags(content_obj.content), title="Generated Content"))
                else:
                    preview = remove_thinking_tags(content_obj.content)[:1000] + "..."
                    console.print(Panel(preview, title="Generated Content (Preview)"))
                    console.print(f"\n[yellow]Content truncated. Use --show-full to see complete content ({len(content_obj.content):,} characters)[/yellow]")
            else:
                console.print("\n[yellow]No content available[/yellow]")

    except Exception as e:
        if output == 'json':
            error_data = {"error": str(e)}
            click.echo(json.dumps(error_data))
        else:
            console.print(f"[red]Error retrieving content: {e}[/red]")
        logger.exception("Failed to get content")
        sys.exit(1)
    finally:
        # Restore original log levels
        if output == 'json':
            for logger_name, original_level in original_levels.items():
                db_logger = logging.getLogger(logger_name)
                db_logger.setLevel(original_level)


@generated_content.command('list')
@click.option('--company', help='Filter by company ticker')
@click.option('--description', help='Filter by description (partial match)')
@click.option('--limit', default=10, help='Maximum number of items to show')
@click.option('-o', '--output', type=click.Choice(['table', 'json']), default='table', help='Output format')
def list_generated_content(company: str, description: str, limit: int, output: str):
    """List generated content in the database."""

    # For JSON output, temporarily suppress INFO level logs to avoid interference with JSON parsing
    if output == 'json':
        # Get all loggers and set their level to WARNING temporarily
        original_levels = {}
        for logger_name in ['src.database.generated_content']:
            db_logger = logging.getLogger(logger_name)
            original_levels[logger_name] = db_logger.level
            db_logger.setLevel(logging.WARNING)

    try:
        session = init_session()

        query = session.query(db.GeneratedContent)

        # Apply filters
        if company:
            company_upper = company.upper()
            query = query.join(db.GeneratedContent.company).filter(
                db.GeneratedContent.company.has(ticker=company_upper)
            )

        if description:
            query = query.filter(db.GeneratedContent.description.ilike(f"%{description}%"))

        content_list = query.limit(limit).all()

        if not content_list:
            if output == 'json':
                click.echo(json.dumps([]))
            else:
                console.print("[yellow]No generated content found[/yellow]")
            return

        if output == 'json':
            # Prepare data for JSON output
            content_data = []
            for content in content_list:
                content_size = len(content.content) if content.content else 0
                company_ticker = content.company.ticker if content.company else None

                item_data = {
                    "id": str(content.id),
                    "content_hash": content.content_hash,
                    "short_hash": content.get_short_hash(),
                    "company": company_ticker,
                    "source_type": content.source_type.value,
                    "created_at": content.created_at.isoformat() if content.created_at else None,
                    "content_size": content_size,
                    "total_duration": content.total_duration
                }
                content_data.append(item_data)

            click.echo(json.dumps(content_data, indent=2))
        else:
            table = Table(title=f"Generated Content ({len(content_list)} found)")
            table.add_column("Hash", style="green")
            table.add_column("Company", style="cyan")
            table.add_column("Source Type", style="yellow")
            table.add_column("Created", style="white")
            table.add_column("Content Size", style="blue")

            for content in content_list:
                content_size = f"{len(content.content):,} chars" if content.content else "No content"
                company_ticker = content.company.ticker if content.company else "None"

                table.add_row(
                    content.get_short_hash()[:8],
                    company_ticker,
                    content.source_type.value,
                    content.created_at.strftime("%Y-%m-%d") if content.created_at else "Unknown",
                    content_size
                )

            console.print(table)

            if len(content_list) == limit:
                console.print(f"\n[yellow]Showing first {limit} results. Use --limit to see more.[/yellow]")

    except Exception as e:
        if output == 'json':
            error_data = {"error": str(e)}
            click.echo(json.dumps(error_data))
        else:
            console.print(f"[red]Error listing generated content: {e}[/red]")
        logger.exception("Failed to list generated content")
        sys.exit(1)
    finally:
        # Restore original log levels
        if output == 'json':
            for logger_name, original_level in original_levels.items():
                db_logger = logging.getLogger(logger_name)
                db_logger.setLevel(original_level)
