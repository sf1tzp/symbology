"""
AI integration package for Symbology.

This package provides functionalities for interacting with OpenAI API
and implementing prompt engineering for financial document analysis.
"""

from .client import Message, CompletionRequest, CompletionResponse, OpenAIClient
from .prompts import (
    PromptType,
    PromptTemplate,
    get_prompt_template,
    create_custom_template
)

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