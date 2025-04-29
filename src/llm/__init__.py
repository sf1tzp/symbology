"""
AI integration package for Symbology.

This package provides functionalities for interacting with OpenAI API
and implementing prompt engineering for financial document analysis.
"""

from .client import create_chat_completion
from .prompts import format_user_prompt, SYSTEM_PROMPTS, USER_PROMPT_TEMPLATES

__all__ = [
    'create_chat_completion',
    'format_user_prompt'
    'USER_PROMPT_TEMPLATES',
    'SYSTEM_PROMPTS',
]