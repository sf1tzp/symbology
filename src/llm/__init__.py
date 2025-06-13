"""
AI integration package for Symbology.

This package provides functionalities for interacting with OpenAI API
and implementing prompt engineering for financial document analysis.
"""

from .client import create_chat_completion
from .prompts import format_prompt_template, SYSTEM_PROMPTS, USER_PROMPT_TEMPLATES

__all__ = [
    'create_chat_completion',
    'format_prompt_template'
    'USER_PROMPT_TEMPLATES',
    'SYSTEM_PROMPTS',
]