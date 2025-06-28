"""
Prompt engineering and management for AI analysis of financial documents.

This module provides:
1. Pre-defined prompt templates for different analysis types
2. Functions to customize and combine prompts
3. Utilities for storing and retrieving prompt history
"""

from enum import Enum

from pydantic import BaseModel

from src.database.documents import DocumentType
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


def format_document_messages(document):
    messages = [{
        'role': PromptRole.SYSTEM.value,
        'content': DOCUMENT_PROMPTS[document.document_type]
    },
    {
        'role': PromptRole.USER.value,
        'content': document.content
    }]
    return messages



def format_aggregate_messages(chat_contents):
    formatted_contents = list(map(lambda date: f"""
        ---

        # Filed On: {date}

        {chat_contents[date]}

        """, sorted(chat_contents.keys())))

    messages = [{
        'role': PromptRole.SYSTEM.value,
        'content': "Summarize the historical changes in these documents."
    },
    {
        'role': PromptRole.USER.value,
        'content': ("").join(formatted_contents)
    }]
    return messages