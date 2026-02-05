"""CLI commands for rating management."""

import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from collector.database.base import get_db_session
from collector.database.generated_content import get_generated_content_by_hash
from collector.database.ratings import create_rating, Rating
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
def ratings():
    """Rating management commands."""
    pass


@ratings.command('create')
@click.argument('content_hash')
@click.argument('rating', type=int)
@click.argument('message')
@click.option('--format-score', type=int, help='Format score (1-10)')
def create_rating_cmd(content_hash: str, rating: int, message: str, format_score: int):
    """
    Rate generated content.

    CONTENT_HASH: Hash of the generated content to rate
    RATING: Content score (1-10)
    MESSAGE: Rating message/feedback
    """

    if not (1 <= rating <= 10):
        console.print("[red]Error: Rating must be between 1 and 10[/red]")
        sys.exit(1)

    if format_score is not None and not (1 <= format_score <= 10):
        console.print("[red]Error: Format score must be between 1 and 10[/red]")
        sys.exit(1)

    try:
        init_session()

        # Get the content to rate
        content_obj = get_generated_content_by_hash(content_hash)
        if not content_obj:
            console.print(f"[red]Error: Generated content with hash {content_hash} not found[/red]")
            sys.exit(1)

        # Create rating
        rating_data = {
            'generated_content_id': content_obj.id,
            'content_score': rating,
            'comment': message
        }

        if format_score is not None:
            rating_data['format_score'] = format_score

        rating_obj = create_rating(rating_data)

        console.print(f"[green]✓[/green] Rating created for content {content_hash[:8]}...")
        console.print(f"[blue]Content Score:[/blue] {rating}/10")
        if format_score is not None:
            console.print(f"[blue]Format Score:[/blue] {format_score}/10")
        console.print(f"[blue]Message:[/blue] {message}")
        console.print(f"[blue]Rating ID:[/blue] {rating_obj.id}")

    except Exception as e:
        console.print(f"[red]Error creating rating: {e}[/red]")
        logger.exception("Failed to create rating")
        sys.exit(1)


@ratings.command('list')
@click.option('--content-hash', help='Filter by content hash')
@click.option('--min-score', type=int, help='Minimum content score filter')
@click.option('--max-score', type=int, help='Maximum content score filter')
@click.option('--limit', default=20, help='Maximum number of ratings to show')
def list_ratings(content_hash: str, min_score: int, max_score: int, limit: int):
    """List ratings in the database."""

    try:
        session = init_session()

        query = session.query(Rating)

        # Apply filters
        if content_hash:
            content_obj = get_generated_content_by_hash(content_hash)
            if not content_obj:
                console.print(f"[red]Error: Generated content with hash {content_hash} not found[/red]")
                sys.exit(1)
            query = query.filter(Rating.generated_content_id == content_obj.id)

        if min_score is not None:
            query = query.filter(Rating.content_score >= min_score)

        if max_score is not None:
            query = query.filter(Rating.content_score <= max_score)

        ratings_list = query.limit(limit).all()

        if not ratings_list:
            console.print("[yellow]No ratings found[/yellow]")
            return

        table = Table(title=f"Ratings ({len(ratings_list)} found)")
        table.add_column("Content Hash", style="green")
        table.add_column("Company", style="cyan")
        table.add_column("Content Score", style="yellow")
        table.add_column("Format Score", style="magenta")
        table.add_column("Comment", style="white")
        table.add_column("Tags", style="blue")

        for rating in ratings_list:
            content_hash_display = rating.generated_content.get_short_hash()[:8] if rating.generated_content else "Unknown"
            company_ticker = rating.generated_content.company.ticker if rating.generated_content and rating.generated_content.company else "None"
            comment_preview = rating.comment[:40] + "..." if rating.comment and len(rating.comment) > 40 else (rating.comment or "")
            tags_display = ", ".join(rating.tags[:3]) if rating.tags else ""
            if len(rating.tags) > 3:
                tags_display += "..."

            table.add_row(
                content_hash_display,
                company_ticker,
                str(rating.content_score) if rating.content_score is not None else "N/A",
                str(rating.format_score) if rating.format_score is not None else "N/A",
                comment_preview,
                tags_display
            )

        console.print(table)

        if len(ratings_list) == limit:
            console.print(f"\n[yellow]Showing first {limit} results. Use --limit to see more.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error listing ratings: {e}[/red]")
        logger.exception("Failed to list ratings")
        sys.exit(1)


@ratings.command('get')
@click.argument('rating_id')
def get_rating(rating_id: str):
    """Get detailed information about a specific rating."""

    try:
        session = init_session()

        # Try to parse as UUID
        from uuid import UUID
        try:
            uuid_obj = UUID(rating_id)
            rating = session.query(Rating).filter(Rating.id == uuid_obj).first()
        except ValueError:
            console.print(f"[red]Error: Invalid rating ID format '{rating_id}'[/red]")
            sys.exit(1)

        if not rating:
            console.print(f"[red]Error: Rating with ID '{rating_id}' not found[/red]")
            sys.exit(1)

        # Display rating info
        panel_title = "Rating Details"

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_row("[bold blue]ID:[/bold blue]", str(rating.id))
        table.add_row("[bold blue]Content Hash:[/bold blue]", rating.generated_content.get_short_hash() if rating.generated_content else "Unknown")
        table.add_row("[bold blue]Company:[/bold blue]", rating.generated_content.company.ticker if rating.generated_content and rating.generated_content.company else "None")
        table.add_row("[bold blue]Content Score:[/bold blue]", f"{rating.content_score}/10" if rating.content_score is not None else "N/A")
        table.add_row("[bold blue]Format Score:[/bold blue]", f"{rating.format_score}/10" if rating.format_score is not None else "N/A")
        table.add_row("[bold blue]Tags:[/bold blue]", ", ".join(rating.tags) if rating.tags else "None")

        console.print(Panel(table, title=panel_title))

        if rating.comment:
            console.print("\n[bold]Comment:[/bold]")
            console.print(Panel(rating.comment, title="Rating Comment"))

    except Exception as e:
        console.print(f"[red]Error retrieving rating: {e}[/red]")
        logger.exception("Failed to get rating")
        sys.exit(1)


@ratings.command('stats')
@click.option('--content-hash', help='Get stats for specific content')
def rating_stats(content_hash: str):
    """Show rating statistics."""

    try:
        session = init_session()

        query = session.query(Rating)

        # Filter by content if specified
        if content_hash:
            content_obj = get_generated_content_by_hash(content_hash)
            if not content_obj:
                console.print(f"[red]Error: Generated content with hash {content_hash} not found[/red]")
                sys.exit(1)
            query = query.filter(Rating.generated_content_id == content_obj.id)
            title_suffix = f" for Content {content_hash[:8]}..."
        else:
            title_suffix = " (All Content)"

        ratings_list = query.all()

        if not ratings_list:
            console.print(f"[yellow]No ratings found{title_suffix.lower()}[/yellow]")
            return

        # Calculate statistics
        content_scores = [r.content_score for r in ratings_list if r.content_score is not None]
        format_scores = [r.format_score for r in ratings_list if r.format_score is not None]

        stats_table = Table(title=f"Rating Statistics{title_suffix}")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Content Score", style="yellow")
        stats_table.add_column("Format Score", style="magenta")

        if content_scores:
            content_avg = sum(content_scores) / len(content_scores)
            content_min = min(content_scores)
            content_max = max(content_scores)
        else:
            content_avg = content_min = content_max = "N/A"

        if format_scores:
            format_avg = sum(format_scores) / len(format_scores)
            format_min = min(format_scores)
            format_max = max(format_scores)
        else:
            format_avg = format_min = format_max = "N/A"

        stats_table.add_row("Total Ratings", str(len(content_scores)), str(len(format_scores)))
        stats_table.add_row("Average", f"{content_avg:.1f}" if content_avg != "N/A" else "N/A", f"{format_avg:.1f}" if format_avg != "N/A" else "N/A")
        stats_table.add_row("Minimum", str(content_min), str(format_min))
        stats_table.add_row("Maximum", str(content_max), str(format_max))

        console.print(stats_table)

        # Show distribution
        if content_scores:
            console.print("\n[bold]Content Score Distribution:[/bold]")
            distribution = {}
            for score in content_scores:
                distribution[score] = distribution.get(score, 0) + 1

            dist_table = Table()
            dist_table.add_column("Score", style="cyan")
            dist_table.add_column("Count", style="white")
            dist_table.add_column("Percentage", style="yellow")

            for score in sorted(distribution.keys()):
                count = distribution[score]
                percentage = (count / len(content_scores)) * 100
                dist_table.add_row(str(score), str(count), f"{percentage:.1f}%")

            console.print(dist_table)

    except Exception as e:
        console.print(f"[red]Error calculating rating statistics: {e}[/red]")
        logger.exception("Failed to calculate rating stats")
        sys.exit(1)
