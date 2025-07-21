import json
import os
from typing import Dict, List, Optional

from src.database.companies import get_company_by_ticker
from src.database.completions import Completion, create_completion
from src.database.documents import Document, DocumentType, get_documents_by_filing
from src.database.filings import get_filings_by_company
from src.database.prompts import Prompt
from src.llm.client import get_chat_response, ModelConfig
from src.llm.prompts import format_document_messages
from src.utils.logging import get_logger

logger = get_logger(name="completions")


def process_document_completion(
    document: Document,
    prompt: Prompt,
    model_config: ModelConfig,
) -> Completion:
    """
    Process a single document to generate a completion.


    Args:
        client: The LLM client instance
        document: Document instance to process
        filing: Filing instance the document belongs to
        ticker: Company ticker symbol
        model: Model to use for completion

    Returns:
        Tuple of (completion_result_dict, completion_id)
    """
    filing = document.filing
    company = document.company

    try:
        messages = format_document_messages(prompt, document)

        logger.info("document_completion_start", company=company.ticker, year=filing.fiscal_year, document_type=document.document_type.value)
        response = get_chat_response(model_config, messages)

        # Extract necessary details from the response
        created_at = response.created_at
        total_duration = response.total_duration / 1e9
        content = response.message.content

        completion_data = {
            'model': model_config.name,
            'num_ctx': model_config.num_ctx,
            'temperature': model_config.temperature,
            'top_k': model_config.top_k,
            'top_p': model_config.top_p,
            'document_ids': [document.id],
            'system_prompt_id': prompt.id,
            'total_duration': total_duration,
            'created_at': created_at,
            'content': content,
        }

        completion = create_completion(completion_data)

        return completion

    except Exception as e:
        logger.error("Error processing document completion",
                    document_id=document.id,
                    error=str(e))
        raise


def process_company_document_completions(
    client,
    ticker: str,
    model: str = "qwen3:4b",
    output_dir: Optional[str] = None
) -> Dict[str, List[int]]:
    """
    Process all documents for a company and generate completions.

    Args:
        client: The LLM client instance
        ticker: Company ticker symbol
        model: Model to use for completions
        output_dir: Optional directory to save results (defaults to outputs/{ticker})

    Returns:
        Dictionary mapping document types to lists of completion IDs
    """
    logger.info(f"Starting document completion processing for {ticker}")

    company = get_company_by_ticker(ticker)
    filings = get_filings_by_company(company_id=company.id)

    # Storage for results by document type
    descriptions = {}
    risk_factors = {}
    mdas = {}

    # Track completion IDs by document type for aggregation
    completion_ids_by_type = {
        "description": [],
        "risk_factors": [],
        "mda": []
    }

    total_processed = 0

    for filing in filings:
        documents = get_documents_by_filing(filing.id)

        for document in documents:
            result, completion_id = process_document_completion(
                client, document, filing, ticker, model
            )

            # Store results and track completion IDs for aggregation
            if document.document_type == DocumentType.DESCRIPTION:
                descriptions[result["filing_date"]] = result["content"]
                completion_ids_by_type["description"].append(completion_id)
            elif document.document_type == DocumentType.RISK_FACTORS:
                risk_factors[result["filing_date"]] = result["content"]
                completion_ids_by_type["risk_factors"].append(completion_id)
            elif document.document_type == DocumentType.MDA:
                mdas[result["filing_date"]] = result["content"]
                completion_ids_by_type["mda"].append(completion_id)
            else:
                logger.warning(f"Unknown document type: {document.document_type}")

            total_processed += 1

    logger.info(f"Document completions generated for {ticker}",
                total_processed=total_processed)

    # Save results to files if output directory specified
    if output_dir:
        save_completion_results(ticker, descriptions, risk_factors, mdas, output_dir)

    return completion_ids_by_type


def save_completion_results(
    ticker: str,
    descriptions: Dict,
    risk_factors: Dict,
    mdas: Dict,
    output_dir: str = None
) -> None:
    """
    Save completion results to JSON files.

    Args:
        ticker: Company ticker symbol
        descriptions: Dictionary of description completions
        risk_factors: Dictionary of risk factor completions
        mdas: Dictionary of MDA completions
        output_dir: Directory to save files (defaults to outputs/{ticker})
    """
    if output_dir is None:
        output_dir = f'outputs/{ticker}'

    os.makedirs(output_dir, exist_ok=True)

    files_to_save = [
        (f'{output_dir}/mdas.json', mdas),
        (f'{output_dir}/risk_factors.json', risk_factors),
        (f'{output_dir}/descriptions.json', descriptions)
    ]

    for filepath, data in files_to_save:
        try:
            with open(filepath, 'w') as file:
                json.dump(data, file, indent=4)
            logger.info(f"Saved completion results to {filepath}")
        except Exception as e:
            logger.error(f"Error saving to {filepath}: {str(e)}")


def get_completion_results_by_type(
    ticker: str,
    document_type: DocumentType
) -> Dict[str, str]:
    """
    Load completion results for a specific document type from saved files.

    Args:
        ticker: Company ticker symbol
        document_type: Type of document to load

    Returns:
        Dictionary mapping filing dates to completion content
    """
    type_mapping = {
        DocumentType.DESCRIPTION: 'descriptions.json',
        DocumentType.RISK_FACTORS: 'risk_factors.json',
        DocumentType.MDA: 'mdas.json'
    }

    filename = type_mapping.get(document_type)
    if not filename:
        raise ValueError(f"Unsupported document type: {document_type}")

    filepath = f'outputs/{ticker}/{filename}'

    try:
        with open(filepath, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        logger.warning(f"No completion results found at {filepath}")
        return {}
    except Exception as e:
        logger.error(f"Error loading completion results from {filepath}: {str(e)}")
        return {}