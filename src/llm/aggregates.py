from typing import Dict, List, Optional, Tuple

from src.database.aggregates import create_aggregate, get_recent_aggregates_by_ticker, update_aggregate
from src.database.companies import Company, get_company, get_company_by_ticker, update_company
from src.database.completions import Completion
from src.database.documents import DocumentType
from src.database.prompts import Prompt
from src.llm.client import get_chat_response, init_client
from src.llm.completions import ModelConfig
from src.llm.prompts import AGGREGATE_SUMMARY_PROMPT, format_aggregate_messages, PromptRole
from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(name="aggregates")


def create_document_type_aggregate(
    document_type: DocumentType,
    completions: List[Completion],
    prompt: Prompt,
    model_config: ModelConfig,
) -> Optional[object]:
    """
    Create an aggregate for a specific document type.

    Args:
        document_type: Type of documents to aggregate
        completions: List of completion objects to aggregate
        prompt: Prompt to use for aggregation
        model_config: Model configuration for aggregation

    Returns:
        Created aggregate object or None if failed
    """
    if len(completions) < 1:
        return None

    document = completions[0].source_documents[0]
    company = document.company

    try:

        logger.info("document_aggregate", company=company.ticker, document_type=document.document_type)
        messages = format_aggregate_messages(prompt, completions)
        response = get_chat_response(model_config, messages)

        # Create aggregate record in database
        created_at = response.created_at
        total_duration = response.total_duration / 1e9
        content = response.message.content

        aggregate_data = {
            'model': model_config.name,
            'company_id': company.id,
            'document_type': document_type,
            'system_prompt_id': prompt.id,
            'total_duration': total_duration,
            'created_at': created_at,
            'num_ctx': model_config.num_ctx,
            'temperature': model_config.temperature,
            'top_k': model_config.top_k,
            'top_p': model_config.top_p,
            'content': content,
            'completions': completions
        }

        aggregate = create_aggregate(aggregate_data)

        return aggregate

    except Exception as e:
        logger.error(
            f"Error creating {document_type.value} aggregate",
            ticker=company.ticker,
            error=str(e)
        )
        return None


def process_all_aggregates(
    client,
    ticker: str,
    completion_ids_by_type: Dict[str, List[int]],
    completion_data_by_type: Dict[str, Dict[str, str]],
    model: str = "qwen3:14b",
) -> Dict[str, object]:
    """
    Process aggregates for all document types.

    Args:
        client: The LLM client instance
        ticker: Company ticker symbol
        completion_ids_by_type: Dictionary mapping document types to completion ID lists
        completion_data_by_type: Dictionary mapping document types to completion content
        model: Model to use for aggregation

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
                model_config=model,
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


def generate_company_summary(
    ticker: str,
    company: Company,
    model: ModelConfig,
    prompt: Prompt
) -> Optional[str]:
    try:
        client = init_client(settings.openai_api.url)

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
        summary_response = get_chat_response(client, model, {}, summary_messages)
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