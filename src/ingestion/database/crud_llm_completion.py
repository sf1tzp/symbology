"""
CRUD operations for the AI-related models, including PromptTemplate,
LLMCompletion, and CompletionRating.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from . import models


def create_prompt_template(
    db: Session,
    name: str,
    system_prompt: str,
    user_prompt_template: str,
    description: Optional[str] = None,
    assistant_prompt_template: Optional[str] = None,
    category: Optional[str] = None,
    default_parameters: Optional[Dict[str, Any]] = None,
    is_active: bool = True,
) -> models.PromptTemplate:
    """
    Create a new prompt template.

    Args:
        db: Database session
        name: Name of the prompt template
        system_prompt: System role prompt text
        user_prompt_template: User role prompt template text
        description: Optional description of the prompt template
        assistant_prompt_template: Optional assistant role prompt template
        category: Optional category for the prompt template
        default_parameters: Optional default parameters for OpenAI requests
        is_active: Whether the template is active

    Returns:
        The created PromptTemplate object
    """
    now = datetime.now()
    db_prompt = models.PromptTemplate(
        name=name,
        description=description,
        system_prompt=system_prompt,
        user_prompt_template=user_prompt_template,
        assistant_prompt_template=assistant_prompt_template,
        category=category,
        default_parameters=default_parameters,
        created_at=now,
        updated_at=now,
        is_active=is_active,
    )
    db.add(db_prompt)
    db.commit()
    db.refresh(db_prompt)
    return db_prompt


def get_prompt_template(db: Session, prompt_id: int) -> Optional[models.PromptTemplate]:
    """
    Get a prompt template by ID.

    Args:
        db: Database session
        prompt_id: ID of the prompt template

    Returns:
        The PromptTemplate object if found, None otherwise
    """
    return db.query(models.PromptTemplate).filter(models.PromptTemplate.id == prompt_id).first()


def get_prompt_templates(
    db: Session,
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100
) -> List[models.PromptTemplate]:
    """
    Get a list of prompt templates with optional filtering.

    Args:
        db: Database session
        category: Optional category to filter by
        is_active: Optional active status to filter by
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of PromptTemplate objects
    """
    query = db.query(models.PromptTemplate)

    if category:
        query = query.filter(models.PromptTemplate.category == category)

    if is_active is not None:
        query = query.filter(models.PromptTemplate.is_active == is_active)

    return query.offset(skip).limit(limit).all()


def update_prompt_template(
    db: Session,
    prompt_id: int,
    **kwargs
) -> Optional[models.PromptTemplate]:
    """
    Update a prompt template.

    Args:
        db: Database session
        prompt_id: ID of the prompt template to update
        **kwargs: Fields to update

    Returns:
        The updated PromptTemplate object if found, None otherwise
    """
    db_prompt = get_prompt_template(db, prompt_id)
    if not db_prompt:
        return None

    # Update specified fields
    for key, value in kwargs.items():
        if hasattr(db_prompt, key):
            setattr(db_prompt, key, value)

    # Always update the updated_at timestamp
    db_prompt.updated_at = datetime.now()

    db.commit()
    db.refresh(db_prompt)
    return db_prompt


def delete_prompt_template(db: Session, prompt_id: int) -> bool:
    """
    Delete a prompt template.

    Args:
        db: Database session
        prompt_id: ID of the prompt template to delete

    Returns:
        True if deleted, False if not found
    """
    db_prompt = get_prompt_template(db, prompt_id)
    if not db_prompt:
        return False

    db.delete(db_prompt)
    db.commit()
    return True


def create_ai_completion(
    db: Session,
    prompt_template_id: int,
    system_prompt: str,
    user_prompt: str,
    completion_text: str,
    model: str,
    temperature: float,
    max_tokens: int,
    company_id: Optional[int] = None,
    filing_id: Optional[int] = None,
    source_document_ids: Optional[List[int]] = None,
    context_completion_ids: Optional[List[int]] = None,
    context_texts: Optional[List[str]] = None,
    top_p: Optional[float] = None,
    frequency_penalty: Optional[float] = None,
    presence_penalty: Optional[float] = None,
    stop_sequences: Optional[List[str]] = None,
    completion_id: Optional[str] = None,
    token_usage: Optional[Dict[str, int]] = None,
    tags: Optional[List[str]] = None,
    notes: Optional[str] = None,
) -> models.LLMCompletion:
    """
    Create a new AI completion record.

    Args:
        db: Database session
        prompt_template_id: ID of the prompt template used
        system_prompt: System prompt text used
        user_prompt: User prompt text used
        completion_text: The generated completion text
        model: The model used (e.g., "gpt-4")
        temperature: Temperature setting used
        max_tokens: Max tokens setting used
        company_id: Optional ID of the related company
        filing_id: Optional ID of the related filing
        source_document_ids: Optional list of source document IDs used as context
        context_completion_ids: Optional list of completion IDs used as context
        context_texts: Optional list of context texts provided
        top_p: Optional top_p setting used
        frequency_penalty: Optional frequency penalty setting used
        presence_penalty: Optional presence penalty setting used
        stop_sequences: Optional stop sequences used
        completion_id: Optional OpenAI completion ID
        token_usage: Optional token usage statistics
        tags: Optional tags for the completion
        notes: Optional notes about the completion

    Returns:
        The created LLMCompletion object
    """
    now = datetime.now()
    db_completion = models.LLMCompletion(
        prompt_template_id=prompt_template_id,
        company_id=company_id,
        filing_id=filing_id,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        context_texts=context_texts,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
        stop_sequences=stop_sequences,
        completion_text=completion_text,
        completion_id=completion_id,
        created_at=now,
        token_usage=token_usage,
        tags=tags,
        notes=notes,
    )
    db.add(db_completion)
    db.flush()  # This assigns an ID to db_completion without committing the transaction

    # Add source documents if provided
    if source_document_ids:
        for doc_id in source_document_ids:
            source_doc = db.query(models.SourceDocument).filter(models.SourceDocument.id == doc_id).first()
            if source_doc:
                db_completion.source_documents.append(source_doc)

    # Add context completions if provided
    if context_completion_ids:
        for comp_id in context_completion_ids:
            context_completion = db.query(models.LLMCompletion).filter(models.LLMCompletion.id == comp_id).first()
            if context_completion:
                db_completion.context_completions.append(context_completion)

    db.commit()
    db.refresh(db_completion)
    return db_completion


def get_ai_completion(db: Session, completion_id: int) -> Optional[models.LLMCompletion]:
    """
    Get an AI completion by ID.

    Args:
        db: Database session
        completion_id: ID of the AI completion

    Returns:
        The LLMCompletion object if found, None otherwise
    """
    return db.query(models.LLMCompletion).filter(models.LLMCompletion.id == completion_id).first()


def get_ai_completions(
    db: Session,
    prompt_template_id: Optional[int] = None,
    company_id: Optional[int] = None,
    filing_id: Optional[int] = None,
    source_document_id: Optional[int] = None,
    context_completion_id: Optional[int] = None,
    used_as_context_by_completion_id: Optional[int] = None,
    model: Optional[str] = None,
    tags: Optional[List[str]] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[models.LLMCompletion]:
    """
    Get a list of AI completions with optional filtering.

    Args:
        db: Database session
        prompt_template_id: Optional prompt template ID to filter by
        company_id: Optional company ID to filter by
        filing_id: Optional filing ID to filter by
        source_document_id: Optional source document ID to filter by
        context_completion_id: Optional ID of a completion used as context
        used_as_context_by_completion_id: Optional ID of a completion that uses this completion as context
        model: Optional model to filter by
        tags: Optional tags to filter by
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of LLMCompletion objects
    """
    query = db.query(models.LLMCompletion)

    if prompt_template_id is not None:
        query = query.filter(models.LLMCompletion.prompt_template_id == prompt_template_id)

    if company_id is not None:
        query = query.filter(models.LLMCompletion.company_id == company_id)

    if filing_id is not None:
        query = query.filter(models.LLMCompletion.filing_id == filing_id)

    if source_document_id is not None:
        # Filter by source document ID using the many-to-many relationship
        query = query.join(models.LLMCompletion.source_documents).filter(
            models.SourceDocument.id == source_document_id
        )

    if context_completion_id is not None:
        # Filter by completion ID used as context
        # We need to use the association table directly for this query
        query = query.join(
            models.completion_context_completions,
            models.LLMCompletion.id == models.completion_context_completions.c.parent_completion_id
        ).filter(
            models.completion_context_completions.c.context_completion_id == context_completion_id
        )

    if used_as_context_by_completion_id is not None:
        # Filter by completion ID that uses this completion as context
        query = query.join(
            models.completion_context_completions,
            models.LLMCompletion.id == models.completion_context_completions.c.context_completion_id
        ).filter(
            models.completion_context_completions.c.parent_completion_id == used_as_context_by_completion_id
        )

    if model is not None:
        query = query.filter(models.LLMCompletion.model == model)

    # Filter by tags if specified (properly handling JSON contains)
    if tags is not None and len(tags) > 0:
        from sqlalchemy import cast
        from sqlalchemy.dialects.postgresql import JSONB
        for tag in tags:
            # Use PostgreSQL's JSON containment operator @> with proper casting
            query = query.filter(cast(models.LLMCompletion.tags, JSONB).contains([tag]))

    return query.offset(skip).limit(limit).all()


def create_completion_rating(
    db: Session,
    completion_id: int,
    rating: Optional[int] = None,
    accuracy_score: Optional[int] = None,
    relevance_score: Optional[int] = None,
    helpfulness_score: Optional[int] = None,
    comments: Optional[str] = None,
) -> models.CompletionRating:
    """
    Create a new completion rating.

    Args:
        db: Database session
        completion_id: ID of the related AI completion
        rating: Optional overall rating (1-5)
        accuracy_score: Optional accuracy score (1-5)
        relevance_score: Optional relevance score (1-5)
        helpfulness_score: Optional helpfulness score (1-5)
        comments: Optional comments about the completion

    Returns:
        The created CompletionRating object
    """
    now = datetime.now()
    db_rating = models.CompletionRating(
        completion_id=completion_id,
        rating=rating,
        accuracy_score=accuracy_score,
        relevance_score=relevance_score,
        helpfulness_score=helpfulness_score,
        comments=comments,
        created_at=now,
        updated_at=now,
    )
    db.add(db_rating)
    db.commit()
    db.refresh(db_rating)
    return db_rating


def get_completion_rating(db: Session, rating_id: int) -> Optional[models.CompletionRating]:
    """
    Get a completion rating by ID.

    Args:
        db: Database session
        rating_id: ID of the completion rating

    Returns:
        The CompletionRating object if found, None otherwise
    """
    return db.query(models.CompletionRating).filter(models.CompletionRating.id == rating_id).first()


def get_completion_ratings(
    db: Session,
    completion_id: Optional[int] = None,
    min_rating: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[models.CompletionRating]:
    """
    Get a list of completion ratings with optional filtering.

    Args:
        db: Database session
        completion_id: Optional completion ID to filter by
        min_rating: Optional minimum rating to filter by
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of CompletionRating objects
    """
    query = db.query(models.CompletionRating)

    if completion_id is not None:
        query = query.filter(models.CompletionRating.completion_id == completion_id)

    if min_rating is not None:
        query = query.filter(models.CompletionRating.rating >= min_rating)

    return query.offset(skip).limit(limit).all()


def update_completion_rating(
    db: Session,
    rating_id: int,
    **kwargs
) -> Optional[models.CompletionRating]:
    """
    Update a completion rating.

    Args:
        db: Database session
        rating_id: ID of the completion rating to update
        **kwargs: Fields to update

    Returns:
        The updated CompletionRating object if found, None otherwise
    """
    db_rating = get_completion_rating(db, rating_id)
    if not db_rating:
        return None

    # Update specified fields
    for key, value in kwargs.items():
        if hasattr(db_rating, key):
            setattr(db_rating, key, value)

    # Always update the updated_at timestamp
    db_rating.updated_at = datetime.now()

    db.commit()
    db.refresh(db_rating)
    return db_rating

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
    completion = get_ai_completion(db, completion_id)
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

def rate_completion(
    db: Session,
    completion_id: int,
    rating: Optional[int] = None,
    accuracy_score: Optional[int] = None,
    relevance_score: Optional[int] = None,
    helpfulness_score: Optional[int] = None,
    comments: Optional[str] = None,
) -> models.CompletionRating:
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
    completion = get_ai_completion(db, completion_id)
    if not completion:
        raise ValueError(f"Completion with ID {completion_id} not found")

    # Create the rating
    db_rating = create_completion_rating(
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
        existing_templates = get_prompt_templates(
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
            new_template = create_prompt_template(
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