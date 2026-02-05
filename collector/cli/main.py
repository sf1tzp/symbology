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


import click

# Import command modules
from src.cli.companies import companies
from src.cli.documents import documents
from src.cli.filings import filings
from src.cli.financials import financials
from src.cli.generated_content import generated_content
from src.cli.model_configs import model_configs
from src.cli.prompts import prompts
from src.cli.ratings import ratings

# Add project root to path for imports
# sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.utils.config import settings
from src.utils.logging import configure_logging, get_logger

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



if __name__ == '__main__':
    cli()
