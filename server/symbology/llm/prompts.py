"""
Prompt engineering and management for AI analysis of financial documents.

This module provides:
1. Pre-defined prompt templates for different analysis types
2. Functions to customize and combine prompts
3. Utilities for storing and retrieving prompt history
"""

from enum import Enum
from typing import List, Optional

from symbology.database.documents import Document, DocumentType
from symbology.database.generated_content import GeneratedContent
from symbology.llm.client import remove_thinking_tags
from symbology.utils.logging import get_logger

logger = get_logger(__name__)

class PromptRole(str, Enum):
    """Enumeration of valid prompt roles."""
    SYSTEM = "system"
    ASSISTANT = "assistant"
    USER = "user"


# System prompt templates for different analysis types
DOCUMENT_PROMPTS = {
    DocumentType.RISK_FACTORS: """
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

Provide only one message as your response, and do not ask a follow up question.
""",

    DocumentType.MDA: """
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

    DocumentType.DESCRIPTION: """
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

AGGREGATE_PROMPT = """
Summarize the historical changes in these documents.

When you're done, add a table of contents section to the top.

"""

AGGREGATE_SUMMARY_PROMPT = """
Consider these historical reports. Write 100 words providing an overview of the company.
"""


def format_user_prompt_content(
    source_documents: Optional[List[Document]] = None,
    source_content: Optional[List[GeneratedContent]] = None,
    additional_text: Optional[str] = None
) -> str:
    """
    Format user prompt content from various source materials.

    This function assembles content from multiple sources into a single user prompt:
    - Source documents (SEC filings, etc.)
    - Generated content (previous AI outputs)
    - Additional text content

    Args:
        source_documents: List of Document objects to include
        source_content: List of GeneratedContent objects to include
        additional_text: Additional text content to include

    Returns:
        Formatted user prompt content as a string
    """
    formatted_parts = []

    # Format source documents
    if source_documents:
        for document in source_documents:
            filing = document.filing
            company = document.company

            formatted_parts.append(f"""
<document>
<meta company_name="{company.name}" filing_type="{filing.form}" period_of_report="{filing.period_of_report}" document_type="{document.document_type.value}"/>
<content>
{remove_thinking_tags(document.content)}
</content>
</document>
""")

    # Format source content (generated content)
    if source_content:
        for content in source_content:
            company = content.company

            # Try to get filing info from source documents if available
            filing_info = ""
            if content.source_documents:
                document = content.source_documents[0]
                filing = document.filing
                filing_info = f'generated_from_form="{filing.form}" generated_from_period_of_report="{filing.period_of_report}"'

            formatted_parts.append(f"""
<document>
<meta company_name="{company.name if company else 'Unknown'}" {filing_info}" source_type="generated_content"/>
<content>
{remove_thinking_tags(content.content) if content.content else ''}
</content>
</document>
""")

    # Add additional text content if provided
    if additional_text:
        formatted_parts.append(f"""
<additional_content>
{additional_text.strip()}
</additional_content>
""")

    return ("").join(formatted_parts)