"""CLI commands for generated content management."""

import sys
from typing import List, Optional, Tuple

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.database.base import get_db_session
from src.database.companies import get_company_by_ticker
from src.database.documents import Document, DocumentType, get_document_by_content_hash
import src.database.generated_content as db
from src.database.model_configs import get_model_config_by_content_hash
from src.database.prompts import get_prompt_by_content_hash, create_prompt, PromptRole
from src.llm.client import get_generate_response
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
@click.option('--document-type',
              type=click.Choice([dt.name for dt in DocumentType]),
              help='Document type for the generated content')
def create_generated_content(prompt: str, model_config: str, source_documents: Tuple[str],
                           source_content: Tuple[str], additional_content: Optional[str],
                           company: Optional[str], document_type: Optional[str]):
    """
    Generate AI content from prompt, model config, and source materials.
    """

    try:
        init_session()

        # Validate that we have at least one source
        total_sources = len(source_documents) + len(source_content) + (1 if additional_content else 0)
        if total_sources == 0:
            console.print("[red]Error: At least one source must be provided (--source-documents, --source-content, or --additional-content)[/red]")
            sys.exit(1)

        # Get prompt
        prompt_obj = get_prompt_by_content_hash(prompt)
        if not prompt_obj:
            console.print(f"[red]Error: Prompt with hash {prompt} not found[/red]")
            sys.exit(1)

        # Get model config
        model_config_obj = get_model_config_by_content_hash(model_config)
        if not model_config_obj:
            console.print(f"[red]Error: Model config with hash {model_config} not found[/red]")
            sys.exit(1)

        # Validate source documents exist
        source_docs: List[Document] = []
        for doc_hash in source_documents:
            doc = get_document_by_content_hash(doc_hash)
            if not doc:
                console.print(f"[red]Error: Source document with hash {doc_hash} not found[/red]")
                sys.exit(1)
            source_docs.append(doc)

        # Validate source content exists (similar to documents, but for generated content)
        source_contents: List[db.GeneratedContent] = []
        for content_hash in source_content:
            content_obj = db.get_generated_content_by_hash(content_hash)
            if not content_obj:
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
                    console.print("[red]Error: No content provided via stdin[/red]")
                    sys.exit(1)
            else:
                additional_text = additional_content

        # Build the user prompt from source materials
        console.print("[blue]Building user prompt from source materials...[/blue]")
        user_prompt = format_user_prompt_content(
            source_documents=source_docs if source_docs else None,
            source_content=source_contents if source_contents else None,
            additional_text=additional_text
        )

        console.print(f"[blue]User prompt assembled: {len(user_prompt):,} characters[/blue]")
        # todo: save the user prompt to the database

        # Call the LLM with system prompt + user prompt
        console.print(f"[blue]Generating content using model {model_config_obj.model}...[/blue]")
        try:
            response = get_generate_response(
                model_config=model_config_obj,
                system_prompt=prompt_obj.content,
                user_prompt=user_prompt
            )

            console.print(f"[green]✓ Content generated successfully[/green]")
            console.print(f"[blue]Response length: {len(response.response):,} characters[/blue]")

            # Save user prompt to database
            console.print("[blue]Saving user prompt to database...[/blue]")
            user_prompt_obj, was_created = create_prompt({
                'name': f"User prompt for {prompt_obj.name}",
                'description': f"Generated user prompt combining {len(source_docs)} documents, {len(source_contents)} content items" + (", and additional text" if additional_text else ""),
                'role': PromptRole.USER,
                'content': user_prompt
            })

            if was_created:
                console.print(f"[green]✓ User prompt saved with hash {user_prompt_obj.get_short_hash()}[/green]")
            else:
                console.print(f"[yellow]User prompt already exists with hash {user_prompt_obj.get_short_hash()}[/yellow]")

            # Get company object if specified
            company_obj = None
            if company:
                company_obj = get_company_by_ticker(company.upper())
                if not company_obj:
                    console.print(f"[yellow]Warning: Company '{company}' not found in database[/yellow]")

            # Determine source type and document type
            if source_docs and source_contents:
                source_type = db.ContentSourceType.BOTH
            elif source_contents:
                source_type = db.ContentSourceType.GENERATED_CONTENT
            else:
                source_type = db.ContentSourceType.DOCUMENTS

            doc_type_enum = None
            if document_type:
                doc_type_enum = DocumentType[document_type]

            # Create GeneratedContent record
            console.print("[blue]Saving generated content to database...[/blue]")
            generated_content_data = {
                'content': response.response,
                'company_id': company_obj.id if company_obj else None,
                'document_type': doc_type_enum,
                'source_type': source_type,
                'total_duration': response.total_duration / 1e9 if hasattr(response, 'total_duration') else None,
                'model_config_id': model_config_obj.id,
                'system_prompt_id': prompt_obj.id,
                'user_prompt_id': user_prompt_obj.id
            }

            generated_content_obj = db.create_generated_content(generated_content_data)

            # Associate source documents and content with the generated content
            session = get_db_session()
            if source_docs:
                generated_content_obj.source_documents.extend(source_docs)
            if source_contents:
                generated_content_obj.source_content.extend(source_contents)
            session.commit()

            console.print(f"[green]✓ Generated content saved with hash {generated_content_obj.get_short_hash()}[/green]")
            console.print("\n[bold]Generated Content:[/bold]")
            console.print(Panel(response.response[:1000] + ("..." if len(response.response) > 1000 else ""),
                               title="Generated Content Preview"))

        except Exception as e:
            console.print(f"[red]Error generating content: {e}[/red]")
            logger.exception("Failed to generate content")
            sys.exit(1)

        console.print("\nGeneration details:")
        console.print(f"  Prompt: {prompt_obj.name}")
        console.print(f"  Model: {model_config_obj.model}")
        console.print(f"  Source Documents: {[doc.get_short_hash() for doc in source_docs]}")
        console.print(f"  Source Content: {[content.get_short_hash() for content in source_contents]}")
        if additional_text:
            console.print(f"  Additional Content: {len(additional_text)} characters")
        if company:
            console.print(f"  Company: {company}")
        if document_type:
            console.print(f"  Document Type: {document_type}")

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
        content_obj = db.get_generated_content_by_hash(hash)
        if not content_obj:
            console.print(f"[red]Error: Generated content with hash {hash} not found[/red]")
            sys.exit(1)

        # Display content info
        panel_title = "Generated Content"

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
@click.option('--document-type',
              type=click.Choice([dt.name for dt in DocumentType]),
              help='Filter by document type')
@click.option('--limit', default=10, help='Maximum number of items to show')
def list_generated_content(company: str, document_type: str, limit: int):
    """List generated content in the database."""

    try:
        session = init_session()

        query = session.query(db.GeneratedContent)

        # Apply filters
        if company:
            company_upper = company.upper()
            query = query.join(db.GeneratedContent.company).filter(
                db.GeneratedContent.company.has(ticker=company_upper)
            )

        if document_type:
            doc_type_enum = DocumentType[document_type]
            query = query.filter(db.GeneratedContent.document_type == doc_type_enum)

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

        search_query = session.query(db.GeneratedContent).filter(
            db.GeneratedContent.content.ilike(f"%{query}%")
        )

        # Apply company filter if specified
        if company:
            company_upper = company.upper()
            search_query = search_query.join(db.GeneratedContent.company).filter(
                db.GeneratedContent.company.has(ticker=company_upper)
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
