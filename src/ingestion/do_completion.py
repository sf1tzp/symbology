"""
Completion functions for document processing workflow.

This module handles the workflow of retrieving documents from the database,
sending them to the LLM for processing, and storing the results back in the database.
It serves as a bridge between the database layer and the LLM layer.
"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from .config import settings
from .database import crud_company, crud_filing, crud_llm_completion, crud_source_document
from .database.models import LLMCompletion
from .llm.client import OpenAIClient

logger = logging.getLogger(__name__)

def summarize_document(
    db: Session,
    source_document_id: int,
    prompt_template_id: int,
    company_id: Optional[int] = None,
    filing_id: Optional[int] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    tags: Optional[List[str]] = None,
    notes: Optional[str] = None
) -> LLMCompletion:
    """
    Summarizes a document from the database using an LLM and stores the result.

    This function demonstrates the edgar -> database -> llm -> database flow
    by retrieving a document, sending it to the LLM, and storing the result.

    Args:
        db: Database session
        source_document_id: ID of the document to summarize
        prompt_template_id: ID of the prompt template to use
        company_id: Optional ID of the company associated with the document
        filing_id: Optional ID of the filing associated with the document
        model: Optional model override
        temperature: Optional temperature override
        max_tokens: Optional max tokens override
        tags: Optional tags for the completion
        notes: Optional notes about the completion

    Returns:
        The created LLMCompletion object
    """
    # Step 1: Retrieve the document from the database
    document = crud_source_document.get_source_document(db, source_document_id)
    if not document:
        raise ValueError(f"Source document with ID {source_document_id} not found")

    # Step 2: Retrieve the prompt template
    prompt_template = crud_llm_completion.get_prompt_template(db, prompt_template_id)
    if not prompt_template:
        raise ValueError(f"Prompt template with ID {prompt_template_id} not found")

    # Step 3: If company_id is provided but filing_id isn't, try to find the filing
    if company_id and not filing_id and document.filing_id:
        filing_id = document.filing_id

    # Step 4: Prepare variables for prompt template
    company_name = None
    document_type = None

    if company_id:
        company = crud_company.get_company(db, company_id)
        if company:
            company_name = company.name

    if filing_id:
        filing = crud_filing.get_filing(db, filing_id)
        if filing:
            document_type = filing.filing_type

    # Set defaults if not found
    company_name = company_name or "the company"
    document_type = document_type or "financial document"

    # Prepare the prompt variables
    user_prompt_vars = {
        "company_name": company_name,
        "document_type": document_type
    }

    # Format the prompts with variables
    try:
        system_prompt = prompt_template.system_prompt
        user_prompt = prompt_template.user_prompt_template.format(**user_prompt_vars)
    except KeyError as e:
        raise ValueError(f"Missing required variable for prompt template: {str(e)}") from e

    # Step 5: Get default parameters from the template if not overridden
    default_params = prompt_template.default_parameters or {}

    # Use model from parameters, template, or global settings
    model = model or default_params.get("model") or settings.openai.default_model

    temperature = temperature if temperature is not None else default_params.get("temperature", 0.7)
    max_tokens = max_tokens or default_params.get("max_tokens", 4000)
    top_p = default_params.get("top_p", 1.0)
    frequency_penalty = default_params.get("frequency_penalty", 0.0)
    presence_penalty = default_params.get("presence_penalty", 0.0)
    stop_sequences = default_params.get("stop_sequences")

    # Step 6: Create the OpenAI client and generate the completion
    client = OpenAIClient()

    # The document text will be used as context
    context_texts = [document.content]

    # Generate the completion using the LLM
    completion_text = client.generate_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        context_texts=context_texts,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
        stop=stop_sequences,
    )

    # Step 7: Store the completion in the database
    db_completion = crud_llm_completion.create_ai_completion(
        db=db,
        prompt_template_id=prompt_template_id,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        completion_text=completion_text,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        company_id=company_id,
        filing_id=filing_id,
        source_document_ids=[source_document_id],
        context_completion_ids=None,
        context_texts=context_texts,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
        stop_sequences=stop_sequences,
        token_usage=None,  # Token usage not available with current client implementation
        tags=tags,
        notes=notes,
    )

    return db_completion

def summarize_multiple_documents(
    db: Session,
    source_document_ids: List[int],
    prompt_template_id: int,
    company_id: Optional[int] = None,
    filing_id: Optional[int] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    tags: Optional[List[str]] = None,
    notes: Optional[str] = None
) -> LLMCompletion:
    """
    Summarizes multiple documents from the database using an LLM and stores the result.

    Args:
        db: Database session
        source_document_ids: List of IDs of documents to summarize
        prompt_template_id: ID of the prompt template to use
        company_id: Optional ID of the company associated with the documents
        filing_id: Optional ID of the filing associated with the documents
        model: Optional model override
        temperature: Optional temperature override
        max_tokens: Optional max tokens override
        tags: Optional tags for the completion
        notes: Optional notes about the completion

    Returns:
        The created LLMCompletion object
    """
    # Step 1: Retrieve all documents from the database
    documents = []
    for doc_id in source_document_ids:
        document = crud_source_document.get_source_document(db, doc_id)
        if document:
            documents.append(document)

    if not documents:
        raise ValueError("No valid source documents found with provided IDs")

    # Step 2: Retrieve the prompt template
    prompt_template = crud_llm_completion.get_prompt_template(db, prompt_template_id)
    if not prompt_template:
        raise ValueError(f"Prompt template with ID {prompt_template_id} not found")

    # Step 3: If company_id is provided but filing_id isn't, try to find the filing
    if company_id and not filing_id and documents[0].filing_id:
        filing_id = documents[0].filing_id

    # Step 4: Prepare variables for prompt template
    company_name = None
    document_type = None

    if company_id:
        company = crud_company.get_company(db, company_id)
        if company:
            company_name = company.name

    if filing_id:
        filing = crud_filing.get_filing(db, filing_id)
        if filing:
            document_type = filing.filing_type

    # Set defaults if not found
    company_name = company_name or "the company"
    document_type = document_type or "financial documents"

    # Prepare the prompt variables
    user_prompt_vars = {
        "company_name": company_name,
        "document_type": document_type
    }

    # Format the prompts with variables
    try:
        system_prompt = prompt_template.system_prompt
        user_prompt = prompt_template.user_prompt_template.format(**user_prompt_vars)
    except KeyError as e:
        raise ValueError(f"Missing required variable for prompt template: {str(e)}") from e

    # Step 5: Get default parameters from the template if not overridden
    default_params = prompt_template.default_parameters or {}

    # Use model from parameters, template, or global settings
    model = model or default_params.get("model") or settings.openai.default_model

    # Ensure model is never None
    if model is None:
        logger.warning("No model specified in parameters, template or settings. Using a fallback model.")
        model = "hf.co/lmstudio-community/gemma-3-12b-it-GGUF:Q6_K"  # Fallback model as last resort

    temperature = temperature if temperature is not None else default_params.get("temperature", 0.7)
    max_tokens = max_tokens or default_params.get("max_tokens", 4000)
    top_p = default_params.get("top_p", 1.0)
    frequency_penalty = default_params.get("frequency_penalty", 0.0)
    presence_penalty = default_params.get("presence_penalty", 0.0)
    stop_sequences = default_params.get("stop_sequences")

    # Step 6: Create the OpenAI client and generate the completion
    client = OpenAIClient()

    # Combine document contents as context
    context_texts = [doc.content for doc in documents]

    # Generate the completion using the LLM
    completion_text = client.generate_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        context_texts=context_texts,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
        stop=stop_sequences,
    )

    # Step 7: Store the completion in the database
    db_completion = crud_llm_completion.create_ai_completion(
        db=db,
        prompt_template_id=prompt_template_id,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        completion_text=completion_text,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        company_id=company_id,
        filing_id=filing_id,
        source_document_ids=source_document_ids,
        context_completion_ids=None,
        context_texts=context_texts,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
        stop_sequences=stop_sequences,
        token_usage=None,  # Token usage not available with current client implementation
        tags=tags,
        notes=notes,
    )

    return db_completion