import argparse
import sys

from ingestion.edgar.accessors import edgar_login, get_company
from src.ingestion.config import settings
from src.ingestion.database.base import close_session, get_db_session, init_db
from src.ingestion.database.crud_company import get_companies_by_ticker, upsert_company
from src.ingestion.database.crud_source_document import get_source_documents_by_company_id
from src.ingestion.ten_k import batch_process_10k_filings, process_10k_filing
from src.ingestion.utils.logging import configure_logging, get_logger

# Initialize structlog
logger = get_logger(__name__)


def parse_args():
    """
    Parse command line arguments for the 10-K data ingestion pipeline.
    """
    parser = argparse.ArgumentParser(
        description="Symbology: Financial data processing CLI"
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Add a "demo" command that runs the original demo code
    _ = subparsers.add_parser("demo", help="Run the original demo code")

    # Add a "10k" command for processing 10-K filings
    tenk_parser = subparsers.add_parser("10k", help="Process 10-K filings from EDGAR")
    tenk_parser.add_argument(
        "--tickers",
        "-t",
        nargs="+",
        required=True,
        help="List of ticker symbols (e.g., AAPL MSFT GOOGL)"
    )
    tenk_parser.add_argument(
        "--years",
        "-y",
        type=int,
        nargs="+",
        required=True,
        help="List of years to process (e.g., 2022 2023)"
    )
    tenk_parser.add_argument(
        "--edgar-contact",
        type=str,
        help="Email to use for EDGAR API (defaults to value from config)"
    )

    # Add a "delete" command for deleting companies by ticker
    delete_parser = subparsers.add_parser("delete", help="Delete a company and all its associated data")
    delete_parser.add_argument(
        "--ticker",
        "-t",
        type=str,
        required=True,
        help="Ticker symbol of the company to delete (e.g., AAPL)"
    )
    delete_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force deletion without confirmation"
    )

    # Add a "summarize" command for document summarization
    summarize_parser = subparsers.add_parser("summarize", help="Summarize a document using LLM")
    summarize_parser.add_argument(
        "--document-id",
        "-d",
        type=int,
        required=True,
        help="ID of the document to summarize"
    )
    summarize_parser.add_argument(
        "--template-id",
        "-t",
        type=int,
        required=True,
        help="ID of the prompt template to use"
    )
    summarize_parser.add_argument(
        "--model",
        "-m",
        type=str,
        help="LLM model to use (defaults to template setting)"
    )
    summarize_parser.add_argument(
        "--temperature",
        type=float,
        help="Temperature setting for the LLM (defaults to template setting)"
    )
    summarize_parser.add_argument(
        "--max-tokens",
        type=int,
        help="Maximum tokens for the LLM output (defaults to template setting)"
    )

    # If no arguments are provided, show help and exit
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    return parser.parse_args()


def run_demo():
    """
    Run the original demo functionality that queries information for Microsoft.
    """
    logger.info("Starting demo application")

    # Use the config class for Edgar API login
    logger.info(f"Using Edgar contact: {settings.api.edgar_contact}")
    edgar_login(settings.api.edgar_contact)

    ticker = "MSFT"

    # Get company information for MSFT
    company = get_company(ticker)
    logger.info(f"Retrieved company data for MSFT: {company.name}")
    logger.debug(company)

    # Initialize the database (create tables if they don't exist)
    # Pass the database URL from settings instead of importing settings in the database module
    init_db(settings.database.url)
    logger.info("Database initialized")

    # Convert Edgar company object to dictionary for database storage
    company_data = {
        "cik": company.cik,
        "name": company.name,
        "tickers": [ticker],
        "sic": company.sic,
        "sic_description": company.sic_description,
        "business_address": str(company.business_address),
        "mailing_address": str(company.mailing_address),
        "fiscal_year_end": company.fiscal_year_end,
    }

    # Insert or update the company in the database
    # Using default session since we're in the main application flow
    db_company = upsert_company(company.cik, company_data)
    logger.info(f"Company upserted to database with ID: {db_company.id}")

    # Read back the MSFT data from the database
    # Now we can directly access attributes from the returned objects
    companies = get_companies_by_ticker("MSFT")
    if companies:
        logger.info(f"Retrieved company from database: {companies[0].name}")
        logger.info(f"Company details: {companies[0].to_dict()}")
    else:
        logger.error("Could not find MSFT in the database")

    # Process MSFT 2024 10-K filing
    logger.info("Processing MSFT 2024 10-K filing")
    result = process_10k_filing(ticker, 2024, settings.api.edgar_contact)

    if result["success"]:
        logger.info(f"Successfully processed 10-K filing: {result['message']}")

        # Get the business description from the database
        session = get_db_session()
        source_documents = get_source_documents_by_company_id(session, result["company_id"])

        # Filter to only get business descriptions
        business_descriptions = [doc for doc in source_documents if doc.document_type == "business_description"]
        mgmt_discussion = [doc for doc in source_documents if doc.document_type == "management_discussion"]
        risk_factors = [doc for doc in source_documents if doc.document_type == "risk_factors"]

        if business_descriptions:
            # Get the most recent business description
            latest_business_desc = max(business_descriptions, key=lambda x: x.report_date)

            # Truncate the content to 140 characters
            truncated_content = latest_business_desc.content[:540] + "..." if len(latest_business_desc.content) > 140 else latest_business_desc.content

            logger.info(f"Business Description (truncated): {truncated_content}")
        else:
            logger.warning("No business description found for MSFT")

        if mgmt_discussion:
            # Get the most recent business description
            latest_mgmt_discussion = max(mgmt_discussion, key=lambda x: x.report_date)

            # Truncate the content to 140 characters
            truncated_content = latest_mgmt_discussion.content[:540] + "..." if len(latest_mgmt_discussion.content) > 140 else latest_mgmt_discussion.content

            logger.info(f"Management Discussion (truncated): {truncated_content}")
        else:
            logger.warning("No management discussion found for MSFT")

        if risk_factors:
            # Get the most recent business description
            latest_risk_factors = max(risk_factors, key=lambda x: x.report_date)

            # Truncate the content to 140 characters
            truncated_content = latest_risk_factors.content[:540] + "..." if len(latest_risk_factors.content) > 140 else latest_risk_factors.content

            logger.info(f"Risk Factors (truncated): {truncated_content}")
        else:
            logger.warning("No risk factors found for MSFT")

        session.close()
    else:
        logger.error(f"Failed to process 10-K filing: {result['message']}")
        if result.get("errors"):
            for error in result["errors"]:
                logger.error(f"Error: {error}")

    # Close the session when you're done with all database operations
    close_session()


def run_10k_ingestion(tickers, years, edgar_contact=None):
    """
    Run the 10-K data ingestion pipeline for the specified tickers and years.
    """
    logger.info(f"Starting 10-K data ingestion for {len(tickers)} tickers and {len(years)} years")

    # Initialize the database
    init_db(settings.database.url)
    logger.info("Database initialized")

    # Use the contact email from settings if not provided
    if edgar_contact is None:
        edgar_contact = settings.api.edgar_contact

    # Process the 10-K filings
    logger.info(f"Using Edgar contact: {edgar_contact}")
    results = batch_process_10k_filings(tickers, years, edgar_contact)

    # Log the results
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    logger.info(f"Processed {len(results)} filings")
    logger.info(f"  - Successful: {len(successful)}")
    logger.info(f"  - Failed: {len(failed)}")

    # Log details about failures if any
    if failed:
        logger.warning("Failed filings:")
        for f in failed:
            logger.warning(f"  - {f['ticker']} ({f['year']}): {f['message']}")

    # Close the session when you're done with all database operations
    close_session()

    return results


def delete_company_by_ticker(ticker, force=False):
    """
    Delete a company by its ticker symbol.

    Args:
        ticker: The ticker symbol of the company to delete
        force: If True, skip confirmation prompt

    Returns:
        True if the company was found and deleted, False otherwise
    """
    from src.ingestion.database.crud_company import delete_company, get_companies_by_ticker

    logger.info(f"Looking up company with ticker: {ticker}")

    # Initialize the database
    init_db(settings.database.url)

    # Find the company by ticker
    companies = get_companies_by_ticker(ticker)

    if not companies:
        logger.error(f"No company found with ticker: {ticker}")
        return False

    if len(companies) > 1:
        logger.warning(f"Multiple companies found with ticker {ticker}. Will delete them all.")

    # Confirm deletion if not forced
    if not force:
        company_names = ", ".join([company.name for company in companies])
        confirmation = input(f"Are you sure you want to delete {company_names} and all associated data? This cannot be undone. [y/N]: ")
        if confirmation.lower() not in ["y", "yes"]:
            logger.info("Deletion cancelled.")
            return False

    # Delete all companies with this ticker
    deleted_count = 0
    for company in companies:
        logger.info(f"Deleting company: {company.name} (ID: {company.id}, CIK: {company.cik})")
        result = delete_company(company.id)
        if result:
            deleted_count += 1
            logger.info(f"Successfully deleted company {company.name}")
        else:
            logger.error(f"Failed to delete company {company.name}")

    logger.info(f"Deleted {deleted_count} out of {len(companies)} companies with ticker {ticker}")

    # Close the session when done
    close_session()

    return deleted_count > 0


def run_summarize_document(document_id, template_id, model=None, temperature=None, max_tokens=None):
    """
    Run the document summarization for a specific document using the LLM.

    Args:
        document_id: ID of the document to summarize
        template_id: ID of the prompt template to use
        model: Optional LLM model to use
        temperature: Optional temperature setting
        max_tokens: Optional max tokens setting

    Returns:
        The generated summary completion object
    """
    from src.ingestion.config import settings
    from src.ingestion.database.base import close_session, get_db_session, init_db
    from src.ingestion.database.crud_llm_completion import create_predefined_prompt_templates
    from src.ingestion.do_completion import summarize_document

    logger.info(f"Starting document summarization for document ID: {document_id} with template ID: {template_id}")

    # Initialize the database
    init_db(settings.database.url)

    # Get a database session
    db = get_db_session()

    # load default prompt templates
    create_predefined_prompt_templates(db)

    try:
        # Run the summarization
        completion = summarize_document(
            db=db,
            source_document_id=document_id,
            prompt_template_id=template_id,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )

        logger.info(f"Successfully summarized document. Summary ID: {completion.id}")

        # Print a short preview of the summary
        preview_length = 200
        preview = completion.completion_text[:preview_length] + "..." if len(completion.completion_text) > preview_length else completion.completion_text
        logger.info(f"Summary preview: {preview}")

        return completion

    except Exception as e:
        logger.error(f"Error summarizing document: {str(e)}")
        raise
    finally:
        db.close()
        close_session()


def main():
    # Set up logging
    configure_logging()

    # Parse command line arguments
    args = parse_args()

    # Run the appropriate command
    if args.command == "demo":
        run_demo()
    elif args.command == "10k":
        run_10k_ingestion(
            tickers=args.tickers,
            years=args.years,
            edgar_contact=args.edgar_contact
        )
    elif args.command == "delete":
        success = delete_company_by_ticker(args.ticker, args.force)
        if not success:
            sys.exit(1)
    elif args.command == "summarize":
        try:
            run_summarize_document(
                document_id=args.document_id,
                template_id=args.template_id,
                model=args.model,
                temperature=args.temperature,
                max_tokens=args.max_tokens
            )
        except Exception as e:
            logger.error(f"Summarization failed: {str(e)}")
            sys.exit(1)
    else:
        logger.error(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
