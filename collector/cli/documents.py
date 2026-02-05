"""CLI commands for document management."""

import json
import logging
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from collector.database.base import get_db_session
from collector.database.documents import Document, DocumentType, get_documents_by_filing
from collector.database.filings import Filing
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
def documents():
    """Document management commands."""
    pass

# Generate document type choices from the enum
document_type_choices = [doc_type.value for doc_type in DocumentType]

@documents.command('list')
@click.argument('accession_number')
# @click.option('--ticker', prompt="Filter by company ticker")
@click.option('--document-type', type=click.Choice(document_type_choices),
              help='Filter by document type')
@click.option('--limit', default=20, help='Maximum number of documents to show')
@click.option('-o', '--output', type=click.Choice(['table', 'json']), default='table', help='Output format')
def list_documents(accession_number: str, document_type: str, limit: int, output: str):
    """List documents for a specific filing."""

    # For JSON output, temporarily suppress INFO level logs to avoid interference with JSON parsing
    if output == 'json':
        # Get all loggers and set their level to WARNING temporarily
        original_levels = {}
        for logger_name in ['src.database.documents']:
            db_logger = logging.getLogger(logger_name)
            original_levels[logger_name] = db_logger.level
            db_logger.setLevel(logging.WARNING)

    try:
        session = init_session()

        # Get filing
        filing = session.query(Filing).filter(Filing.accession_number == accession_number).first()
        if not filing:
            if output == 'json':
                error_data = {"error": f"Filing with accession number '{accession_number}' not found"}
                click.echo(json.dumps(error_data))
            else:
                console.print(f"[red]Error: Filing with accession number '{accession_number}' not found[/red]")
            sys.exit(1)

        # Get documents
        documents_list = get_documents_by_filing(filing.id)

        # Filter by document type if specified
        if document_type:
            dt = DocumentType(document_type)
            if dt:
                documents_list = [doc for doc in documents_list if doc.document_type == dt]

        # Apply limit
        documents_list = documents_list[:limit]

        if not documents_list:
            if output == 'json':
                click.echo(json.dumps([]))
            else:
                console.print(f"[yellow]No documents found for filing {accession_number}[/yellow]")
            return

        if output == 'json':
            # Prepare data for JSON output
            documents_data = []
            for doc in documents_list:
                content_size = len(doc.content) if doc.content else 0
                doc_data = {
                    "id": str(doc.id),
                    "title": doc.title,
                    "document_type": doc.document_type.value if doc.document_type else None,
                    "content_hash": doc.content_hash,
                    "short_hash": doc.get_short_hash(),
                    "content_size": content_size,
                    "filing_accession_number": accession_number
                }
                documents_data.append(doc_data)

            click.echo(json.dumps(documents_data, indent=2))
        else:
            # Original table output
            console.print(f"[blue]Filing:[/blue] {filing.form} - {filing.company.name if filing.company else 'Unknown'}")

            table = Table(title=f"Documents ({len(documents_list)} found)")
            table.add_column("Type", style="cyan")
            table.add_column("Title", style="white")
            table.add_column("Content Hash", style="green")
            table.add_column("Content Size", style="yellow")

            for doc in documents_list:
                content_size = f"{len(doc.content):,} chars" if doc.content else "No content"
                title = doc.title

                table.add_row(
                    doc.document_type.value if doc.document_type else "Unknown",
                    title,
                    doc.get_short_hash(),
                    content_size
                )

            console.print(table)

    except Exception as e:
        if output == 'json':
            error_data = {"error": str(e)}
            click.echo(json.dumps(error_data))
        else:
            console.print(f"[red]Error listing documents: {e}[/red]")
        logger.exception("Failed to list documents")
        sys.exit(1)
    finally:
        # Restore original log levels
        if output == 'json':
            for logger_name, original_level in original_levels.items():
                db_logger = logging.getLogger(logger_name)
                db_logger.setLevel(original_level)


@documents.command('get')
@click.argument('content_hash')
@click.option('--show-content', is_flag=True, help='Display the full document content')
@click.option('-o', '--output', type=click.Choice(['table', 'json']), default='table', help='Output format')
def get_document(content_hash: str, show_content: bool, output: str):
    """Get detailed information about a specific document by its content hash."""

    # For JSON output, temporarily suppress INFO level logs to avoid interference with JSON parsing
    if output == 'json':
        # Get all loggers and set their level to WARNING temporarily
        original_levels = {}
        for logger_name in ['src.database.documents']:
            db_logger = logging.getLogger(logger_name)
            original_levels[logger_name] = db_logger.level
            db_logger.setLevel(logging.WARNING)

    try:
        session = init_session()

        # Try to find document by content hash (exact or prefix match)
        document = session.query(Document).filter(Document.content_hash == content_hash).first()

        if not document and len(content_hash) < 64:
            # Try prefix match for short hashes
            document = session.query(Document).filter(
                Document.content_hash.like(f"{content_hash}%")
            ).first()

        if not document:
            if output == 'json':
                error_data = {"error": f"Document with hash '{content_hash}' not found"}
                click.echo(json.dumps(error_data))
            else:
                console.print(f"[red]Error: Document with hash '{content_hash}' not found[/red]")
            sys.exit(1)

        if output == 'json':
            # Prepare data for JSON output
            document_data = {
                "id": str(document.id),
                "title": document.title,
                "document_type": document.document_type.value if document.document_type else None,
                "content_hash": document.content_hash,
                "short_hash": document.get_short_hash(),
                "filing_accession_number": document.filing.accession_number if document.filing else None,
                "company_name": document.filing.company.name if document.filing and document.filing.company else None,
                "content_size": len(document.content) if document.content else 0
            }

            # Include content if requested
            if show_content and document.content:
                document_data["content"] = document.content

            click.echo(json.dumps(document_data, indent=2))
        else:
            # Original table output
            panel_title = f"Document: {document.title or 'Untitled'}"

            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_row("[bold blue]ID:[/bold blue]", str(document.id))
            table.add_row("[bold blue]Title:[/bold blue]", document.title or "Unknown")
            table.add_row("[bold blue]Type:[/bold blue]", document.document_type.value if document.document_type else "Unknown")
            table.add_row("[bold blue]Hash:[/bold blue]", document.content_hash or "Unknown")
            table.add_row("[bold blue]Filing:[/bold blue]", document.filing.accession_number if document.filing else "Unknown")
            table.add_row("[bold blue]Company:[/bold blue]", document.filing.company.name if document.filing and document.filing.company else "Unknown")
            table.add_row("[bold blue]Content Size:[/bold blue]", f"{len(document.content):,} characters" if document.content else "No content")

            console.print(Panel(table, title=panel_title))

            if show_content and document.content:
                console.print("\n[bold]Content:[/bold]")
                content_preview = document.content[:2000] + "..." if len(document.content) > 2000 else document.content
                console.print(Panel(content_preview, title="Document Content"))
            elif document.content:
                console.print(f"\n[yellow]Use --show-content to display the full content ({len(document.content):,} characters)[/yellow]")

    except Exception as e:
        if output == 'json':
            error_data = {"error": str(e)}
            click.echo(json.dumps(error_data))
        else:
            console.print(f"[red]Error retrieving document: {e}[/red]")
        logger.exception("Failed to get document")
        sys.exit(1)
    finally:
        # Restore original log levels
        if output == 'json':
            for logger_name, original_level in original_levels.items():
                db_logger = logging.getLogger(logger_name)
                db_logger.setLevel(original_level)

