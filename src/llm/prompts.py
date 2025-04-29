"""
Prompt engineering and management for AI analysis of financial documents.

This module provides:
1. Pre-defined prompt templates for different analysis types
"""

from pathlib import Path

from src.utils.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPTS = {}
with open(Path("src/llm/system_prompts/business_description.md")) as file:
    SYSTEM_PROMPTS["business_description"] = file.read()

with open(Path("src/llm/system_prompts/management_discussion.md")) as file:
    SYSTEM_PROMPTS["management_discussion"] = file.read()

with open(Path("src/llm/system_prompts/risk_factors.md")) as file:
    SYSTEM_PROMPTS["risk_factors"] = file.read()

USER_PROMPT_TEMPLATES = {
    "risk_factors": """
    Please analyze the following Risk Factors section from {company_name}'s {year} 10-K filing:

    {content}
    """,

    "management_discussion": """
    Please analyze the following Management's Discussion and Analysis section from {company_name}'s {year} 10-K filing:

    {content}
    """,

    "business_description": """
    Please provide a business summary based on the following information from {company_name}'s {year} 10-K filing:

    {content}
    """
}

def format_user_prompt(prompt: str, **kwargs) -> str:
    """
    Format the user prompt template with provided values.

    Args:
        **kwargs: Values to format into the user prompt template

    Returns:
        The formatted user prompt
    """
    try:
        return prompt.format(**kwargs)
    except KeyError as e:
        logger.error(f"Missing required parameter in prompt template: {e}")
        raise ValueError(f"Missing required parameter: {e}") from e