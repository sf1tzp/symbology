"""CLI commands for document management."""

import sys

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.database.base import get_db_session
from src.database.documents import Document, DocumentType, get_documents_by_filing
from src.database.filings import Filing
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
def documents():
    """Document management commands."""
    pass


@documents.command('list')
@click.argument('accession_number')
@click.option('--document-type', type=click.Choice(['MDA', 'RISK_FACTORS', 'BUSINESS', 'FINANCIALS']),
              help='Filter by document type')
@click.option('--limit', default=20, help='Maximum number of documents to show')
def list_documents(accession_number: str, document_type: str, limit: int):
    """List documents for a specific filing."""

    try:
        session = init_session()

        # Get filing
        filing = session.query(Filing).filter(Filing.accession_number == accession_number).first()
        if not filing:
            console.print(f"[red]Error: Filing with accession number '{accession_number}' not found[/red]")
            sys.exit(1)

        # Get documents
        documents_list = get_documents_by_filing(filing.id)

        # Filter by document type if specified
        if document_type:
            doc_type_enum = DocumentType(document_type)
            documents_list = [doc for doc in documents_list if doc.document_type == doc_type_enum]

        # Apply limit
        documents_list = documents_list[:limit]

        if not documents_list:
            console.print(f"[yellow]No documents found for filing {accession_number}[/yellow]")
            return

        console.print(f"[blue]Filing:[/blue] {filing.form_type} - {filing.company.name if filing.company else 'Unknown'}")

        table = Table(title=f"Documents ({len(documents_list)} found)")
        table.add_column("Type", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Content Hash", style="green")
        table.add_column("Content Size", style="yellow")

        for doc in documents_list:
            content_size = f"{len(doc.content):,} chars" if doc.content else "No content"
            title = doc.title[:50] + "..." if doc.title and len(doc.title) > 50 else (doc.title or "Unknown")

            table.add_row(
                doc.document_type.value if doc.document_type else "Unknown",
                title,
                doc.get_short_hash()[:8] if hasattr(doc, 'get_short_hash') else "N/A",
                content_size
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error listing documents: {e}[/red]")
        logger.exception("Failed to list documents")
        sys.exit(1)


@documents.command('get')
@click.argument('content_hash')
@click.option('--show-content', is_flag=True, help='Display the full document content')
def get_document(content_hash: str, show_content: bool):
    """Get detailed information about a specific document by its content hash."""

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
            console.print(f"[red]Error: Document with hash '{content_hash}' not found[/red]")
            sys.exit(1)

        # Display document info
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
        console.print(f"[red]Error retrieving document: {e}[/red]")
        logger.exception("Failed to get document")
        sys.exit(1)


@documents.command('search')
@click.argument('query')
@click.option('--document-type', type=click.Choice(['MDA', 'RISK_FACTORS', 'BUSINESS', 'FINANCIALS']),
              help='Filter by document type')
@click.option('--limit', default=10, help='Maximum number of results to show')
def search_documents(query: str, document_type: str, limit: int):
    """Search documents by title or content."""

    try:
        session = init_session()

        # Build query
        search_query = session.query(Document)

        # Add text search (case-insensitive)
        search_query = search_query.filter(
            Document.title.ilike(f"%{query}%") |
            Document.content.ilike(f"%{query}%")
        )

        # Filter by document type if specified
        if document_type:
            doc_type_enum = DocumentType(document_type)
            search_query = search_query.filter(Document.document_type == doc_type_enum)

        documents_list = search_query.limit(limit).all()

        if not documents_list:
            console.print(f"[yellow]No documents found matching '{query}'[/yellow]")
            return

        table = Table(title=f"Search Results for '{query}' ({len(documents_list)} found)")
        table.add_column("Type", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Company", style="magenta")
        table.add_column("Filing", style="yellow")
        table.add_column("Hash", style="green")

        for doc in documents_list:
            title = doc.title[:40] + "..." if doc.title and len(doc.title) > 40 else (doc.title or "Unknown")
            company_name = doc.filing.company.name[:20] + "..." if doc.filing and doc.filing.company and len(doc.filing.company.name) > 20 else (doc.filing.company.name if doc.filing and doc.filing.company else "Unknown")

            table.add_row(
                doc.document_type.value if doc.document_type else "Unknown",
                title,
                company_name,
                doc.filing.accession_number if doc.filing else "Unknown",
                doc.content_hash[:8] if doc.content_hash else "N/A"
            )

        console.print(table)

        if len(documents_list) == limit:
            console.print(f"\n[yellow]Showing first {limit} results. Use --limit to see more.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error searching documents: {e}[/red]")
        logger.exception("Failed to search documents")
        sys.exit(1)
