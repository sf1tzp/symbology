"""
AI integration package for Symbology.

This package provides functionalities for interacting with OpenAI API
and implementing prompt engineering for financial document analysis.
"""

from .client import get_chat_response, init_client

__all__ = [
    'Message',
    'CompletionRequest',
    'CompletionResponse',
    'OpenAIClient',
    'PromptType',
    'PromptTemplate',
    'get_prompt_template',
    'create_custom_template',
]
