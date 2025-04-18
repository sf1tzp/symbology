"""
Prompt engineering and management for AI analysis of financial documents.

This module provides:
1. Pre-defined prompt templates for different analysis types
2. Functions to customize and combine prompts
3. Utilities for storing and retrieving prompt history
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel

from src.utils.logging import get_logger

logger = get_logger(__name__)

class PromptRole(str, Enum):
    """Enumeration of valid prompt roles."""
    SYSTEM = "system"
    ASSISTANT = "assistant"
    USER = "user"


class PromptType(str, Enum):
    """Types of prompts supported by the system."""

    RISK_ANALYSIS = "risk_analysis"
    MANAGEMENT_ASSESSMENT = "management_assessment"
    FINANCIAL_POSITION = "financial_position"
    BUSINESS_SUMMARY = "business_summary"
    CUSTOM = "custom"


class PromptTemplate(BaseModel):
    """Template for a structured prompt."""

    name: str
    type: PromptType
    system_prompt: str
    user_prompt_template: str
    description: str = ""

    def format_user_prompt(self, **kwargs) -> str:
        """
        Format the user prompt template with provided values.

        Args:
            **kwargs: Values to format into the user prompt template

        Returns:
            The formatted user prompt
        """
        try:
            return self.user_prompt_template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing required parameter in prompt template: {e}")
            raise ValueError(f"Missing required parameter: {e}") from e


# System prompt templates for different analysis types
SYSTEM_PROMPTS = {
    PromptType.RISK_ANALYSIS: """
You are a financial analyst specializing in risk assessment. Your task is to analyze
the risk factors section of a company's 10-K filing and provide a structured assessment.
Focus on identifying the most significant risks, changes from previous years, and how
the company plans to mitigate these risks.

Provide your analysis in a clear, structured format with sections for:
1. Key Risk Categories
2. Most Significant Risks
3. Risk Trend Analysis (if historical data available)
4. Risk Mitigation Strategies
5. Overall Risk Assessment

Base your analysis solely on the provided information without adding external knowledge.
""",

    PromptType.MANAGEMENT_ASSESSMENT: """
You are a management consultant evaluating the leadership team of a company based on their
Management's Discussion and Analysis (MD&A) section of their 10-K filing. Your goal is to
assess the management team's:
1. Transparency and honesty in discussing challenges
2. Strategic thinking and forward planning
3. Execution capabilities based on past performance
4. Risk awareness and mitigation strategies

Provide a balanced assessment that identifies both strengths and weaknesses, supporting
each observation with specific evidence from the text.
""",

    PromptType.FINANCIAL_POSITION: """
You are a financial analyst specializing in company valuation and financial health assessment.
Analyze the provided financial statements and related disclosures to provide insights on:
1. Financial health and stability
2. Growth trajectory and trends
3. Efficiency and operational performance
4. Liquidity and solvency
5. Investment considerations

Highlight any significant changes from previous periods and potential red flags.
Use specific metrics and data points to support your analysis.
""",

    PromptType.BUSINESS_SUMMARY: """
You are a business analyst creating a comprehensive summary of a company based on its
10-K filing. Your task is to create a clear, concise overview of the company that includes:
1. Core business model and revenue streams
2. Market position and competitive landscape
3. Key products and services
4. Growth strategy and future outlook
5. Major business segments and their performance

Focus on providing a balanced, objective summary that captures the essential aspects of the
business without subjective evaluation.
"""
}


# User prompt templates for different analysis types
USER_PROMPT_TEMPLATES = {
    PromptType.RISK_ANALYSIS: """
Please analyze the following Risk Factors section from {company_name}'s {year} 10-K filing:

{risk_factors_text}

{additional_instructions}
""",

    PromptType.MANAGEMENT_ASSESSMENT: """
Please analyze the following Management's Discussion and Analysis section from {company_name}'s {year} 10-K filing:

{md_a_text}

{additional_instructions}
""",

    PromptType.FINANCIAL_POSITION: """
Please analyze the following financial information from {company_name}'s {year} 10-K filing:

BALANCE SHEET:
{balance_sheet_text}

INCOME STATEMENT:
{income_statement_text}

CASH FLOW STATEMENT:
{cash_flow_text}

{additional_notes}

{additional_instructions}
""",

    PromptType.BUSINESS_SUMMARY: """
Please provide a business summary based on the following information from {company_name}'s {year} 10-K filing:

BUSINESS DESCRIPTION:
{business_description_text}

{additional_instructions}
"""
}


def get_prompt_template(prompt_type: PromptType, name: Optional[str] = None) -> PromptTemplate:
    """
    Get a prompt template for the specified type.

    Args:
        prompt_type: The type of prompt template to retrieve
        name: Optional name for the template

    Returns:
        A PromptTemplate instance
    """
    if prompt_type not in SYSTEM_PROMPTS or prompt_type not in USER_PROMPT_TEMPLATES:
        raise ValueError(f"Unsupported prompt type: {prompt_type}")

    template_name = name or f"{prompt_type.value}_template"

    return PromptTemplate(
        name=template_name,
        type=prompt_type,
        system_prompt=SYSTEM_PROMPTS[prompt_type],
        user_prompt_template=USER_PROMPT_TEMPLATES[prompt_type]
    )


def create_custom_template(
    name: str,
    system_prompt: str,
    user_prompt_template: str,
    description: str = ""
) -> PromptTemplate:
    """
    Create a custom prompt template.

    Args:
        name: Name for the template
        system_prompt: System instructions for the model
        user_prompt_template: Template for the user prompt
        description: Optional description of the template

    Returns:
        A PromptTemplate instance
    """
    return PromptTemplate(
        name=name,
        type=PromptType.CUSTOM,
        system_prompt=system_prompt,
        user_prompt_template=user_prompt_template,
        description=description
    )