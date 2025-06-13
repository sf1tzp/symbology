"""
OpenAI API client for making inference requests to the OpenAI endpoint.

This module provides functionality to:
1. Connect to the configured OpenAI endpoint
2. Send prompts with configurable parameters
3. Process and return responses
"""
from openai import OpenAI, OpenAIError

from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


client = OpenAI(
    base_url = f"http://{settings.openai_api.host}:{settings.openai_api.port}/v1",
    api_key = f"{settings.openai_api.api_key}"
)

def create_chat_completion(model: str, temperature: float, system_prompt: str, user_prompt: str):
    try:
        response = client.chat.completions.create(
            messages=[
                {
                    'role': 'system',
                    'content': system_prompt
                },
                {
                    "role": 'user',
                    "content": user_prompt
                }
            ],
            model=model,
            temperature=temperature
        )
        if len(response.choices) > 1:
            logger.warning(f"generated {len(response.choices)} choices")

        return response.choices[0].message.content

    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
