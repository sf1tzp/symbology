import os
from typing import Dict, List, Optional, Tuple

from src.database.aggregates import create_aggregate, get_recent_aggregates_by_ticker, update_aggregate
from src.database.companies import get_company, get_company_by_ticker, update_company
from src.database.documents import DocumentType
from src.database.prompts import get_prompt_by_name
from src.llm.client import get_chat_response
from src.llm.models import MODEL_CONFIG
from src.llm.prompts import AGGREGATE_SUMMARY_PROMPT, format_aggregate_messages, PromptRole
from src.utils.logging import get_logger

logger = get_logger(name="aggregations")


def create_document_type_aggregate(
    client,
    ticker: str,
    document_type: DocumentType,
    completion_data: Dict[str, str],
    completion_ids: List[int],
    model: str = "qwen3:14b",
    output_dir: Optional[str] = None
) -> Optional[object]:
    """
    Create an aggregate for a specific document type.

    Args:
        client: The LLM client instance
        ticker: Company ticker symbol
        document_type: Type of documents to aggregate
        completion_data: Dictionary mapping filing dates to completion content
        completion_ids: List of completion IDs to associate with aggregate
        model: Model to use for aggregation
        output_dir: Optional directory to save markdown output

    Returns:
        Created aggregate object or None if failed
    """
    try:
        company = get_company_by_ticker(ticker)

        # Generate aggregate using LLM
        messages = format_aggregate_messages(completion_data)
        response = get_chat_response(client, model, messages)

        logger.info(
            f"{document_type.value} Aggregate Done",
            time=f"{response.total_duration / 1e9}s"
        )

        # Save markdown output if directory specified
        if output_dir:
            save_aggregate_markdown(ticker, document_type, response.message.content, output_dir)

        # Create aggregate record in database
        created_at = response.created_at
        total_duration = response.total_duration / 1e9
        content = response.message.content
        prompt = get_prompt_by_name("aggregate_prompt")

        aggregate_data = {
            'model': model,
            'company_id': company.id,
            'document_type': document_type,
            'system_prompt_id': prompt.id,
            'total_duration': total_duration,
            'created_at': created_at,
            'num_ctx': MODEL_CONFIG[model]["ctx"],
            'content': content,
            'completion_ids': completion_ids
        }

        aggregate = create_aggregate(aggregate_data)

        logger.info(
            f"Created {document_type.value} aggregate",
            aggregate_id=aggregate.id,
            completion_count=len(completion_ids),
            model=aggregate.model,
            duration=f"{aggregate.total_duration:.2f}s",
            content_length=len(aggregate.content)
        )

        return aggregate

    except Exception as e:
        logger.error(
            f"Error creating {document_type.value} aggregate",
            ticker=ticker,
            error=str(e)
        )
        return None


def process_all_aggregates(
    client,
    ticker: str,
    completion_ids_by_type: Dict[str, List[int]],
    completion_data_by_type: Dict[str, Dict[str, str]],
    model: str = "qwen3:14b",
    output_dir: Optional[str] = None
) -> Dict[str, object]:
    """
    Process aggregates for all document types.

    Args:
        client: The LLM client instance
        ticker: Company ticker symbol
        completion_ids_by_type: Dictionary mapping document types to completion ID lists
        completion_data_by_type: Dictionary mapping document types to completion content
        model: Model to use for aggregation
        output_dir: Optional directory to save markdown outputs

    Returns:
        Dictionary mapping document types to created aggregate objects
    """
    logger.info(f"Starting aggregate processing for {ticker}")

    # Mapping from our internal keys to DocumentType enums
    type_mapping = {
        "mda": DocumentType.MDA,
        "risk_factors": DocumentType.RISK_FACTORS,
        "description": DocumentType.DESCRIPTION
    }

    aggregates = {}

    for type_key, document_type in type_mapping.items():
        if type_key in completion_ids_by_type and completion_ids_by_type[type_key]:
            completion_data = completion_data_by_type.get(type_key, {})
            completion_ids = completion_ids_by_type[type_key]

            aggregate = create_document_type_aggregate(
                client=client,
                ticker=ticker,
                document_type=document_type,
                completion_data=completion_data,
                completion_ids=completion_ids,
                model=model,
                output_dir=output_dir
            )

            if aggregate:
                aggregates[type_key] = aggregate
            else:
                logger.warning(f"Failed to create aggregate for {type_key}")
        else:
            logger.info(f"No completions found for {type_key}, skipping aggregate")

    logger.info(f"Completed aggregate processing for {ticker}",
                aggregates_created=len(aggregates))

    return aggregates


def save_aggregate_markdown(
    ticker: str,
    document_type: DocumentType,
    content: str,
    output_dir: Optional[str] = None
) -> None:
    """
    Save aggregate content to a markdown file.

    Args:
        ticker: Company ticker symbol
        document_type: Type of document
        content: Aggregate content to save
        output_dir: Directory to save file (defaults to outputs/{ticker})
    """
    if output_dir is None:
        output_dir = f'outputs/{ticker}'

    os.makedirs(output_dir, exist_ok=True)

    # Map document types to filenames
    filename_mapping = {
        DocumentType.MDA: 'mda.md',
        DocumentType.RISK_FACTORS: 'risk_factors.md',
        DocumentType.DESCRIPTION: 'descriptions.md'
    }

    filename = filename_mapping.get(document_type, f'{document_type.value}.md')
    filepath = f'{output_dir}/{filename}'

    try:
        with open(filepath, 'w') as file:
            file.write(content)
        logger.info(f"Saved {document_type.value} aggregate to {filepath}")
    except Exception as e:
        logger.error(f"Error saving aggregate to {filepath}: {str(e)}")


def generate_company_summary(
    client,
    ticker: str,
    model: str = "qwen3:14b"
) -> Optional[str]:
    """
    Generate a comprehensive company summary from recent aggregates.

    Args:
        client: The LLM client instance
        ticker: Company ticker symbol
        model: Model to use for summary generation

    Returns:
        Generated summary content or None if failed
    """
    try:
        company = get_company_by_ticker(ticker)

        # Get the most recent aggregates for the ticker
        recent_aggregates = get_recent_aggregates_by_ticker(ticker)
        logger.info(f"Found {len(recent_aggregates)} recent aggregates for {ticker}")

        if not recent_aggregates:
            logger.warning(f"No recent aggregates found for {ticker}")
            return None

        # Prepare content for summary generation
        aggregate_contents = {}
        for aggregate in recent_aggregates:
            doc_type = aggregate.document_type.value if aggregate.document_type else 'unknown'
            aggregate_contents[doc_type] = aggregate.content

        logger.info(f"Aggregate types available: {list(aggregate_contents.keys())}")

        # Format the aggregates content for the summary prompt
        formatted_content = ""
        for doc_type, content in aggregate_contents.items():
            formatted_content += f"\n\n## {doc_type.upper()} Analysis\n\n{content}"

        # Create messages for summary generation
        summary_messages = [{
            'role': PromptRole.SYSTEM.value,
            'content': AGGREGATE_SUMMARY_PROMPT,
        }, {
            'role': PromptRole.USER.value,
            'content': formatted_content,
        }]

        logger.info(f"Generating summary for {ticker} using {len(aggregate_contents)} aggregate reports")

        # Generate the summary using the aggregates
        summary_response = get_chat_response(client, model, summary_messages)
        logger.info(f"Summary generation completed in {summary_response.total_duration / 1e9:.2f} seconds")

        # Extract the summary content
        summary_content = summary_response.message.content
        logger.info(f"Generated summary length: {len(summary_content)} characters")

        # Save the summary to the company's summary column
        update_data = {'summary': summary_content}
        updated_company = update_company(company.id, update_data)

        if updated_company:
            logger.info(
                f"Successfully updated company summary for {ticker}",
                company_id=str(company.id),
                summary_length=len(summary_content)
            )
            return summary_content
        else:
            logger.error(f"Failed to update company summary for {ticker}")
            return None

    except Exception as e:
        logger.error(f"Error generating company summary for {ticker}: {str(e)}")
        return None


def generate_aggregate_summaries(
    client,
    ticker: str,
    model: str = "qwen3:14b"
) -> Dict[str, bool]:
    """
    Generate concise summaries for individual aggregates.

    Args:
        client: The LLM client instance
        ticker: Company ticker symbol
        model: Model to use for summary generation

    Returns:
        Dictionary mapping aggregate IDs to success status
    """
    logger.info(f"Starting individual aggregate summary generation for {ticker}")

    recent_aggregates = get_recent_aggregates_by_ticker(ticker)
    results = {}

    for i, aggregate in enumerate(recent_aggregates):
        doc_type = aggregate.document_type.value if aggregate.document_type else 'unknown'

        logger.info(
            f"Processing Aggregate {i+1}/{len(recent_aggregates)}: {doc_type.upper()}",
            aggregate_id=aggregate.id,
            content_length=len(aggregate.content) if aggregate.content else 0
        )

        # Skip if aggregate already has a summary
        if aggregate.summary:
            logger.info(f"Aggregate {aggregate.id} already has summary. Skipping.")
            results[str(aggregate.id)] = True
            continue

        # Skip if no content to summarize
        if not aggregate.content or len(aggregate.content.strip()) < 50:
            logger.warning(f"Aggregate {aggregate.id} has insufficient content. Skipping.")
            results[str(aggregate.id)] = False
            continue

        success = _generate_single_aggregate_summary(client, aggregate, doc_type, model)
        results[str(aggregate.id)] = success

    successful_count = sum(results.values())
    logger.info(
        f"Completed individual aggregate summaries for {ticker}",
        total_processed=len(results),
        successful=successful_count
    )

    return results


def _generate_single_aggregate_summary(
    client,
    aggregate,
    doc_type: str,
    model: str
) -> bool:
    """
    Generate summary for a single aggregate.

    Args:
        client: The LLM client instance
        aggregate: Aggregate object to summarize
        doc_type: Document type string
        model: Model to use for summary generation

    Returns:
        True if successful, False otherwise
    """
    try:
        # Create summary prompt based on document type
        prompt_mapping = {
            'management_discussion': "Summarize this management discussion and analysis in 2-3 sentences, highlighting key business developments, financial performance insights, and management's strategic outlook.",
            'risk_factors': "Summarize this risk factors analysis in 2-3 sentences, identifying the most significant risks and any notable changes in the company's risk profile.",
            'business_description': "Summarize this business description analysis in 2-3 sentences, capturing the company's core business model, market position, and key value propositions."
        }

        summary_prompt = prompt_mapping.get(
            doc_type,
            "Summarize this analysis in 2-3 sentences, highlighting the key findings and insights."
        )

        # Create messages for individual aggregate summary
        aggregate_summary_messages = [{
            'role': PromptRole.SYSTEM.value,
            'content': summary_prompt,
        }, {
            'role': PromptRole.USER.value,
            'content': aggregate.content,
        }]

        logger.info(f"Generating summary for {doc_type} aggregate {aggregate.id}")

        # Generate the summary
        aggregate_summary_response = get_chat_response(client, model, aggregate_summary_messages)
        aggregate_summary_content = aggregate_summary_response.message.content.strip()

        logger.info(
            f"Summary generated for aggregate {aggregate.id}",
            summary_length=len(aggregate_summary_content)
        )

        # Update the aggregate with the summary
        update_data = {'summary': aggregate_summary_content}
        updated_aggregate = update_aggregate(aggregate.id, update_data)

        if updated_aggregate:
            logger.info(f"Summary saved to aggregate {aggregate.id}")
            return True
        else:
            logger.error(f"Failed to save summary to aggregate {aggregate.id}")
            return False

    except Exception as e:
        logger.error(
            f"Error generating summary for aggregate {aggregate.id}",
            document_type=doc_type,
            error=str(e)
        )
        return False


def verify_company_summary(ticker: str) -> Tuple[bool, Optional[str]]:
    """
    Verify that a company summary was successfully saved.

    Args:
        ticker: Company ticker symbol

    Returns:
        Tuple of (success_status, summary_preview)
    """
    try:
        company = get_company_by_ticker(ticker)
        refreshed_company = get_company(company.id)

        if refreshed_company and refreshed_company.summary:
            preview = refreshed_company.summary[:200] + "..." if len(refreshed_company.summary) > 200 else refreshed_company.summary
            logger.info(f"Company summary verification successful for {ticker}")
            return True, preview
        else:
            logger.warning(f"Company summary verification failed for {ticker}")
            return False, None

    except Exception as e:
        logger.error(f"Error verifying company summary for {ticker}: {str(e)}")
        return False, None


def get_aggregates_summary_report(ticker: str) -> Dict[str, Dict]:
    """
    Generate a summary report of all aggregates for a company.

    Args:
        ticker: Company ticker symbol

    Returns:
        Dictionary with aggregate information
    """
    try:
        refreshed_aggregates = get_recent_aggregates_by_ticker(ticker)
        report = {}

        for aggregate in refreshed_aggregates:
            doc_type = aggregate.document_type.value if aggregate.document_type else 'unknown'

            report[doc_type] = {
                'id': str(aggregate.id),
                'has_summary': bool(aggregate.summary),
                'summary_length': len(aggregate.summary) if aggregate.summary else 0,
                'content_length': len(aggregate.content) if aggregate.content else 0,
                'model': aggregate.model,
                'created_at': str(aggregate.created_at),
                'summary_preview': aggregate.summary[:100] + "..." if aggregate.summary else None
            }

        logger.info(f"Generated summary report for {ticker}", aggregates_count=len(report))
        return report

    except Exception as e:
        logger.error(f"Error generating summary report for {ticker}: {str(e)}")
        return {}