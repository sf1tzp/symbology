"""
Utility functions for working with AI completions and storing them in the database.

This module provides a bridge between the OpenAI client and the database CRUD
operations for storing AI completions and related metadata.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..database import crud_ai_completion
from ..database.models import CompletionRating, LLMCompletion
from .client import OpenAIClient


def generate_and_store_completion(
    db: Session,
    prompt_template_id: int,
    user_prompt_vars: Dict[str, str] = None,
    system_prompt_vars: Dict[str, str] = None,
    company_id: Optional[int] = None,
    filing_id: Optional[int] = None,
    source_document_ids: Optional[List[int]] = None,
    context_completion_ids: Optional[List[int]] = None,
    context_texts: Optional[List[str]] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    top_p: Optional[float] = None,
    frequency_penalty: Optional[float] = None,
    presence_penalty: Optional[float] = None,
    stop_sequences: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    notes: Optional[str] = None,
) -> LLMCompletion:
    """
    Generate a completion using a prompt template and store it in the database.

    Args:
        db: Database session
        prompt_template_id: ID of the prompt template to use
        user_prompt_vars: Variables to format into the user prompt template
        system_prompt_vars: Variables to format into the system prompt template
        company_id: Optional ID of the related company
        filing_id: Optional ID of the related filing
        source_document_ids: Optional list of source document IDs to use as context
        context_completion_ids: Optional list of completion IDs to use as context
        context_texts: Optional list of context texts to provide
        model: Optional model to use (overrides template default)
        temperature: Optional temperature to use (overrides template default)
        max_tokens: Optional max tokens to use (overrides template default)
        top_p: Optional top_p to use (overrides template default)
        frequency_penalty: Optional frequency penalty to use (overrides template default)
        presence_penalty: Optional presence penalty to use (overrides template default)
        stop_sequences: Optional stop sequences to use (overrides template default)
        tags: Optional tags for the completion
        notes: Optional notes about the completion

    Returns:
        The created LLMCompletion object
    """
    # Get the prompt template
    prompt_template = crud_ai_completion.get_prompt_template(db, prompt_template_id)
    if not prompt_template:
        raise ValueError(f"Prompt template with ID {prompt_template_id} not found")

    # Format the prompts with variables
    user_prompt_vars = user_prompt_vars or {}
    system_prompt_vars = system_prompt_vars or {}

    try:
        system_prompt = prompt_template.system_prompt.format(**system_prompt_vars)
        user_prompt = prompt_template.user_prompt_template.format(**user_prompt_vars)
    except KeyError as e:
        raise ValueError(f"Missing required variable for prompt template: {str(e)}") from e

    # Get default parameters from the template if not overridden
    default_params = prompt_template.default_parameters or {}
    model = model or default_params.get("model")
    temperature = temperature if temperature is not None else default_params.get("temperature", 0.7)
    max_tokens = max_tokens or default_params.get("max_tokens", 4000)
    top_p = top_p if top_p is not None else default_params.get("top_p", 1.0)
    frequency_penalty = frequency_penalty if frequency_penalty is not None else default_params.get("frequency_penalty", 0.0)
    presence_penalty = presence_penalty if presence_penalty is not None else default_params.get("presence_penalty", 0.0)
    stop_sequences = stop_sequences or default_params.get("stop_sequences")

    # Get context from previous completions if specified
    if context_completion_ids:
        context_texts = context_texts or []
        for comp_id in context_completion_ids:
            prev_completion = crud_ai_completion.get_ai_completion(db, comp_id)
            if prev_completion:
                context_texts.append(prev_completion.completion_text)

    # Create the OpenAI client
    client = OpenAIClient()

    # Generate the completion
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

    # Store the completion in the database
    db_completion = crud_ai_completion.create_ai_completion(
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
        context_completion_ids=context_completion_ids,
        context_texts=context_texts,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
        stop_sequences=stop_sequences,
        # Completion ID not available with current client implementation
        token_usage=None,  # Token usage not available with current client implementation
        tags=tags,
        notes=notes,
    )

    return db_completion


def rate_completion(
    db: Session,
    completion_id: int,
    rating: Optional[int] = None,
    accuracy_score: Optional[int] = None,
    relevance_score: Optional[int] = None,
    helpfulness_score: Optional[int] = None,
    comments: Optional[str] = None,
) -> CompletionRating:
    """
    Rate an AI completion and store the rating in the database.

    Args:
        db: Database session
        completion_id: ID of the completion to rate
        rating: Optional overall rating (1-5)
        accuracy_score: Optional accuracy score (1-5)
        relevance_score: Optional relevance score (1-5)
        helpfulness_score: Optional helpfulness score (1-5)
        comments: Optional comments about the completion

    Returns:
        The created CompletionRating object
    """
    # Verify the completion exists
    completion = crud_ai_completion.get_ai_completion(db, completion_id)
    if not completion:
        raise ValueError(f"Completion with ID {completion_id} not found")

    # Create the rating
    db_rating = crud_ai_completion.create_completion_rating(
        db=db,
        completion_id=completion_id,
        rating=rating,
        accuracy_score=accuracy_score,
        relevance_score=relevance_score,
        helpfulness_score=helpfulness_score,
        comments=comments,
    )

    return db_rating


def create_predefined_prompt_templates(db: Session) -> Dict[str, int]:
    """
    Create predefined prompt templates for common use cases.

    Args:
        db: Database session

    Returns:
        Dictionary mapping template names to their IDs
    """
    now = datetime.now()
    templates = [
        {
            "name": "Risk Analysis",
            "description": "Analyze a company's risk factors and management's response over time",
            "system_prompt": "You are a financial analyst specializing in risk assessment. Analyze the provided document to identify key risk factors, how management is addressing them, and whether their approach has changed over time. Focus on both explicit statements and implicit indicators of risk management sophistication.",
            "user_prompt_template": "Please analyze the risk factors and management's response for {company_name} from their {document_type}. Pay special attention to:\n\n1. Major risk categories identified\n2. How management plans to mitigate these risks\n3. Changes in risk approach compared to previous statements\n4. The level of detail and sophistication in their risk management\n\nProvide specific examples from the text to support your analysis.",
            "category": "risk_analysis",
            "default_parameters": {
                "temperature": 0.3,
                "max_tokens": 2000
            },
            "created_at": now,
            "updated_at": now,
            "is_active": True
        },
        {
            "name": "Management Competency Assessment",
            "description": "Evaluate management's competency based on their communications and decisions",
            "system_prompt": "You are an executive coach and management consultant who specializes in evaluating leadership effectiveness. Analyze the provided document to assess the competency of the management team based on their communication style, strategic decisions, and how they frame challenges and opportunities.",
            "user_prompt_template": "Please evaluate the competency of {company_name}'s management team based on their {document_type}. Assess:\n\n1. Communication clarity and transparency\n2. Strategic vision and planning capability\n3. Problem-solving approach and decision-making quality\n4. Adaptability to changing conditions\n5. Accountability for results and failures\n\nProvide specific examples from the text to support your assessment.",
            "category": "management_assessment",
            "default_parameters": {
                "temperature": 0.4,
                "max_tokens": 2000
            },
            "created_at": now,
            "updated_at": now,
            "is_active": True
        },
        {
            "name": "Financial Position Analysis",
            "description": "Analyze a company's financial position and performance trends",
            "system_prompt": "You are a financial analyst specializing in evaluating company financial statements. Analyze the provided financial data to assess the company's financial health, performance trends, and areas of strength or concern.",
            "user_prompt_template": "Please analyze the financial position of {company_name} based on their {document_type}. Assess:\n\n1. Profitability trends and margins\n2. Liquidity and solvency indicators\n3. Cash flow generation and quality\n4. Capital allocation and investment strategy\n5. Areas of financial strength and potential concern\n\nProvide specific metrics and figures from the data to support your analysis.",
            "category": "financial_analysis",
            "default_parameters": {
                "temperature": 0.2,
                "max_tokens": 2500
            },
            "created_at": now,
            "updated_at": now,
            "is_active": True
        },
        {
            "name": "Business Model Summary",
            "description": "Create a concise summary of a company's business model and strategy",
            "system_prompt": "You are a business strategist who specializes in analyzing business models and corporate strategies. Review the provided document to extract and summarize the company's core business model, value proposition, target markets, and competitive advantages.",
            "user_prompt_template": "Please provide a concise summary of {company_name}'s business model based on their {document_type}. Include:\n\n1. Core value proposition and revenue streams\n2. Target customers and market positioning\n3. Key products/services and their significance\n4. Growth strategy and expansion plans\n5. Competitive advantages and differentiators\n\nKeep the summary clear, factual, and well-structured.",
            "category": "business_analysis",
            "default_parameters": {
                "temperature": 0.3,
                "max_tokens": 1500
            },
            "created_at": now,
            "updated_at": now,
            "is_active": True
        }
    ]

    template_ids = {}

    for template_data in templates:
        # Check if template already exists
        existing_templates = crud_ai_completion.get_prompt_templates(
            db=db,
            category=template_data["category"]
        )

        existing_template = next(
            (t for t in existing_templates if t.name == template_data["name"]),
            None
        )

        if existing_template:
            template_ids[template_data["name"]] = existing_template.id
        else:
            # Create new template
            new_template = crud_ai_completion.create_prompt_template(
                db=db,
                name=template_data["name"],
                description=template_data["description"],
                system_prompt=template_data["system_prompt"],
                user_prompt_template=template_data["user_prompt_template"],
                category=template_data["category"],
                default_parameters=template_data["default_parameters"],
            )
            template_ids[template_data["name"]] = new_template.id

    return template_ids


def get_completion_dependency_chain(db: Session, completion_id: int, max_depth: int = 5) -> Dict[str, Any]:
    """
    Get the dependency chain for an AI completion, showing the context completions it uses
    and any completions that use it as context, up to a maximum depth.

    Args:
        db: Database session
        completion_id: ID of the completion to analyze
        max_depth: Maximum depth of dependency chain to retrieve

    Returns:
        Dictionary containing the completion and its dependency chain
    """
    completion = crud_ai_completion.get_ai_completion(db, completion_id)
    if not completion:
        raise ValueError(f"Completion with ID {completion_id} not found")

    result = {
        "id": completion.id,
        "prompt_template_name": completion.prompt_template.name if completion.prompt_template else None,
        "created_at": completion.created_at,
        "tags": completion.tags,
        "context_completions": [],
        "used_as_context_by": []
    }

    # Get context completions (parent completions)
    if completion.context_completions and max_depth > 0:
        for ctx_completion in completion.context_completions:
            ctx_result = get_completion_dependency_chain(db, ctx_completion.id, max_depth - 1)
            result["context_completions"].append(ctx_result)

    # Get completions that use this as context (child completions)
    if completion.used_as_context_by and max_depth > 0:
        for child_completion in completion.used_as_context_by:
            child_result = {
                "id": child_completion.id,
                "prompt_template_name": child_completion.prompt_template.name if child_completion.prompt_template else None,
                "created_at": child_completion.created_at,
                "tags": child_completion.tags
            }
            result["used_as_context_by"].append(child_result)

    return result